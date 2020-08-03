python -m rl.main --log_root_dir ./logs --wandb True --prefix SAC.PLANNER.AUGMENTED.reuse15.discount --env sawyer-lift-obstacle-v0 --gpu 1 --max_episode_step 250 --debug False --algo sac --seed 1236 --reward_type sparse --planner_integration True --reuse_data True --action_range 0.5 --omega 0.5 --stochastic_eval True --find_collision_free True --vis_replay True --plot_type 3d --use_smdp_update True --ac_space_type piecewise --step_size 0.02 --success_reward 150.0 --max_reuse_data 15 --reward_scale 0.5 --log_indiv_entropy True --evaluate_interval 10000 --use_discount_meta Truea --is_train False --vis_info False --date 07.25 --camera_name visview --num_eval 30