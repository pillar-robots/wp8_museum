import time
import rclpy
from rclpy.action import ActionClient
import random
from rclpy.node import Node
from std_msgs.msg import Bool
from trajectory_msgs.msg import JointTrajectoryPoint, JointTrajectory
from builtin_interfaces.msg import Duration
from cognitive_nodes.policy import Policy
from core.utils import perception_msg_to_dict
from my_controll.public_speech_policy import TextToSpeechNode
from my_controll.joke import TellJoke
from my_controll.ask_kids import AskQuestion
from my_controll.pointing_picture import Point
from my_controll.screen_show import PointScreen
from my_controll.final_skill_simple import FinalSkill
from my_controll.wave_people import WaveClient
from my_controll.get_closer import GetCloser
from my_controll.silence import Silence
from my_controll.in_row import InRow
from my_controll.sit_down import Sit
from my_controll.blue_area import BlueArea
from my_controll.separation import Separation
from my_controll.autonomous_move import AutonomousMovement
from my_controll.conversation import ConversationPub
from cognitive_node_interfaces.srv import SetActivation
from core.service_client import ServiceClientAsync
from std_msgs.msg import Float32
from pathlib import Path

class PolicySilenceAdults(Policy):
    def __init__(self, name='silenceeead', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)
        self.counter_adult = 0

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response

