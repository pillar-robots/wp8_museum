import rclpy
from rclpy.node import Node
from rclpy.task import Future
from geometry_msgs.msg import Twist, TwistStamped
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from builtin_interfaces.msg import Duration
import random
import time
from std_msgs.msg import Bool

class AutonomousMovement(Node):
    def __init__(self):
        super().__init__('action_autonomous_move')

        # Stavové proměnné
        self.stop_signal = False
        self.movement_history = [] 
        self.done_future = Future()
        
        # Publishers
        self.head_joint_pub = self.create_publisher(JointTrajectory, '/head_controller/joint_trajectory', 0)
        self.torso_pub = self.create_publisher(JointTrajectory, '/torso_controller/joint_trajectory', 0)
        self.mobile_base_pub = self.create_publisher(TwistStamped, '/mobile_base_controller/cmd_vel', 0)

        # Parametry stavového automatu
        self.state = "publishing"
        self.state_start_time = time.time()
        
        self.current_w = random.uniform(-0.1, 0.1)  # Úhlová rychlost
        self.current_duration = random.uniform(1.0, 2.0)

        # Subscription na stop signál
        self.subscription = self.create_subscription(
            Bool, '/stop_signal', self.listener_callback_action, 0
        )

        self.get_logger().info("Autonomous Robot Node Started")
        self.loop_timer = self.create_timer(0.1, self.loop_callback)

    def listener_callback_action(self, msg):
        self.stop_signal = msg.data
        if self.stop_signal and self.state != "returning":
            self.get_logger().warn("STOP SIGNAL: Initiating return home sequence!")
            self.start_return_sequence()

    def publish_head(self, joint_1, joint_2):
        msg = JointTrajectory()
        msg.joint_names = ["head_1_joint", "head_2_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(joint_1), float(joint_2)]
        point.time_from_start = Duration(sec=2, nanosec=0)
        msg.points = [point]
        self.head_joint_pub.publish(msg)

    def publish_torso(self, height):
        height = max(0.1, min(height, 0.2))
        msg = JointTrajectory()
        msg.joint_names = ["torso_lift_joint"]
        point = JointTrajectoryPoint()
        point.positions = [float(height)]
        point.time_from_start = Duration(sec=2, nanosec=0)
        msg.points = [point]
        self.torso_pub.publish(msg)

    def stop_robot(self):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.twist = Twist()
        self.mobile_base_pub.publish(msg)

    def start_return_sequence(self):
        self.state = "returning"
        self.state_start_time = time.time()
        # Při návratu narovnáme tělo
        self.publish_head(0.0, 0.0)
        self.publish_torso(0.15) 

    def loop_callback(self):
        current_time = time.time()
        elapsed = current_time - self.state_start_time

        # --- STAV: POHYB (Ukládání do historie) ---
        if self.state == "publishing":
            if elapsed < self.current_duration:
                msg = TwistStamped()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.twist.angular.z = self.current_w
                self.mobile_base_pub.publish(msg)
            else:
                # Konec úseku - uložit do paměti a pauza
                self.movement_history.append((self.current_w, elapsed))
                self.stop_robot()
                self.state = "pausing"
                self.state_start_time = current_time
                self.current_duration = random.uniform(1.0, 2.0)
                self.get_logger().info(f"Step saved. Total steps in memory: {len(self.movement_history)}")

        # --- STAV: PAUZA (Náhodné pohyby těla) ---
        elif self.state == "pausing":
            if elapsed >= self.current_duration:
                # Rozhodnutí: Pokračovat nebo se už vrátit? (např. po 6 krocích)
                if len(self.movement_history) >= random.randint(1,3):
                    self.start_return_sequence()
                else:
                    self.current_w = random.uniform(-0.1, 0.1)
                    self.current_duration = random.uniform(1.0, 2.0)
                    
                    # Náhodný pohyb tělem v pauze
                    self.publish_head(random.uniform(-0.8, 0.8), random.uniform(-0.2, 0.2))
                    self.publish_torso(random.uniform(0.1, 0.2))
                    
                    self.state = "publishing"
                    self.state_start_time = current_time

        # --- STAV: NÁVRAT (Inverzní pohyby ze stacku) ---
        elif self.state == "returning":
            if not self.movement_history:
                self.get_logger().info("Robot is BACK HOME. Sleeping.")
                self.stop_robot()
                if not self.done_future.done():
                    self.done_future.set_result(True)

                return

            # Poslední pohyb ze seznamu
            w, dur = self.movement_history[-1]

            if elapsed < dur:
                # Provádíme opačný pohyb
                msg = TwistStamped()
                msg.header.stamp = self.get_clock().now().to_msg()
                msg.twist.angular.z = -w
                self.mobile_base_pub.publish(msg)
            else:
                # Tento úsek návratu je hotov
                self.movement_history.pop()
                self.stop_robot()
                self.state_start_time = current_time
                self.get_logger().info(f"Undo step complete. Steps left: {len(self.movement_history)}")

def main(args=None):
    rclpy.init(args=args)
    node = AutonomousMovement()
    rclpy.spin_until_future_complete(node, node.done_future)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()