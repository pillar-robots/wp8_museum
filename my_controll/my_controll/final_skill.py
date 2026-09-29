#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.action.client import ClientGoalHandle
import rclpy.wait_for_message
from tiago_dual_interfaces.action import MoveArm, CarArm
from geometry_msgs.msg import PoseStamped
from my_nodes.tf_test import DepthTo3DNode
from my_nodes.center_robot import YoloDetectionHandler
from my_nodes.public_speech import TextToSpeechNode
from my_nodes.listener_acr import ASRNode
from control_msgs.action import FollowJointTrajectory
from control_msgs.msg import JointTrajectoryControllerState
from builtin_interfaces.msg import Duration
from geometry_msgs.msg import Twist, TwistStamped, WrenchStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from tiago_interfaces.msg import AsrAction
from std_msgs.msg import Bool
import time
import random
import threading

class MoveClient(Node):
    def __init__(self):
        super().__init__("move_client")
        self.move_action_client_ = ActionClient(self, MoveArm, '/nevim')
        self.move_car_action_client_ = ActionClient(self, CarArm, '/cartesian')

        # Subscriber
        self.subscribe_wrist = self.create_subscription(WrenchStamped, '/ft_sensor_left_controller/wrench', self.callback_wrist, 0)
        self.force = None
        # Publishers for head, mobile base, and torso
        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
        self.mobile_base_pub = self.create_publisher(TwistStamped, '/mobile_base_controller/cmd_vel', 0)
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)

        #Action server
        self._action_client_left = ActionClient(self, FollowJointTrajectory, '/arm_left_controller/follow_joint_trajectory')
        self._action_client_right = ActionClient(self, FollowJointTrajectory, '/arm_right_controller/follow_joint_trajectory')
        self._action_client_left.wait_for_server()
        self._action_client_right.wait_for_server()

        # Mobile base parameters for autonomous movement
        self.last_rotate = 0.1
        self.rotation_count = 0
        self.current_publish_duration = random.uniform(2.0, 5.0)
        self.current_pause_duration = random.uniform(5.0, 10.0)

        # self.subscription = self.create_subscription(
        #     AsrAction,
        #     'detail_action',
        #     self.listener_callback_action,
        #     2
        # )
        self.stop_publisher_ = self.create_publisher(Bool, '/stop_signal', 10)

    def callback_wrist(self,msg):
        if msg:
            self.force = msg.wrench.force.z

    def return_force(self):
        return self.force

    def send_goal(self, arm, goal):
        self.get_logger().info("Čekám na akční server...")
        if not self.move_action_client_.wait_for_server(timeout_sec=1.0):
            self.get_logger().error("Akční server není dostupný!")
            return

        self.get_logger().info("Akční server připojen, odesílám goal.")
        goal_msg = MoveArm.Goal()
        goal_msg.goal = goal
        goal_msg.arm_name = arm

        future_goal = self.move_action_client_.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future_goal)

        try:
            goal_handle = future_goal.result()
            if not goal_handle.accepted:
                self.get_logger().error("Goal nebyl přijat.")
                return None

            self.get_logger().info("Goal přijat, čekám na výsledek.")
            future_result = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, future_result)
            result = future_result.result().result
            self.get_logger().info(f"Výsledek akce: {result}")
            return result
        
        except Exception as e:
            self.get_logger().error(f"Chyba při zpracování goalu: {e}")
            return None
    
    def send_goal_car(self, arm, goal):
        self.get_logger().info("Čekám na akční server...")
        if not self.move_car_action_client_.wait_for_server(timeout_sec=1.0):
            self.get_logger().error("Akční server není dostupný!")
            return

        self.get_logger().info("Akční server připojen, odesílám goal.")
        goal_msg = CarArm.Goal()
        goal_msg.goal = goal
        goal_msg.arm_name = arm

        future_goal = self.move_car_action_client_.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, future_goal)

        try:
            goal_handle = future_goal.result()
            if not goal_handle.accepted:
                self.get_logger().error("Goal nebyl přijat.")
                return None

            self.get_logger().info("Goal přijat, čekám na výsledek.")
            future_result = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, future_result)
            result = future_result.result().result
            self.get_logger().info(f"Výsledek akce: {result}")
            return result
        
        except Exception as e:
            self.get_logger().error(f"Chyba při zpracování goalu: {e}")
            return None
    
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
    
    def publish_head(self, joint_1, joint_2):
        head_msg = JointTrajectory()

        head_msg.joint_names = ["head_1_joint", "head_2_joint"]
        point = JointTrajectoryPoint()
        if joint_1 > 1.0 or joint_1 < -1.0:
            return
        
        if joint_2 > 0.6 or joint_2 < -0.92:
            return
        
        point.positions = [
            joint_1,
            joint_2
        ]
        point.velocities = []
        point.effort = []
        point.time_from_start = Duration(sec=2, nanosec=0)
        head_msg.points = [point]

        self.head_joint_pub.publish(head_msg)

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

    def publish_torso(self, value):
        torso_msg = JointTrajectory()
        torso_msg.joint_names = ["torso_lift_joint"]
        point_torso = JointTrajectoryPoint()
        if value < 0.1 or value > 0.3:
            return 
        point_torso.positions = [value]
        point_torso.time_from_start = Duration(sec=5, nanosec=0)
        torso_msg.points = [point_torso]
        self.torso_pub.publish(torso_msg)

    def home_position(self):
        self.publish_head(0.0, 0.0)
        self.publish_torso(0.15)
        self.send_goal_joints("left", 8, -1.1, 1.47, 2.71, 1.71, -1.57, 1.39, 0.0)
        self.send_goal_joints("right", 8, -1.1, 1.47, 2.71, 1.71, -1.57, 1.39, 0.0)
        time.sleep(8)

    def screen_pointing(self):
        self.send_goal_joints("left", 5, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        self.send_goal_joints("right", 5, 0.25, -0.86, 1.52, 1.86, -1.46, 1.39, 0.0)
        time.sleep(5)

    def shake_hand(self):
        self.send_goal_joints("right", 3, 0.32, 1.35, 1.43, 1.76, -1.4, 1.39, 0.0)
        time.sleep(3)
        self.send_goal_joints("right", 1, 0.32, 1.35, 1.43, 1.76, -0.85, 1.39, 0.0)
        time.sleep(1)
        self.send_goal_joints("right", 1, 0.32, 1.35, 1.43, 1.76, -1.94, 1.39, 0.0)
        time.sleep(1)
        self.send_goal_joints("right", 1, 0.32, 1.35, 1.43, 1.76, -0.85, 1.39, 0.0)
        time.sleep(1)
        self.send_goal_joints("right", 1, 0.32, 1.35, 1.43, 1.76, -1.4, 1.39, 0.0)
        time.sleep(1)

    def placak(self):
        self.send_goal_joints("right", 4, 1.37, -0.06, 0.04, 1.24, -1.44, 0.54, 0.0)
        time.sleep(4)
        self.send_goal_joints("right", 1, 1.37, -0.06, 0.04, 1.24, -1.44, 0.0, 0.0)
        time.sleep(2)

def spin_listener(node):
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.1)
        time.sleep(0.01)  # malá pauza, aby se vlákno nepřetěžovalo
        if getattr(node, 'message_received', False):
            print("Message received")
            time.sleep(11.0)
            node.message_received = False

