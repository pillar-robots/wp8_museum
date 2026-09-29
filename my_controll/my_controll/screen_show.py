import paramiko
import time
#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from control_msgs.action import FollowJointTrajectory
from builtin_interfaces.msg import Duration
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from play_motion2_msgs.action import PlayMotion2
from my_controll.public_speech_policy import TextToSpeechNode
import time
import random

class PointScreen(Node):
    def __init__(self):
        super().__init__("point_screen")

        #Action server
        self._action_client_left = ActionClient(self, FollowJointTrajectory, '/arm_left_controller/follow_joint_trajectory')
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)
        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
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
        
    def move_screen_pointing(self):
        self.speech.call_speech("Let's continue with a video on my screen...", "kid")
        time.sleep(2)
        ip = "192.168.123.40"
        username = "pal"  
        password = "pal"
        is_video=True
        file_path="/home/pal/Videos/Pizarrin01.mp4" 

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        if is_video:
            command = f"export DISPLAY=:0; nohup ffplay -fs -autoexit {file_path} > /dev/null 2>&1 &"
        else:
            command = f"export DISPLAY=:0; feh -F {file_path}"

        print(f"Executing: {command}")

        ssh.exec_command(command)
        print("Media launched successfully.")
        
        self.send_goal_joints("left", 4, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        self.send_goal_joints("right", 4, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        time.sleep(4)
        self.publish_head(0.0,-0.8)
        time.sleep(32)
        ssh.close()
        self.publish_head(0.0, 0.0)
        self.send_home()

    def move_screen_pointinga(self):
        self.speech.call_speech("Let's continue with a video on my screen...", "adult")
        time.sleep(2)
        ip = "192.168.123.40"
        username = "pal"  
        password = "pal"
        is_video=True
        file_path="/home/pal/Videos/Pizarrin01.mp4" 

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        if is_video:
            command = f"export DISPLAY=:0; nohup ffplay -fs -autoexit {file_path} > /dev/null 2>&1 &"
        else:
            command = f"export DISPLAY=:0; feh -F {file_path}"

        print(f"Executing: {command}")

        ssh.exec_command(command)
        print("Media launched successfully.")
        
        self.send_goal_joints("left", 4, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        self.send_goal_joints("right", 4, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        time.sleep(4)
        self.publish_head(0.0,-0.8)
        time.sleep(32)
        ssh.close()
        self.publish_head(0.0, 0.0)
        self.send_home()

    def mp3_play(self):
        self.speech.call_speech("I will play a short melody for you.", "adult")
        time.sleep(3)
        ip = "192.168.123.40"
        username = "pal"  
        password = "pal"
        is_video=True
        file_path="/home/pal/Videos/melody.mp3" 

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, username=username, password=password)

        if is_video:
            command = f"export DISPLAY=:0; nohup ffplay -fs -autoexit {file_path} > /dev/null 2>&1 &"
        else:
            command = f"export DISPLAY=:0; feh -F {file_path}"

        print(f"Executing: {command}")

        ssh.exec_command(command)
        print("Media launched successfully.")
        
        time.sleep(10)

def main(args=None):
    rclpy.init()
    node = PointScreen()
    node.mp3_play()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()