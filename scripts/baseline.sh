#!/bin/bash -x
algo=$1
gpu=$2

if [ $algo = 1 ]
then
    algo='ppo'
    rollout_length='512'
    evaluate_interval="10"
    ckpt_interval='100'
    rl_activation="tanh"
    num_batches="100"
elif [ $algo = 2 ]
then
    algo='sac'
    rollout_length="1000"
    evaluate_interval="1000"
    ckpt_interval='100000'
    rl_activation="relu"
    num_batches="1"
fi

workers="1"
prefix="4.15.BASELINE.ppo.debug"
max_global_step="60000000"
env="sawyer-nut-assembly-single-robosuite-v0"
gpu="0"
rl_hid_size="256"
max_episode_step="150"
evaluate_interval="100"
max_grad_norm="0.5"
entropy_loss_coef="0.01"
buffer_size="125000"
num_batches="1"
lr_actor="3e-4"
lr_critic="3e-4"
debug="True"
rollout_length="1000"
batch_size="128"
clip_param="0.2"
seed='1234'
ctrl_reward='1e-2'
reward_type='dense'
comment='Baseline'
start_steps='10000'
actor_num_hid_layers='1'
success_reward='10.'
has_terminal='True'
ckpt_interval='100000'
log_root_dir="./logs"
group='simple-mover-baseline-sac'

#mpiexec -n $workers
python -m rl.main \
    --log_root_dir $log_root_dir \
    --wandb True \
    --prefix $prefix \
    --max_global_step $max_global_step \
    --env $env \
    --gpu $gpu \
    --rl_hid_size $rl_hid_size \
    --max_episode_step $max_episode_step \
    --evaluate_interval $evaluate_interval \
    --entropy_loss_coef $entropy_loss_coef \
    --buffer_size $buffer_size \
    --num_batches $num_batches \
    --lr_actor $lr_actor \
    --lr_critic $lr_critic \
    --debug $debug \
    --rollout_length $rollout_length \
    --batch_size $batch_size \
    --clip_param $clip_param \
    --rl_activation $rl_activation \
    --algo $algo \
    --seed $seed \
    --ctrl_reward $ctrl_reward \
    --reward_type $reward_type \
    --comment $comment \
    --start_steps $start_steps \
    --actor_num_hid_layers $actor_num_hid_layers \
    --success_reward $success_reward \
    --has_terminal $has_terminal \
    --group $group