def main(args=None):
    rclpy.init(args=args)
    node_move = MoveClient()
    rclpy.spin_once(node_move, timeout_sec=0.1)
    node_depth = DepthTo3DNode()
    node_center = YoloDetectionHandler()
    node_speech = TextToSpeechNode()
    spin_duration = 5.0

    # listener_thread = threading.Thread(target=spin_listener, args=(node_move,), daemon=True)
    # listener_thread.start()

    try:
        node_move.open_gripper('left')
        node_move.open_gripper('right')

        # #HIGH FIVE
        # msg = Bool()
        # msg.data = True
        # node_move.stop_publisher_.publish(msg)
        # node_speech.call_speech("I am going to give you high five to visitors")
        # time.sleep(1)
        # node_move.placak()
        # node_move.home_position()
        # msg.data = False
        # node_move.stop_publisher_.publish(msg)

        # #POINTING PICTURE
        # msg.data = True
        # node_move.stop_publisher_.publish(msg)
        # node_move.publish_torso(0.25)
        # time.sleep(2)
        # node_move.publish_head(0.98,0.33)
        # rclpy.spin_once(node_move)
        # future = node_move.send_goal_joints("left", 8, 0.05,-0.5,-0.03,0.21,-1.57,-0.14,0.0)
        # rclpy.spin_until_future_complete(node_move, future)
        # rclpy.spin_once(node_move)
        # future = node_move.send_goal_joints("right", 8, 0.99, 0.18, 1.35, 1.93, -0.23, 0.18,-1.74)
        # rclpy.spin_until_future_complete(node_move, future)
        # #node_move.publish_base(0.1, "angular", 2)
        # node_move.publish_head(0.0, 0.0)

        # #AUTONOMOUS MOVE
        # node_move.home_position()
        # #node_move.publish_base(-0.1, "angular", 2)
        # msg.data = False
        # node_move.stop_publisher_.publish(msg)
        
        # #SCREEN POINTING
        # msg.data = True
        # node_move.stop_publisher_.publish(msg)
        # node_move.screen_pointing()

        #GRASPING
        #node_move.home_position()
        node_move.publish_head(0.5,-0.91)
        #time.sleep(3)
        trans_point = None
        start_time = time.time()
        while time.time() - start_time < spin_duration:
            rclpy.spin_once(node_depth)
            trans_point = node_depth.return_trans_point()
            if trans_point is not None:
                pose_point = trans_point
                break

        pose_grasp = PoseStamped()
        pose_grasp.header.frame_id = "base_footprint"
        pose_grasp.pose.orientation.x = -0.32
        pose_grasp.pose.orientation.y = -0.02
        pose_grasp.pose.orientation.z = 0.03
        pose_grasp.pose.orientation.w = 0.945
        pose_grasp.pose.position.x = 0.1
        pose_grasp.pose.position.y = 0.63
        pose_grasp.pose.position.z = 0.78

        #rclpy.spin_once(node_move)
        result = node_move.send_goal("left", pose_grasp)

        pose_goal1 = PoseStamped()
        pose_goal1.header.frame_id = "base_footprint"
        pose_goal1.pose.orientation.x = 0.5#0.5067372918128967
        pose_goal1.pose.orientation.y = 0.5#0.49766454100608826
        pose_goal1.pose.orientation.z = -0.5#-0.49749240279197693
        pose_goal1.pose.orientation.w = 0.5#0.4977000653743744
        pose_goal1.pose.position.x = pose_point.point.x + 0.02
        pose_goal1.pose.position.y = pose_point.point.y
        pose_goal1.pose.position.z = 0.74 # Here let's SEE what we will enter
        
        pose_goal2 = PoseStamped()
        pose_goal2.header.frame_id = "base_footprint"
        pose_goal2.pose.orientation.x = 0.5#0.5067372918128967
        pose_goal2.pose.orientation.y = 0.5#0.49766454100608826
        pose_goal2.pose.orientation.z = -0.5#-0.49749240279197693
        pose_goal2.pose.orientation.w = 0.5#0.4977000653743744
        pose_goal2.pose.position.x = pose_point.point.x + 0.02
        pose_goal2.pose.position.y = pose_point.point.y
        pose_goal2.pose.position.z = 0.56 #0.57 # Here let's SEE what we will enter
        
        pos = [pose_goal1, pose_goal2]
        rclpy.spin_once(node_move)
        node_move.send_goal_car("left", pos)
        node_move.close_gripper('left')
        
        pose_goal_up = PoseStamped()
        pose_goal_up.header.frame_id = "base_footprint"
        pose_goal_up.pose.orientation.x = 0.5 #0.5067372918128967
        pose_goal_up.pose.orientation.y = 0.5 #0.49766454100608826
        pose_goal_up.pose.orientation.z = -0.5 #-0.49749240279197693
        pose_goal_up.pose.orientation.w = 0.5 #0.4977000653743744
        pose_goal_up.pose.position.x = 0.413
        pose_goal_up.pose.position.y = 0.398
        pose_goal_up.pose.position.z = 0.815 # Here let's SEE what we will enter

        rclpy.spin_once(node_move)
        future = node_move.send_goal_joints("left",4,0.74,-0.74,2.06,1.33,0.85,-1.39,0.0)#1.79)
        rclpy.spin_until_future_complete(node_move, future)
        time.sleep(4)

        rclpy.spin_once(node_move)
        future = node_move.send_goal_joints()
        rclpy.spin_until_future_complete(node_move, future)
        
        #GIVE THE SHOE
        node_move.publish_base(0.1, "linear", 3)
        node_move.publish_head(0.0, 0.0)
        time.sleep(2)

        rclpy.spin_once(node_speech, timeout_sec=0.1)
        node_speech.call_speech("Who wants to take the shoe rise the hand?")
        time.sleep(2)

        while rclpy.ok():
            rclpy.spin_once(node_center, timeout_sec=0.1)
            target_detect = node_center.return_msg_target()
            if target_detect is not None:
                rclpy.spin_once(node_speech, timeout_sec=0.1)
                node_speech.call_speech("I detected you, I will give you the object.")
                break

        while rclpy.ok():
            rclpy.spin_once(node_center, timeout_sec=0.1)
            target_detect = node_center.return_msg_target()
            if target_detect is not None:
                break
        node_center.align_to_target()

        while True:
            rclpy.spin_once(node_center, timeout_sec=0.1)
            start_time = time.time()
            while time.time() - start_time < 3.0:
                node_center.go_robot()
                rclpy.spin_once(node_center, timeout_sec=0.1)
                laser_dis = node_center.return_msg_laser()
                if laser_dis is not None:
                    if laser_dis < 1.0:
                        break
                    
            if laser_dis is None or laser_dis > 1.0:
                continue

            rclpy.spin_once(node_center, timeout_sec=0.1)
            start_time = time.time()
            while time.time() - start_time < 3.0:
                node_center.go_robot()
                rclpy.spin_once(node_center, timeout_sec=0.1)
                laser_dis = node_center.return_msg_laser()
                if laser_dis is not None:
                    if laser_dis < 0.8:
                        break
            break

        if laser_dis is None:
            node_speech.call_speech("I failed to get the data from my laser. Please come closer.")
        time.sleep(2)
        rclpy.spin_once(node_speech, timeout_sec=0.1)
        node_speech.call_speech("Take the object please and wait for release the gripper.")
        time.sleep(3)
        node_move.open_gripper('left')
        time.sleep(1)
        node_speech.call_speech("Thank you for colaboration.")
        node_move.publish_base(-0.3, "linear", duration=3)

        
        #SHAKING HAND
        node_move.home_position()
        node_move.shake_hand()
        node_move.home_position()
        msg.data = False
        node_move.stop_publisher_.publish(msg)
        input("Check the test")

        #From Here real code, till here is only for testing
        while rclpy.ok():
            node_move.run()
            print(f'Tohle jse akce:( "{node_move.msg_action.action}" ))')
            if node_move.msg_action.action == "give_speech":
                print("Jsme spravne a cekame")
                time.sleep(8)
            
            if node_move.msg_action.action == "show_object":
                break
        # node_move.publish_base(0.3, "angluar", duration=4)
        # node_move.publish_head(0.95, 0.5)

        # time.sleep(5)

        # node_move.publish_base(-0.3, "angluar", duration=4)
        # node_move.publish_head(0.0, 0.0)
        
        # input("Jsme venku")

        node_move.publish_base(0.3, "angluar", duration=4)
        node_move.publish_torso(0.06)
        node_move.publish_head(0.6, -0.91)
        time.sleep(3)
        while rclpy.ok():
            #First loop!
            while True:
                rclpy.spin_once(node_speech, timeout_sec=0.1)
                node_speech.call_speech("I will try to grasp the object.")
                time.sleep(1)

                # 1. Action for recognize the object the object. --WORKING - ONLY THE HEAD MOVEMENT WE CAN SETUP
                trans_point = None
                start_time = time.time()
                while time.time() - start_time < spin_duration:
                    rclpy.spin_once(node_depth)
                    trans_point = node_depth.return_trans_point()
                    if trans_point is not None:
                        pose_point = trans_point
                        break
                
                if trans_point is None:
                    node_move.publish_base(0.1, "angluar", duration=1)
                    time.sleep(1)
                    continue

                # 2. Action for grasp the object.
                pose_grasp = PoseStamped()
                pose_grasp.header.frame_id = "base_footprint"
                pose_grasp.pose.orientation.x = -0.32
                pose_grasp.pose.orientation.y = -0.02
                pose_grasp.pose.orientation.z = 0.03
                pose_grasp.pose.orientation.w = 0.945
                pose_grasp.pose.position.x = 0.1
                pose_grasp.pose.position.y = 0.63     
                pose_grasp.pose.position.z = 0.78

                rclpy.spin_once(node_move, timeout_sec=0.1)
                start_time = time.time()
                while time.time() - start_time < spin_duration:
                    #rclpy.spin_once(node_move)
                    result = node_move.send_goal("left", pose_grasp)
                    if result is None or result.success == False:
                        print("Check becasue failed in planning")
                    else:
                        break
                
                if result is None or result.success == False:
                    continue
                    

                pose_goal1 = PoseStamped()
                pose_goal1.header.frame_id = "base_footprint"
                pose_goal1.pose.orientation.x = 0.5#0.5067372918128967
                pose_goal1.pose.orientation.y = 0.5#0.49766454100608826
                pose_goal1.pose.orientation.z = -0.5#-0.49749240279197693
                pose_goal1.pose.orientation.w = 0.5#0.4977000653743744
                pose_goal1.pose.position.x = pose_point.point.x + 0.02
                pose_goal1.pose.position.y = pose_point.point.y
                pose_goal1.pose.position.z = 0.74 # Here let's SEE what we will enter

                pose_goal2 = PoseStamped()
                pose_goal2.header.frame_id = "base_footprint"
                pose_goal2.pose.orientation.x = 0.5#0.5067372918128967
                pose_goal2.pose.orientation.y = 0.5#0.49766454100608826
                pose_goal2.pose.orientation.z = -0.5#-0.49749240279197693
                pose_goal2.pose.orientation.w = 0.5#0.4977000653743744
                pose_goal2.pose.position.x = pose_point.point.x + 0.02
                pose_goal2.pose.position.y = pose_point.point.y
                pose_goal2.pose.position.z = 0.57 #0.715 # Here let's SEE what we will enter

                pos = [pose_goal1, pose_goal2]
                rclpy.spin_once(node_move, timeout_sec=0.1)
                node_move.send_goal_car("left", pos)
                node_move.close_gripper('left')

                # pose_goal_up = PoseStamped()
                # pose_goal_up.header.frame_id = "base_footprint"
                # pose_goal_up.pose.orientation.x = 0.5 #0.5067372918128967
                # pose_goal_up.pose.orientation.y = 0.5 #0.49766454100608826
                # pose_goal_up.pose.orientation.z = -0.5 #-0.49749240279197693
                # pose_goal_up.pose.orientation.w = 0.5 #0.4977000653743744
                # pose_goal_up.pose.position.x = pose_point.point.x + 0.02
                # pose_goal_up.pose.position.y = pose_point.point.y
                # pose_goal_up.pose.position.z = 0.7 # Here let's SEE what we will enter

                pose_goal_up = PoseStamped()
                pose_goal_up.header.frame_id = "base_footprint"
                pose_goal_up.pose.position.x = 0.629
                pose_goal_up.pose.position.y = 0.438
                pose_goal_up.pose.position.z = 0.96
                pose_goal_up.pose.orientation.x = -0.72
                pose_goal_up.pose.orientation.y = -0.047
                pose_goal_up.pose.orientation.z = -0.03
                pose_goal_up.pose.orientation.w = 0.68

                #pos = [pose_goal_up, pose_goal]
                rclpy.spin_once(node_move, timeout_sec=0.1)
                start_time = time.time()
                while time.time() - start_time < spin_duration:
                    #rclpy.spin_once(node_move)
                    result = node_move.send_goal("left", pose_goal_up)
                    if result is None or result.success == False:
                        print("Check becasue failed in planning")
                    else:
                        break
                
                if result is None or result.success == False:
                    continue
                    
                # node_move.close_gripper('left')
                # pose_goal = PoseStamped()
                # pose_goal.header.frame_id = "base_footprint"
                # pose_goal.pose.orientation.x = 0.5067372918128967
                # pose_goal.pose.orientation.y = 0.49766454100608826
                # pose_goal.pose.orientation.z = -0.49749240279197693
                # pose_goal.pose.orientation.w = 0.4977000653743744
                # pose_goal.pose.position.x = pose_point.point.x + 0.02
                # pose_goal.pose.position.y = pose_point.point.y
                # pose_goal.pose.position.z = 0.95 # Here let's SEE what we will enter

                # rclpy.spin_once(node_move, timeout_sec=0.1)
                # start_time = time.time()
                # while time.time() - start_time < spin_duration:
                #     #rclpy.spin_once(node_move)
                #     result = node_move.send_goal("left", pose_goal)
                #     if result is None or result.success == False:
                #         print("Check becasue failed in planning")
                #     else:
                #         break
                
                # if result is None or result.success == False:
                #     continue

                node_move.publish_torso(0.2)
                node_move.publish_head(0.6, 0.0)

                # Checking if we hold the object
                start_time = time.time()
                while time.time() - start_time < spin_duration:
                    rclpy.spin_once(node_move, timeout_sec=0.1)
                    force_wrist = node_move.return_force()
                    if force_wrist is not None:
                        break

                if force_wrist > 30:
                    break
            
            node_move.publish_base(-0.3, "angluar", duration=4)
            node_move.publish_head(0.0,0.0)
            time.sleep(2)

            #Second loop!
            while True:
                start_time = time.time()
                while time.time() - start_time < spin_duration:
                    rclpy.spin_once(node_center, timeout_sec=0.1)
                    laser_dis = node_center.return_msg_laser()
                    if laser_dis is not None:
                            break
                
                if laser_dis is None or laser_dis < 0.8:
                    node_move.publish_base(-0.1, "angluar", duration=2)
                    time.sleep(1)
                    continue

                else:
                    node_move.publish_base(0.1, "linear", duration=2)
                    break


            pose_goal = PoseStamped()
            pose_goal.header.frame_id = "base_footprint"
            pose_goal.pose.position.x = 0.66
            pose_goal.pose.position.y = 0.42
            pose_goal.pose.position.z = 0.91
            pose_goal.pose.orientation.x = 0.13
            pose_goal.pose.orientation.y = -0.11
            pose_goal.pose.orientation.z = -0.09
            pose_goal.pose.orientation.w = 0.98

            rclpy.spin_once(node_move, timeout_sec=0.1)
            start_time = time.time()
            while time.time() - start_time < spin_duration:
                #rclpy.spin_once(node_move)
                result = node_move.send_goal("left", pose_goal)
                if result is None or result.success == False:
                    print("Check becasue failed in planning")
                else:
                    break

            # 3. Ask who want to take the object.
            rclpy.spin_once(node_speech, timeout_sec=0.1)
            node_speech.call_speech("Who wants to take the shoe rise the hand?")
            time.sleep(2)

            # 4. Action for detect a person.
            while rclpy.ok():
                rclpy.spin_once(node_center, timeout_sec=0.1)
                target_detect = node_center.return_msg_target()
                if target_detect is not None:
                    rclpy.spin_once(node_speech, timeout_sec=0.1)
                    node_speech.call_speech("I detected you, I will give you the object.")
                    break
            
            # 5. Action for center the robot and give the object.
            while rclpy.ok():
                    rclpy.spin_once(node_center, timeout_sec=0.1)
                    target_detect = node_center.return_msg_target()
                    if target_detect is not None:
                        break
            node_center.align_to_target()

            #Third loop!
            while True:
                rclpy.spin_once(node_center, timeout_sec=0.1)
                start_time = time.time()
                while time.time() - start_time < 3.0:
                    node_center.go_robot()
                    rclpy.spin_once(node_center, timeout_sec=0.1)
                    laser_dis = node_center.return_msg_laser()
                    if laser_dis is not None:
                        if laser_dis < 1.0:
                            break
                    
                if laser_dis is None or laser_dis > 1.0:
                    continue

                rclpy.spin_once(node_center, timeout_sec=0.1)
                start_time = time.time()
                while time.time() - start_time < 3.0:
                    node_center.go_robot()
                    rclpy.spin_once(node_center, timeout_sec=0.1)
                    laser_dis = node_center.return_msg_laser()
                    if laser_dis is not None:
                        if laser_dis < 0.8:
                            break
                break
            break

        # 5. Give the object to the person and return to base position.
        rclpy.spin_once(node_speech, timeout_sec=0.1)
        node_speech.call_speech("Take the object please and wait for release the gripper.")
        time.sleep(6)
        node_move.open_gripper('left')
        time.sleep(2)
        node_move.publish_base(-0.3, "linear", duration=3)
        node_speech.call_speech("Thank you for colaboration.")
                

    except KeyboardInterrupt:
        node_move.get_logger().info('Controll program stopped.')
    finally:
        node_move.destroy_node()
        rclpy.shutdown()
        #listener_thread.join()


if __name__ == '__main__':
    main()