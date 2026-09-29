#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from play_motion2_msgs.action import PlayMotion2
from my_controll.public_speech_policy import TextToSpeechNode
from geometry_msgs.msg import Twist, TwistStamped, WrenchStamped
import time
import random

class BlueArea(Node):
    def __init__(self):
        super().__init__("blue_area")

        #Action server
        self._action_client_left = ActionClient(self, FollowJointTrajectory, '/arm_left_controller/follow_joint_trajectory')
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)
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

    def send_blue(self):
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'blue'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending blue motion goal...')
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
        
    def move_bluek(self):
        #time.sleep(10)
        phrases = [
        ("Alright kids, could everyone please make their way over to the blue area and stay together there during the exhibition?", "kid"),
        ("Hey everyone, all the kids should slowly head toward the blue zone and wait there until the next instruction is given.", "kid"),
        ("Please move over to the blue area now, and make sure you stay inside the marked section with the rest of the group.", "kid")
        ]
        self.speech.call_speech(*random.choice(phrases))

        self.publish_base(0.2, "linear", duration=3)

        self.send_blue()
        time.sleep(14)

        # left_up = self.send_goal_joints("left",3, 0.21, -1.02, 1.71, 1.72, -2.0, 1.12, 0.0)
        # right_up = self.send_goal_joints("right",3, 0.41, -1.1, 2.15, 1.62, -1.83, 1.28, 0.0)
        # time.sleep(2.8)

        # left_up = self.send_goal_joints("left",2, 1.4, -0.76, 2.49, 0.95, -2.0, 1.25, 0.0)
        # right_up = self.send_goal_joints("right",2, 1.54, -0.84, 3.03, 1.03, -1.66, 1.17, 0.0)
        # time.sleep(3)

        # left_up = self.send_goal_joints("left",2, 0.87, -0.57, 2.32, 0.95, -2.11, 1.15, 0.0)
        # right_up = self.send_goal_joints("right",2, 1.08, -0.7, 2.91, 1.03, -1.6, 1.05, 0.0)
        # time.sleep(1.8)

        # left_up = self.send_goal_joints("left",2, 0.39, -0.47, 1.57, 1.61, -2.11, 1.4, 0.0)
        # right_up = self.send_goal_joints("right",2, 0.25, -0.62, 1.79, 1.78, -1.76, 1.0, 0.0)
        # time.sleep(1.8)

        # left_up = self.send_goal_joints("left",2, 0.87, -0.47, 1.57, 1.69, -2.11, 1.4, 0.0)
        # right_up = self.send_goal_joints("right",2, 0.66, -0.67, 1.79, 1.86, -1.62, 1.0, 0.0)
        # time.sleep(3.5)

        # self.send_goal_joints("left",3, -1.1, 1.46, 2.71, 1.69, -1.57, 1.39, 0.0)
        # self.send_goal_joints("right",3, -1.1, 1.45, 2.71, 1.69, -1.57, 1.38, -0.01)
        self.publish_base(-0.3, "linear", duration=3)
        #self.send_home()

    def move_bluea(self):
        #time.sleep(10)
        phrases = [
        ("Attention adults, please proceed calmly to the blue area and remain there until further instructions are announced.", "adult"),
        ("Could all adults make their way toward the blue zone and gather there in an orderly manner, please?", "adult"),
        ("Ladies and gentlemen, we kindly ask all adults to move over to the designated blue area and wait there for the next update.", "adult")
]
        self.speech.call_speech(*random.choice(phrases))

        self.publish_base(0.2, "linear", duration=2)

        self.send_blue()
        time.sleep(14)

        # left_up = self.send_goal_joints("left",3, 0.21, -1.02, 1.71, 1.72, -2.0, 1.12, 0.0)
        # right_up = self.send_goal_joints("right",3, 0.41, -1.1, 2.15, 1.62, -1.83, 1.28, 0.0)
        # time.sleep(2.7)

        # left_up = self.send_goal_joints("left",3, 1.4, -0.76, 2.49, 0.95, -2.0, 1.25, 0.0)
        # right_up = self.send_goal_joints("right",3, 1.54, -0.84, 3.03, 1.03, -1.66, 1.17, 0.0)
        # time.sleep(5)

        # left_up = self.send_goal_joints("left",2, 0.87, -0.57, 2.32, 0.95, -2.11, 1.15, 0.0)
        # right_up = self.send_goal_joints("right",2, 1.08, -0.7, 2.91, 1.03, -1.6, 1.05, 0.0)
        # time.sleep(1.7)

        # left_up = self.send_goal_joints("left",2, 0.39, -0.47, 1.57, 1.61, -2.11, 1.4, 0.0)
        # right_up = self.send_goal_joints("right",2, 0.25, -0.62, 1.79, 1.78, -1.76, 1.0, 0.0)
        # time.sleep(1.7)

        # left_up = self.send_goal_joints("left",2, 0.87, -0.47, 1.57, 1.69, -2.11, 1.4, 0.0)
        # right_up = self.send_goal_joints("right",2, 0.66, -0.67, 1.79, 1.86, -1.62, 1.0, 0.0)
        # time.sleep(3.5)

        # self.send_goal_joints("left",3, -1.1, 1.46, 2.71, 1.69, -1.57, 1.39, 0.0)
        # self.send_goal_joints("right",3, -1.1, 1.45, 2.71, 1.69, -1.57, 1.38, -0.01)
        self.publish_base(-0.3, "linear", duration=2)
        #self.send_home()


def main(args=None):
    rclpy.init()
    node = BlueArea()
    node.move_bluea()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
