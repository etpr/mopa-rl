import re
from collections import OrderedDict

import numpy as np
from gym import spaces
from env.base import BaseEnv
from env.sawyer.sawyer import SawyerEnv

class SawyerPegInsertionEnv(SawyerEnv):
    def __init__(self, **kwargs):
        kwargs['camera_name'] = 'topview'
        super().__init__("sawyer_peg_insertion.xml", **kwargs)
        self._get_reference()
        self._init_goal = self.sim.model.body_pos[self.sim.model.body_name2id("box")].copy()

    def _get_reference(self):
        super()._get_reference()

    def _reset(self):
        init_qpos = self.init_qpos + np.random.randn(self.init_qpos.shape[0]) * 0.02
        self.sim.data.qpos[self.ref_joint_pos_indexes] = init_qpos
        self.sim.data.qvel[self.ref_joint_vel_indexes] = 0.
        goal = self._init_goal.copy()
        goal[:2] += np.random.randn(2) * 0.02
        self.sim.model.body_pos[self.sim.model.body_name2id('box')] = goal
        self.sim.forward()

        return self._get_obs()

    def compute_reward(self, action):
        info = {}
        reward = 0
        pegHeadPos = self.sim.data.get_site_xpos("pegHead")
        hole = self.sim.data.get_site_xpos("hole")
        dist = np.linalg.norm(pegHeadPos-hole)
        reward_reach = -dist
        reward += reward_reach
        info = dict(reward_reach=reward_reach)
        if dist < 0.05:
            reward += self._kwargs['success_reward']
            self._success = True
            self._terminal = True

        return reward, info


    def _get_obs(self):
        di = super()._get_obs()
        di['hole']  = self.sim.data.get_site_xpos("hole")
        di['pegHead'] = self.sim.data.get_site_xpos("pegHead")
        di['pegEnd'] = self.sim.data.get_site_xpos("pegEnd")
        di['peg_quat'] = self._get_quat("peg")
        return di

    @property
    def static_geom_ids(self):
        return ['table_collision', 'box']

    def _step(self, action, is_planner=False):
        """
        (Optional) does gripper visualization after actions.
        """
        assert len(action) == self.dof, "environment got invalid action dimension"

        if not is_planner or self._prev_state is None:
            self._prev_state = self.sim.data.qpos[self.ref_joint_pos_indexes].copy()

        if self._i_term is None:
            self._i_term = np.zeros_like(self.mujoco_robot.dof)

        if is_planner:
            rescaled_ac = np.clip(action[:self.robot_dof], -self._ac_scale, self._ac_scale)
        else:
            rescaled_ac = action[:self.robot_dof] * self._ac_scale
        desired_state = self._prev_state + rescaled_ac

        n_inner_loop = int(self._frame_dt/self.dt)
        for _ in range(n_inner_loop):
            self.sim.data.qfrc_applied[self.ref_joint_vel_indexes] = self.sim.data.qfrc_bias[self.ref_joint_vel_indexes].copy()

            if self.use_robot_indicator:
                self.sim.data.qfrc_applied[
                    self.ref_indicator_joint_pos_indexes
                ] = self.sim.data.qfrc_bias[
                    self.ref_indicator_joint_pos_indexes
                ].copy()

            if self.use_target_robot_indicator:
                self.sim.data.qfrc_applied[
                    self.ref_target_indicator_joint_pos_indexes
                ] = self.sim.data.qfrc_bias[
                    self.ref_target_indicator_joint_pos_indexes
                ].copy()
            self._do_simulation(desired_state)

        self._prev_state = np.copy(desired_state)
        reward, info = self.compute_reward(action)

        return self._get_obs(), reward, self._terminal, info
