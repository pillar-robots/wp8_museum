#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from my_controll.public_speech_policy import TextToSpeechNode
from control_msgs.msg import JointTrajectoryControllerState
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from play_motion2_msgs.action import PlayMotion2
from geometry_msgs.msg import Twist, TwistStamped, WrenchStamped
import time

class FinalSkill(Node):
    def __init__(self):
        super().__init__("get_closer")

        #Action server
        self._action_client_left = ActionClient(self, FollowJointTrajectory, '/arm_left_controller/follow_joint_trajectory')
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)
        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
        self.mobile_base_pub = self.create_publisher(TwistStamped, '/mobile_base_controller/cmd_vel', 0)
        self._action_client_left.wait_for_server()
        self._action_client_right.wait_for_server()
        self.speech = TextToSpeechNode()

        self._client = ActionClient(
            self,
            PlayMotion2,
            '/play_motion2'
        )
    
    def send_goal_joints(self, side="left",timesec=4,j1=1.03,j2=0.98,j3=0.48,j4=1.8,j5=1.48,j6=0.67,j7=2.07):
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory.joint_names = [f'arm_{side}_{i}_joint' for i in range(1, 8)]
        
        point = JointTrajectoryPoint()
        #point.positions = [1.03, 0.98, 0.48, 1.8, 1.48, 0.67, 2.07]  # Cílové pozice kloubů
        point.positions = [j1,j2,j3,j4,j5,j6,j7]
        point.time_from_start = Duration(sec=timesec, nanosec=0)  # Čas vykonání trajektorie
        
        goal_msg.trajectory.points.append(point)
        
        self.get_logger().info(f"Odesílám trajektorii k /arm_{side}_controller/follow_joint_trajectory")
        if side == "left":
            return self._action_client_left.send_goal_async(goal_msg)
        elif side == "right":
            return self._action_client_right.send_goal_async(goal_msg)
        else:
            return None
        
    def send_home(self):
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'home'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending home motion goal...')
        send_goal_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_goal_future.add_done_callback(self.goal_response_callback)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Home motion rejected')
            return

        self.get_logger().info('Home motion accepted')
        self._result_future = goal_handle.get_result_async()
        self._result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(f'Feedback: {feedback}')

    def result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Home motion finished')
        rclpy.shutdown()

    def publish_torso(self,height, time_up = 2):
        height = max(0.1, min(height, 0.35))
        msg = JointTrajectory()
        msg.joint_names = ["torso_lift_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(height)]
        point.time_from_start = Duration(sec=time_up, nanosec=0)
        msg.points = [point]
        self.torso_pub.publish(msg)
    
    def publish_head(self, joint_1, joint_2):
        msg = JointTrajectory()
        msg.joint_names = ["head_1_joint", "head_2_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(joint_1), float(joint_2)]
        point.time_from_start = Duration(sec=2, nanosec=0)
        msg.points = [point]
        self.head_joint_pub.publish(msg)

    def get_joint_states(self, topic):
        self.get_logger().info("Obtaining joint states...")
        future = rclpy.task.Future()

        def callback(msg):
            if not future.done():
                future.set_result(msg)

        subscription = self.create_subscription(
            JointTrajectoryControllerState,
            topic,
            callback,
            1
        )

        rclpy.spin_until_future_complete(self, future)

        self.destroy_subscription(subscription)

        result = future.result()
        assert isinstance(result, JointTrajectoryControllerState)
        joint_names = result.joint_names
        joint_positions = list(result.reference.positions)
        joint_states = dict(zip(joint_names, joint_positions))

        return joint_states
    
    def close_gripper(self, arm, vel_factor = 0.1, sleep_time=0.1):
        point = JointTrajectoryPoint()
        point.positions = [0.005, 0.0]
        self.get_logger().info("Closing gripper")
        future = self.gripper_action(arm, point, vel_factor, sleep_time)
        return future

    def open_gripper(self, arm, vel_factor = 0.1, sleep_time=0.1):
        point = JointTrajectoryPoint()
        point.positions = [0.044, 0.044]
        self.get_logger().info("Opening gripper")
        future = self.gripper_action(arm, point, vel_factor, sleep_time)
        return future
    
    def move_gripper (self, arm, left_finger, right_finger, vel_factor = 0.1, sleep_time = 0.1):
        point = JointTrajectoryPoint()
        point.positions = [right_finger, left_finger]
        self.get_logger().info(f"Moving {arm} gripper to: {right_finger},{left_finger}")
        future = self.gripper_action(arm, point, vel_factor, sleep_time)
        return future
    
    def gripper_action(self, arm, point:JointTrajectoryPoint, vel_factor, sleep_time):
        if arm == 'left' or arm == 'right':
            msg = FollowJointTrajectory.Goal()
            action_name = f"/gripper_{arm}_controller/follow_joint_trajectory"
            action_client = ActionClient(self, FollowJointTrajectory, action_name)
        else:
            self.get_logger().error('Wrong Arm Selected: Arm must be "left" or "right".')
            return False
        
        joint_states = self.get_joint_states(f"/gripper_{arm}_controller/controller_state")
        joint_goals = list(point.positions)
        distances = [abs(joint_states[f"gripper_{arm}_right_finger_joint"]-joint_goals[0]),abs(joint_states[f"gripper_{arm}_left_finger_joint"]-joint_goals[1])]
        duration = (max(distances)/vel_factor)*2
        point.time_from_start.sec = int(duration)
        
        point.time_from_start.nanosec = int((duration - int(duration)) * 1e9)
        msg.trajectory.joint_names = [f"gripper_{arm}_right_finger_joint", f"gripper_{arm}_left_finger_joint"]
        msg.trajectory.points = [point]
        future = action_client.send_goal_async(msg)
        time.sleep(duration + sleep_time)
        return future
    
    def publish_base(self, value_move, type_move ,duration = 3):
        twist_stamped_msg = TwistStamped()
        twist_stamped_msg.twist = Twist()
        if type_move == "linear":
            twist_stamped_msg.twist.linear.x = value_move
        else:
            twist_stamped_msg.twist.angular.z = value_move
        start_time = time.time()
        while time.time() - start_time < duration:
            self.mobile_base_pub.publish(twist_stamped_msg)
            time.sleep(0.1)
        twist_stamped_msg.twist.linear.x = 0.0
        twist_stamped_msg.twist.angular.z = 0.0
        self.mobile_base_pub.publish(twist_stamped_msg)
    
    def move_skill(self):
        #time.sleep(10)
        self.open_gripper('left')
        self.open_gripper('right')
        self.speech.call_speech("I am going to grasp the shoe and give it to you then.", "kid")
        left_close = self.send_goal_joints("left",2, -0.27, 0.84, 1.78, 1.97, -1.88, 1.39, 0.0)
        time.sleep(1.7)

        self.publish_head(0.95, -0.74)

        left_close = self.send_goal_joints("left",3, -0.33, -0.77, 2.36, 1.14, -2.08, 1.35, 0.03)
        time.sleep(2.7)

        left_close = self.send_goal_joints("left",3, -0.1, -0.61, 2.67, 1.7, -2.11, 0.68, 0.66)
        time.sleep(4)

        self.close_gripper('left')

        left_close = self.send_goal_joints("left",2, -0.35, -0.75, 2.44, 1.5, -2.11, 0.98, 0.3)
        time.sleep(1.7)

        self.publish_head(0.0, 0.0)

        left_close = self.send_goal_joints("left",6, 1.25, 0.86, 0.47, 2.07, -1.6, -1.14, 0.29)
        time.sleep(5)

        self.speech.call_speech("I will move a bit forward to show you and give you the typical shoe.", "kid")
        time.sleep(2)

        self.publish_base(0.2, "linear", duration=3)
        self.speech.call_speech("Now you can take the shoe.", "kid")
        time.sleep(5)

        self.open_gripper('left')
        time.sleep(2)

        self.publish_base(-0.3, "linear", duration=3)
        time.sleep(3)

        self.send_home()

    def move_skilla(self):
        #time.sleep(10)
        self.open_gripper('left')
        self.open_gripper('right')
        self.speech.call_speech("I am going to grasp the shoe and give it to you then.", "adult")
        left_close = self.send_goal_joints("left",2, -0.27, 0.84, 1.78, 1.97, -1.88, 1.39, 0.0)
        time.sleep(1.7)

        self.publish_head(0.95, -0.74)

        left_close = self.send_goal_joints("left",3, -0.33, -0.77, 2.36, 1.14, -2.08, 1.35, 0.03)
        time.sleep(2.7)

        left_close = self.send_goal_joints("left",3, -0.1, -0.61, 2.67, 1.7, -2.11, 0.68, 0.66)
        time.sleep(4)

        self.close_gripper('left')

        left_close = self.send_goal_joints("left",2, -0.35, -0.75, 2.44, 1.5, -2.11, 0.98, 0.3)
        time.sleep(1.7)

        self.publish_head(0.0, 0.0)

        left_close = self.send_goal_joints("left",6, 1.25, 0.86, 0.47, 2.07, -1.6, -1.14, 0.29)
        time.sleep(5)

        self.speech.call_speech("I will move a bit forward to show you and give you the typical shoe.", "adult")
        time.sleep(2)

        self.publish_base(0.2, "linear", duration=3)
        self.speech.call_speech("Now you can take the shoe.", "adult")
        time.sleep(5)

        self.open_gripper('left')
        time.sleep(2)

        self.publish_base(-0.3, "linear", duration=3)
        time.sleep(3)

        self.send_home()

def main(args=None):
    rclpy.init()
    node = FinalSkill()
    node.move_skilla()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
