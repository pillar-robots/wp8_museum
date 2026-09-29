#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
import time
from play_motion2_msgs.action import PlayMotion2
from my_controll.public_speech_policy import TextToSpeechNode
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration

class WaveClient(Node):

    def __init__(self):
        super().__init__('wave_client')

        self._client = ActionClient(self, PlayMotion2, '/play_motion2')
        self.speech = TextToSpeechNode()
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)

    def publish_torso(self,height, time_up = 2):
        height = max(0.1, min(height, 0.35))
        msg = JointTrajectory()
        msg.joint_names = ["torso_lift_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(height)]
        point.time_from_start = Duration(sec=time_up, nanosec=0)
        msg.points = [point]
        self.torso_pub.publish(msg)

    def send_wave(self):
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'wave'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending wave motion goal...')
        send_goal_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_goal_future.add_done_callback(self.goal_response_callback)
        time.sleep(3)
        self.speech.call_speech("Hello visitors, welcome in the museum for our exhibition. We will slowly start with the organisation.", "adult")

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

    def send_reach(self):
        self.publish_torso(0.25, time_up=3)
        time.sleep(3)
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'vertical_reach'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending reach motion goal...')
        send_goal_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_goal_future.add_done_callback(self.goal_response_callback)
        time.sleep(3)
        self.speech.call_speech("This is my maximum reach I can show you.", "adult")
        time.sleep(10)

        self.send_home()
        time.sleep(3)

    def goal_response_callback(self, future):
        goal_handle = future.result()

        if not goal_handle.accepted:
            self.get_logger().error('Wave motion rejected')
            return

        self.get_logger().info('Wave motion accepted')
        self._result_future = goal_handle.get_result_async()
        self._result_future.add_done_callback(self.result_callback)

    def feedback_callback(self, feedback_msg):
        feedback = feedback_msg.feedback
        self.get_logger().info(f'Feedback: {feedback}')

    def result_callback(self, future):
        result = future.result().result
        self.get_logger().info('Wave motion finished')
        rclpy.shutdown()


def main():
    rclpy.init()
    node = WaveClient()
    node.send_reach()
    rclpy.spin(node)


if __name__ == '__main__':
    main()
