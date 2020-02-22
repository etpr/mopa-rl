import numpy as np
from collections import OrderedDict
import torch
import torch.nn as nn
import torch.optim as optim

from rl.dataset import ReplayBuffer, RandomSampler
from rl.base_agent import BaseAgent
from rl.policies.mlp_actor_critic import MlpActor, MlpCritic
from rl.policies.cnn_actor_critic import CNNActor, CNNCritic
from util.logger import logger
from util.mpi import mpi_average
from util.pytorch import optimizer_cuda, count_parameters, \
    compute_gradient_norm, compute_weight_norm, sync_networks, sync_grads, \
    obs2tensor, to_tensor
from env.action_spec import ActionSpec
from util.gym import action_size
from gym import spaces


class MetaPPOAEAgent(BaseAgent):
    def __init__(self, config, ob_space, joint_space=None):
        super().__init__(config, ob_space)

        if not config.hrl:
            logger.warn('Creating a dummy meta PPO agent')
            return


        if config.primitive_skills:
            skills = config.primitive_skills
        else:
            skills = ['primitive']
        self.skills = skills


        if config.hrl:
            # ac_space = ActionSpec(size=0)
            ac_space = spaces.Dict()
            ac_space.spaces['default'] = spaces.Discrete(len(skills))
                #ac_space.add(','.join(cluster), 'discrete', len(skills), 0, 1)
            if config.hl_type == 'subgoal':
                if config.subgoal_type == 'joint':
                    ac_space.spaces['subgoal'] = spaces.Box(shape=(action_size(joint_space),), low=-1., high=1.)
                    #joint_space['default']
                else:
                    # change here
                    ac_space.spaces['subgoal'] = spaces.Box(shape=(2,), low=-0.3, high=0.3)
            self.ac_space = ac_space

        # build up networks
        self._actor_encoder = Encoder(config, ob_space['default'].shape[0], config.ae_feat_dim)
        self._actor_encoder.copy_conv_weights_from(self._critic_encoder)
        self._decoder = Decoder(config, config.ae_feat_dim, self._critic_encoder.w)
        print(self._actor_encoder)

        self._actor = MlpActor(config, ob_space, ac_space, tanh_policy=config.meta_tanh_policy)
        self._old_actor = MlpActor(config, ob_space, ac_space, tanh_policy=config.meta_tanh_policy)
        self._critic = MlpCritic(config, ob_space)

        self._network_cuda(config.device)

        self._actor_optim = optim.Adam(self._actor.parameters(), lr=config.lr_actor)
        self._critic_optim = optim.Adam(self._critic.parameters(), lr=config.lr_critic)
        self._encoder_optim = optim.Adam(self._critic_encoder.parameters(),
                                         lr=config.lr_encoder)
        self._decoder_optim = optim.Adam(self._decoder.parameters(),
                                         lr=config.lr_decoder)

        sampler = RandomSampler()
        self._buffer = ReplayBuffer(['ob', 'ac', 'done', 'rew', 'ret', 'adv',
                                     'ac_before_activation', 'log_prob'],
                                    config.buffer_size,
                                    sampler.sample_func)

        if config.is_chef:
            logger.warn('Creating a meta PPO agent')
            logger.info('The actor has %d parameters', count_parameters(self._actor))
            logger.info('The critic has %d parameters', count_parameters(self._critic))

    def store_episode(self, rollouts):
        self._compute_gae(rollouts)
        self._buffer.store_episode(rollouts)

    def _compute_gae(self, rollouts):
        T = len(rollouts['done'])
        ob = rollouts['ob']
        if self._config.policy == 'mlp':
            ob = self.normalize(ob)
        ob = obs2tensor(ob, self._config.device)
        vpred = self._critic(ob).detach().cpu().numpy()[:,0]
        assert len(vpred) == T + 1

        done = rollouts['done']
        rew = rollouts['rew']
        adv = np.empty((T, ) , 'float32')
        lastgaelam = 0
        for t in reversed(range(T)):
            nonterminal = 1 - done[t]
            delta = rew[t] + self._config.discount_factor * vpred[t + 1] * nonterminal - vpred[t]
            adv[t] = lastgaelam = delta + self._config.discount_factor * self._config.gae_lambda * nonterminal * lastgaelam

        ret = adv + vpred[:-1]

        assert np.isfinite(adv).all()
        assert np.isfinite(ret).all()

        # update rollouts
        if adv.std() == 0:
            rollouts['adv'] = (adv * 0).tolist()
        else:
            rollouts['adv'] = ((adv - adv.mean()) / adv.std()).tolist()
        rollouts['ret'] = ret.tolist()

    def state_dict(self):
        if not self._config.hrl:
            return {}

        return {
            'actor_state_dict': self._actor.state_dict(),
            'critic_state_dict': self._critic.state_dict(),
            'actor_optim_state_dict': self._actor_optim.state_dict(),
            'critic_optim_state_dict': self._critic_optim.state_dict(),
            'ob_norm_state_dict': self._ob_norm.state_dict(),
            'critic_encoder_state_dict': self._critic_encoder.state_dict(),
            'decoder_state_dict': self._decoder.state_dict(),
            'actor_encoder_state_dict': self._actor_encoder.state_dict(),
            'encoder_optim_state_dict': self._encoder_optim.state_dict(),
            'decoder_optim_state_dict': self._decoder_optim.state_dict()
        }

    def load_state_dict(self, ckpt):
        if not self._config.hrl:
            return

        self._actor.load_state_dict(ckpt['actor_state_dict'])
        self._critic.load_state_dict(ckpt['critic_state_dict'])
        self._ob_norm.load_state_dict(ckpt['ob_norm_state_dict'])
        self._actor_encoder.load_state_dict(ckpt['actor_encoder_state_dict'])
        self._critic_encoder.load_state_dict(ckpt['critc_encoder_state_dict'])
        self._actor_encoder.copy_conv_weights_from(self._critic_encoder)
        self._decoder.load_state_dict(ckpt['decoder_state_dict'])

        self._network_cuda(self._config.device)

        self._actor_optim.load_state_dict(ckpt['actor_optim_state_dict'])
        self._critic_optim.load_state_dict(ckpt['critic_optim_state_dict'])
        self._encoder_optim.load_state_dict(ckpt['encoder_optim_state_dict'])
        self._decoder_optim.load_state_dict(ckpt['decoder_optim_state_dict'])
        optimizer_cuda(self._actor_optim, self._config.device)
        optimizer_cuda(self._critic_optim, self._config.device)

    def _network_cuda(self, device):
        self._actor.to(device)
        self._old_actor.to(device)
        self._critic.to(device)
        self._actor_encoder.to(device)
        self._critic_encoder.to(device)
        self._decoder.to(device)

    def sync_networks(self):
        sync_networks(self._actor)
        sync_networks(self._critic)
        sync_networks(self._actor_encoder)
        sync_networks(self._critic_encoder)
        sync_networks(self._decoder)

    def train(self):
        self._copy_target_network(self._old_actor, self._actor)

        for _ in range(self._config.num_batches):
            transitions = self._buffer.sample(self._config.batch_size)
            train_info = self._update_network(transitions)
            decoder_info = self._update_decoder(transitions['ob'], transitions['ob'])

        self._buffer.clear()

        train_info.update({
            'actor_grad_norm': compute_gradient_norm(self._actor),
            'actor_weight_norm': compute_weight_norm(self._actor),
            'critic_grad_norm': compute_gradient_norm(self._critic),
            'critic_weight_norm': compute_weight_norm(self._critic),
        })

        for k, v in decoder_info.items():
            train_info.update({
                k: v
            })
        return train_info

    def _update_decoder(self, obs, target_obs):
        info = {}
        _to_tensor = lambda x: to_tensor(x, self._config.device)
        obs = _to_tensor(obs)
        target_obs = _to_tensor(target_obs)
        h = self._critic_encoder(obs['default'])

        rec_obs = self._decoder(h)
        rec_loss = F.mse_loss(target_obs['default'], rec_obs)

        latent_loss = (0.5*h.pow(2).sum(1)).mean()

        loss = rec_loss + self._config.decoder_latent_lambda * latent_loss
        self._encoder_optim.zero_grad()
        self._decoder_optim.zero_grad()
        loss.backward(retain_graph=True)
        sync_grads(self._critic_encoder)
        sync_grads(self._decoder)

        self._encoder_optim.step()
        self._decoder_optim.step()
        info['ae_loss'] = loss

        return info

    def _update_network(self, transitions):
        info = {}

        # pre-process observations
        o = transitions['ob']
        if self._config.policy == 'mlp':
            o = self.normalize(o)

        bs = len(transitions['done'])
        _to_tensor = lambda x: to_tensor(x, self._config.device)
        o = _to_tensor(o)
        ac = _to_tensor(transitions['ac'])
        z = _to_tensor(transitions['ac_before_activation'])
        ret = _to_tensor(transitions['ret']).reshape(bs, 1)
        adv = _to_tensor(transitions['adv']).reshape(bs, 1)

        old_log_pi = _to_tensor(transitions['log_prob']).reshape(bs, 1)
        #old_log_pi = _to_tensor(transitions['log_prob'])

        log_pi, ent = self._actor.act_log(o, z)

        # need to fix here
        # if (log_pi - old_log_pi).max() > 20:
        #     print('(log_pi - old_log_pi) is too large', (log_pi - old_log_pi).max())
        #     import ipdb; ipdb.set_trace()


        # the actor loss
        entropy_loss = self._config.entropy_loss_coeff * ent.mean()

        # actor_loss = OrderedDict()
        # for k in log_pi.keys():
        #     ratio = torch.exp(torch.clamp(log_pi[k]-old_log_pi[k], -20, 20))
        #     surr1 = ratio * adv
        #     surr2 = ratio = torch.clamp(ratio, 1.0 - self._config.clip_param,
        #                                       1.0 + self._config.clip_param) * adv
        #     actor_loss[k] = -torch.min(surr1, surr2).mean()
        ratio = torch.exp(torch.clamp(log_pi - old_log_pi, -20, 20))
        surr1 = ratio * adv
        surr2 = torch.clamp(ratio, 1.0 - self._config.clip_param,
                            1.0 + self._config.clip_param) * adv
        actor_loss = -torch.min(surr1, surr2).mean()

        if not np.isfinite(ratio.cpu().detach()).all() or not np.isfinite(adv.cpu().detach()).all():
            import ipdb; ipdb.set_trace()
        info['entropy_loss'] = entropy_loss.cpu().item()

        # for k in actor_loss.keys():
        #     info['actor_loss_'+k] = actor_loss[k].cpu().item()

        #actor_loss = torch.stack(list(actor_loss.values())).sum()
        info['actor_loss'] = actor_loss.cpu().item()
        actor_loss += entropy_loss

        # the q loss
        value_pred = self._critic(o)
        value_loss = self._config.value_loss_coeff * (ret - value_pred).pow(2).mean()

        info['value_target'] = ret.mean().cpu().item()
        info['value_predicted'] = value_pred.mean().cpu().item()
        info['value_loss'] = value_loss.cpu().item()

        # update the actor

        self._actor_optim.zero_grad()
        actor_loss.backward()
        if self._config.max_grad_norm is not None:
            torch.nn.utils.clip_grad_norm_(self._actor.parameters(), self._config.max_grad_norm)
        sync_grads(self._actor)
        self._actor_optim.step()

        # update the critic
        self._critic_optim.zero_grad()
        value_loss.backward()
        if self._config.max_grad_norm is not None:
            torch.nn.utils.clip_grad_norm_(self._critic.parameters(), self._config.max_grad_norm)
        sync_grads(self._critic)
        self._critic_optim.step()

        # include info from policy
        info.update(self._actor.info)

        return mpi_average(info)

    def act(self, ob, is_train=True):
        if self._config.hrl:
            if self._config.policy != 'cnn':
                ob = self.normalize(ob)
            return self._actor.act(ob, is_train, return_log_prob=True)
        else:
            return [0], None, None
