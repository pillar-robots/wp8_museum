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

class TellJoke(Node):
    def __init__(self):
        super().__init__("tell_joke")
        self.speech = TextToSpeechNode()
        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)

    def publish_head(self, joint_1, joint_2):
        msg = JointTrajectory()
        msg.joint_names = ["head_1_joint", "head_2_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(joint_1), float(joint_2)]
        point.time_from_start = Duration(sec=2, nanosec=0)
        msg.points = [point]
        self.head_joint_pub.publish(msg)

    def move_joke(self):
        self.speech.call_speech("I need you fully attention please, I prepaire a good joke for you to get your attention. ... Hope you are ready.", "adult")
        time.sleep(9)
        self.speech.call_speech("I asked my dog, \n\n what's two minus two.", "adult")
        time.sleep(4)
        self.speech.call_speech("He said nothing", "adult")

    def move_jokexp(self):
        self.speech.call_speech("Let me tell a joke about robots to increase your attention. ... Now listen!.", "adult")
        time.sleep(6.5)
        self.speech.call_speech("I told my robot to clean my room.", "adult")
        time.sleep(4.0)
        self.speech.call_speech("Now it controls the entire house.", "adult")

def main(args=None):
    rclpy.init()
    node = TellJoke()
    node.move_joke()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
