import rclpy
from rclpy.node import Node
from rclpy.task import Future
from geometry_msgs.msg import Twist, TwistStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
from my_controll.public_speech_policy import TextToSpeechNode
from play_motion2_msgs.action import PlayMotion2
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
import random
import time
from std_msgs.msg import Bool

class InRow(Node):
    def __init__(self):
        super().__init__('in_row')

        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
        self.speech = TextToSpeechNode()
        self._action_client_left = ActionClient(self, FollowJointTrajectory, '/arm_left_controller/follow_joint_trajectory')
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)
        self._action_client_left.wait_for_server()
        self._action_client_right.wait_for_server()

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


    def move_head(self):
        yaw_positions = [-1.0, 0.0, 1.0] 
        pitch_positions = [0.6, 0.0, -0.6] 
        phrases = [
        ("Adults, please line up in a row so everyone can stand beside one.", "adult"),
        ("Could the adults stand next to each other in one straight line, please?", "adult"),
        ("Alright everyone, let’s form a clean row and stay in position for a moment.", "adult")
        ]
        self.speech.call_speech(*random.choice(phrases))
        right_up = self.send_goal_joints("right",3, 0.82, 0.37, 0.6, 0.86, -0.91, 1.28, 0.31)
        time.sleep(2.8)
        right_up = self.send_goal_joints("right",5, 1.5, 0.34, 0.69, 0.78, -0.89, 1.25, -0.36)
        for yaw in yaw_positions:
            for pitch in pitch_positions:
                self.publish_head(yaw, pitch)
                time.sleep(0.5)
        #time.sleep(2)
        self.publish_head(0.0, 0.0)
        self.send_goal_joints("right",3, -1.1, 1.45, 2.71, 1.69, -1.57, 1.38, -0.01)
        #self.send_home()

def main():
    rclpy.init()
    node = InRow()
    node.move_head()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()