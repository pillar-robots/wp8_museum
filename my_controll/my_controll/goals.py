from cognitive_nodes.goal import GoalMotiven

class SubGoal(GoalMotiven):
    def __init__(self, name='blue_area_goal', class_name='cognitive_nodes.goal.Goal', **params):
        super().__init__(name, class_name, **params)
        
    async def get_reward(self, old_perception=None, perception=None):
        reward = 0.0
        blue_area_old_value = 0
        blue_area_value = 0
        if old_perception is not None:
            blue_area_old_value = perception.read().sel(features=["blue_area:data"]).values[-1] if "blue_area:data" in perception.feature_labels else 0.0
        if perception is not None:
            blue_area_value = perception.read().sel(features=["blue_area:data"]).values[-1] if "blue_area:data" in perception.feature_labels else 0.0
        if blue_area_value-blue_area_old_value>0.2:
            reward = 1.0

        return reward, self.get_clock().now().to_msg()

