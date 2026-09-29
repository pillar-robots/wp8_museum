#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from my_controll.public_speech_policy import TextToSpeechNode
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from play_motion2_msgs.action import PlayMotion2
import time


class Silence(Node):
    def __init__(self):
        super().__init__("silence")

        #Action server
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
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

    def send_silent(self):
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'silent'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending silent motion goal...')
        send_goal_future = self._client.send_goal_async(
            goal_msg,
            feedback_callback=self.feedback_callback
        )

        send_goal_future.add_done_callback(self.goal_response_callback)
    
    def send_quite(self):
        self.get_logger().info('Waiting for /play_motion2 action server...')
        self._client.wait_for_server()

        goal_msg = PlayMotion2.Goal()
        goal_msg.motion_name = 'quite'
        goal_msg.skip_planning = False

        self.get_logger().info('Sending quite motion goal...')
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
        
    def move_finger(self, counterk = 0):
        self.send_silent()
        time.sleep(2)
        if counterk == 0:
            self.speech.call_speech("Well done, you are already organised and now we have to keep quite that we can continue the main part of the exhibition.", "kid")
        elif counterk == 1:
            self.speech.call_speech("Plase be silient that we can continue without any intteruption.", "kid")
        elif counterk == 2:
            self.speech.call_speech("This is my last call for keep you silent.", "kid")
        else:
            pass
        time.sleep(3)
        # time.sleep(1)
        # right_close = self.send_goal_joints("right",4, 1.27, 0.37, 1.22, 2.01, -0.21, 1.06, 0.02)
        # time.sleep(6)

        # self.send_goal_joints("right",4, -1.1, 1.45, 2.71, 1.69, -1.57, 1.38, -0.01)
        #self.send_home()

    def move_calm_down(self, countera = 0):
        #time.sleep(10)
        self.send_quite()
        time.sleep(2)
        #right_close = self.send_goal_joints("right",3, 0.8, -0.1, 1.5, 1.72, -1.51, 0.57, -0.02)
        if countera == 0:
            self.speech.call_speech("Thank you everyone for getting organised so quickly. " "If we could keep the noise level low, we’ll continue with the next part of the exhibition.", "adult"
        )
        elif countera == 1:
            self.speech.call_speech("I would like to ask you again for silence.", "adult")
        elif countera == 2:
            self.speech.call_speech("Let's be quite.", "adult")
        else:
            pass
        time.sleep(3)
        # time.sleep(4)
        # right_close = self.send_goal_joints("right",3, 0.7, 0.52, 1.71, 1.69, -2.07, 0.63, 0.02)
        # time.sleep(4.5)

        # self.send_goal_joints("right",3, -1.1, 1.45, 2.71, 1.69, -1.57, 1.38, -0.01)
        #self.send_home()

def main(args=None):
    rclpy.init()
    node = Silence()
    node.move_calm_down()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
