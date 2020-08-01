#<!/bin/bash -x

prefix="SAC.PLANNER.AUGMENTED.IK.reuse"
gpu=$1
seed=$2
algo='sac'
env="sawyer-push-obstacle-v2"
max_episode_step="250"
debug="True"
reward_type='sparse'
# log_root_dir="/data/jun/projects/hrl-planner/logs"
log_root_dir="./logs"
planner_integration="True"
reuse_data_type="random"
action_range="0.1"
invalid_planner_rew="-0.0"
stochastic_eval="True"
find_collision_free="True"
vis_replay="True"
plot_type='3d'
use_smdp_update="True"
# use_discount_meta="False"
step_size="0.02"
success_reward="150.0"
max_reuse_data='30'
reward_scale="0.2"
use_ik_target="True"
ik_target="grip_site"
ac_rl_maximum="0.05"
ac_rl_minimum="-0.05"

python -m rl.main \
    --log_root_dir $log_root_dir \
    --wandb True \
    --prefix $prefix \
    --env $env \
    --gpu $gpu \
    --max_episode_step $max_episode_step \
    --debug $debug \
    --algo $algo \
    --seed $seed \
    --reward_type $reward_type \
    --planner_integration $planner_integration \
    --reuse_data_type $reuse_data_type \
    --action_range $action_range \
    --stochastic_eval $stochastic_eval \
    --find_collision_free $find_collision_free \
    --vis_replay $vis_replay \
    --plot_type $plot_type \
    --use_smdp_update $use_smdp_update \
    --step_size $step_size \
    --success_reward $success_reward \
    --max_reuse_data $max_reuse_data \
    --reward_scale $reward_scale \
    --use_ik_target $use_ik_target \
    --ik_target $ik_target \
    --ac_rl_maximum $ac_rl_maximum \
    --ac_rl_minimum $ac_rl_minimum \
    --use_discount_meta $use_discount_meta \
