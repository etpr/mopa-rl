#!/bin/bash
workers="2"
prefix="ll.push.dense.cnn.debug"
hrl="True"
max_global_step="60000000"
ll_type="rl"
algo='sac'
policy='cnn'
env="pusher-push-pixel-v0"
gpu="2"
rl_hid_size="256"
meta_update_target="both"
hrl_network_to_update="LL"
hl_type='subgoal'
max_episode_steps="150"
max_meta_len="15"
evaluate_interval="1500"
meta_tanh_policy="True"
max_grad_norm="0.5"
buffer_size="120000"
num_batches="1"
lr_actor="3e-4"
lr_critic="3e-4"
debug="False"
rollout_length="1000"
batch_size="256"
clip_param="0.2"
rl_activation="relu"
reward_type='dense'
comment='Primitive skill with different initialization, use shorter distance between box and origin fix limited_joints use smaller ctrl reward'
seed='1234'
ctrl_reward_coef='1'
start_steps='10000'
reward_scale='1'
actor_num_hid_layers='1'
terminal='True'



mpiexec -n $workers python -m rl.main --log_root_dir ./logs \
    --wandb True \
    --prefix $prefix \
    --max_global_step $max_global_step \
    --hrl $hrl \
    --ll_type $ll_type \
    --env $env \
    --gpu $gpu \
    --rl_hid_size $rl_hid_size \
    --meta_update_target $meta_update_target \
    --hrl_network_to_update $hrl_network_to_update \
    --max_episode_steps $max_episode_steps \
    --evaluate_interval $evaluate_interval \
    --meta_tanh_policy $meta_tanh_policy \
    --max_meta_len $max_meta_len \
    --buffer_size $buffer_size \
    --num_batches $num_batches \
    --lr_actor $lr_actor \
    --lr_critic $lr_critic \
    --debug $debug \
    --rollout_length $rollout_length \
    --batch_size $batch_size \
    --clip_param $clip_param \
    --max_grad_norm $max_grad_norm \
    --rl_activation $rl_activation \
    --reward_type $reward_type \
    --comment $comment \
    --seed $seed \
    --ctrl_reward_coef $ctrl_reward_coef \
    --start_steps $start_steps \
    --reward_scale $reward_scale \
    --actor_num_hid_layers $actor_num_hid_layers \
    --hl_type $hl_type \
    --terminal $terminal \
    --algo $algo \
    --policy $policy