class PolicySilenceKids(Policy):
    def __init__(self, name='silence', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)
        self.counter_kid = 0

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyBlueAreaKids(Policy):
    def __init__(self, name='blue_areak', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyBlueAreaAdults(Policy):
    def __init__(self, name='blue_areaa', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response

class PolicySeat(Policy):
    def __init__(self, name='seat', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyRow(Policy):
    def __init__(self, name='row', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response

class PolicyJokeNov(Policy):
    def __init__(self, name='joken', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
# class PolicyJokeExp(Policy):
#     def __init__(self, name='jokee', class_name='cognitive_nodes.policy.Policy', publisher_msg=None, publisher_topic=None, **params):
#         super().__init__(name, class_name, publisher_msg, publisher_topic, **params)

#     async def execute_callback(self, request, response):
#         self.get_logger().info(f'Execute select - {self.name}')
#         time.sleep(5)
#         response.policy = self.name
#         return response
    
class PolicyAskNov(Policy):
    def __init__(self, name='askn', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyAskExp(Policy):
    def __init__(self, name='aske', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyGetCloser(Policy):
    def __init__(self, name='closer', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicySepSeat(Policy):
    def __init__(self, name='sepseat', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicySepRow(Policy):
    def __init__(self, name='seprow', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyPoint(Policy):
    def __init__(self, name='point', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyPointAdult(Policy):
    def __init__(self, name='pointa', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyScreen(Policy):
    def __init__(self, name='screen', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyScreenAdult(Policy):
    def __init__(self, name='screena', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyScript(Policy):
    def __init__(self, name='script', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyScriptAdult(Policy):
    def __init__(self, name='scripta', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicyRest(Policy):
    def __init__(self, name='rest', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicySing(Policy):
    def __init__(self, name='sing', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response

class PolicyDance(Policy):
    def __init__(self, name='dance', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response

class PolicyTalk(Policy):
    def __init__(self, name='talk', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)

    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info(f'Execute select - {self.name}')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)
        response.policy = self.name
        return response
    
class PolicySelectGuide(Policy):
    def __init__(self, name='guide', class_name='cognitive_nodes.policy.Policy', service_msg=None, service_name=None, **params):      
        super().__init__(name=name, class_name=class_name, **params)
        self.people_value = None
        self.guide_value = None
        self.set_activation_1_1_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_placed_experienced/set_activation', self.cbgroup_client)
        self.set_activation_1_2_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_placed_novel/set_activation', self.cbgroup_client)
        self.set_activation_2_1_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_quite_experienced/set_activation', self.cbgroup_client)
        self.set_activation_2_2_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_quite_novel/set_activation', self.cbgroup_client)
        self.set_activation_3_1_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_engagement_experienced/set_activation', self.cbgroup_client)
        self.set_activation_3_2_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_engagement_novel/set_activation', self.cbgroup_client)
        self.set_activation_4_1_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_exhibition_experienced/set_activation', self.cbgroup_client)
        self.set_activation_4_2_client = ServiceClientAsync(self, SetActivation, '/robot_purpose/visitors_exhibition_novel/set_activation', self.cbgroup_client)
        self.guide_sub = self.create_subscription(Float32,'/exhibition/guide',self.guide_callback,0)
        self.people_sub = self.create_subscription(Float32,'/exhibition/people',self.people_callback,0)

    def guide_callback(self, msg):
        self.guide_value = msg.data

    def people_callback(self, msg):
        self.people_value = msg.data
    
    async def execute_callback(self, request, response):
        msg = Bool()
        msg.data = False
        self.turnon_pub.publish(msg)
        self.get_logger().info('Executing guide policy')
        self.get_logger().info(
            f'Current values -> '
            f'guide: {self.guide_value}'
        )
        if 0.1 <= self.guide_value < 0.5:
            result = await self.set_activation_1_1_client.send_request_async(activation=0.9)
            result = await self.set_activation_2_1_client.send_request_async(activation=0.8)
            result = await self.set_activation_3_1_client.send_request_async(activation=0.7)
            result = await self.set_activation_4_1_client.send_request_async(activation=0.6)
            result = await self.set_activation_1_2_client.send_request_async(activation=0.0)
            result = await self.set_activation_2_2_client.send_request_async(activation=0.0)
            result = await self.set_activation_3_2_client.send_request_async(activation=0.0)
            result = await self.set_activation_4_2_client.send_request_async(activation=0.0)
        
        elif self.guide_value >= 0.5:
            result = await self.set_activation_1_2_client.send_request_async(activation=0.9)
            result = await self.set_activation_2_2_client.send_request_async(activation=0.8)
            result = await self.set_activation_3_2_client.send_request_async(activation=0.7)
            result = await self.set_activation_4_2_client.send_request_async(activation=0.6)
            result = await self.set_activation_1_1_client.send_request_async(activation=0.0)
            result = await self.set_activation_2_1_client.send_request_async(activation=0.0)
            result = await self.set_activation_3_1_client.send_request_async(activation=0.0)
            result = await self.set_activation_4_1_client.send_request_async(activation=0.0)
        
        if self.guide_value >= 0.1:
            print("Here show something on the screen.")
        if self.people_value >= 0.1:
            self.get_logger().info('Executing wave')
        time.sleep(5)
        msg.data = True
        self.turnon_pub.publish(msg)

        response.policy = self.name
        return response

# class AutonomousIdleMotion(Node):
#     def __init__(self):
#         super().__init__('autonomous_idle_motion')

#         self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
#         self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory',0)

#     def publish_head(self, joint_1, joint_2, duration=2):
#         msg = JointTrajectory()
#         msg.joint_names = ["head_1_joint", "head_2_joint"]

#         point = JointTrajectoryPoint()
#         point.positions = [float(joint_1), float(joint_2)]
#         point.time_from_start = Duration(sec=duration, nanosec=0)

#         msg.points = [point]

#         self.head_joint_pub.publish(msg)

#     def publish_torso(self, height, duration=2):
#         height = max(0.10, min(height, 0.20))

#         msg = JointTrajectory()
#         msg.joint_names = ["torso_lift_joint"]

#         point = JointTrajectoryPoint()
#         point.positions = [float(height)]
#         point.time_from_start = Duration(sec=duration, nanosec=0)

#         msg.points = [point]

#         self.torso_pub.publish(msg)

#     def execute_random_motion(self):
#         head_1 = random.uniform(-0.35, 0.35)
#         head_2 = random.uniform(-0.30, 0.30)
#         torso = random.uniform(0.10, 0.20)
#         move_time = random.uniform(1.0, 2.5)

#         self.publish_head(head_1, head_2, int(move_time))
#         self.publish_torso(torso, int(move_time))

#         time.sleep(move_time)
#         time.sleep(random.uniform(0.5, 1.5))

#         if random.random() < 0.65:
#             self.publish_head(1.1, 0.5, 3)
#             time.sleep(4)

#         self.publish_head(0.0, 0.0, 2)
#         self.publish_torso(0.15, 2)

# class AutonomousSinGuideMotion(Node):
#     def __init__(self):
#         super().__init__('autonomous_idle_motion')

#         self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
#         self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory',0)

#     def publish_head(self, joint_1, joint_2, duration=2):
#         msg = JointTrajectory()
#         msg.joint_names = ["head_1_joint", "head_2_joint"]

#         point = JointTrajectoryPoint()
#         point.positions = [float(joint_1), float(joint_2)]
#         point.time_from_start = Duration(sec=duration, nanosec=0)

#         msg.points = [point]

#         self.head_joint_pub.publish(msg)

#     def publish_torso(self, height, duration=2):
#         height = max(0.10, min(height, 0.20))

#         msg = JointTrajectory()
#         msg.joint_names = ["torso_lift_joint"]

#         point = JointTrajectoryPoint()
#         point.positions = [float(height)]
#         point.time_from_start = Duration(sec=duration, nanosec=0)

#         msg.points = [point]

#         self.torso_pub.publish(msg)

#     def execute_random_motion(self):
#         head_1 = random.uniform(-0.35, 0.35)
#         head_2 = random.uniform(-0.30, 0.30)
#         torso = random.uniform(0.10, 0.20)
#         move_time = random.uniform(1.0, 2.5)

#         self.publish_head(head_1, head_2, int(move_time))
#         self.publish_torso(torso, int(move_time))

#         time.sleep(move_time)
#         time.sleep(random.uniform(0.5, 1.5))

#         self.publish_head(0.0, 0.0, 2)
#         self.publish_torso(0.15, 2)