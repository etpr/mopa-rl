python -m rl.main --log_root_dir /data/jun/projects/hrl-planner/logs --wandb True --prefix MoPA-SAC.scale1.0.range0.5.v2_2 --env sawyer-assembly-v1 --gpu 2 --max_episode_step 250 --debug False --algo sac --seed 1235 --reward_type sparse --mopa True --reuse_data True --action_range 0.5 --omega 0.5 --stochastic_eval True --find_collision_free True --vis_replay True --plot_type 3d --use_smdp_update True --ac_space_type piecewise --step_size 0.02 --success_reward 150.0 --max_reuse_data 15 --reward_scale 1.0 --log_indiv_entropy False --use_discount_meta True --is_train False --date 08.09 --is_simplified True
