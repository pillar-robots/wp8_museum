import json
import threading
from copy import deepcopy
from pathlib import Path
import requests
import time
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32
import cv2
from cv_bridge import CvBridge

ANALYSIS_FIELDS = [
    "Age composition",
    "Spatial formation",
    "Interpersonal spacing",
    "Postural assessment",
    "Area positioning",
    "Engagement rating",
]

SMOOTHING_PRIORITY = [
    "Area positioning",
    "Postural assessment",
    "Spatial formation",
    "Interpersonal spacing",
    "Engagement rating",
    "Age composition",
]

class VLMProcessorNode(Node):
    def __init__(self):
        super().__init__('vlm_processor_node')

        self.declare_parameter('image_path', '/home/citic_lab/Pictures/Webcam/2026-06-25-153254.jpg')
        self.declare_parameter('api_url', 'http://127.0.0.1:5555/api/relations')
        self.declare_parameter('model', 'qwen3.5:9b')

        self.is_processing = False
        self.lock = threading.Lock()
        self.bridge = CvBridge()
        self.previous_vlm_state = None
        self.image_path = "/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/picture/image.jpg"

        self.image_sub = self.create_subscription(Image, '/camera/camera/color/image_raw', self.camera_callback, 0)
        self.people_sub = self.create_subscription(Float32, '/exhibition/people', self.people_callback, 0)
        self.timeline_sub = self.create_subscription(Float32, '/exhibition/timeline', self.timeline_callback, 0)
        self.people_count = 0.0
        self.timeline_count = 0.0
        self.people_threshold = 0.1
        self.next_allowed_time = 0.0

        # self.timer = self.create_timer(0.1, self.timer_callback)

        self.vlm_pub = self.create_publisher(String, 'vlm/output', 0)

        self.pub_age = self.create_publisher(Float32, 'vlm/age_composition', 2)
        self.pub_spatial = self.create_publisher(Float32, 'vlm/spatial_formation', 2)
        self.pub_interpersonal = self.create_publisher(Float32, 'vlm/interpersonal_spacing', 2)
        self.pub_postural = self.create_publisher(Float32, 'vlm/postural_assessment', 2)
        self.pub_area = self.create_publisher(Float32, 'vlm/blue_area', 2)
        self.pub_engagement = self.create_publisher(Float32, 'vlm/engagement_rating', 2)

        self.mapping = {
            "Age composition": {
                "Kids": 0.1,
                "Adolescents": 0.2,
                "Primarily Young Adults": 0.3,
                "Primarily Middle-Aged": 0.4,
                "Seniors/Older Adults": 0.7,
                "Mixed People": 0.5,
                "Mixed Adults": 0.6,
                "Not Observed": -1.0
            },
            "Spatial formation": {
                "In a Row": 0.7,
                "Not in a Row": 0.3,
                "Not Observed": -1.0
            },
            "Interpersonal spacing": {
                "Close": 0.8,
                "Separate": 0.2,
                "Not Observed": -1.0
            },
            "Postural assessment": {
                "Standing Only": 0.8,
                "Mixed (Standing/Seated)": 0.5,
                "Sitting Only": 0.2,
                "Not Observed": -1.0
            },
            "Engagement rating": {
                "High Engagement": 0.8,
                "Moderate Engagement": 0.6,
                "Low Engagement": 0.4,
                "Passive/Observation Only": 0.2,
                "Not Observed": -1.0
            }
        }

        self.get_logger().info("VLM Processor Node has started. Waiting for images...")

    def people_callback(self, msg):
        self.people_count = msg.data
    
    def timeline_callback(self, msg):
        self.timeline_count = msg.data

    def timer_callback(self):
        with self.lock:
            if self.is_processing:
                return
            self.is_processing = True

        image_path_str = (
            self.get_parameter('image_path')
            .get_parameter_value()
            .string_value
        )

        self.get_logger().info("Processing image from file...")

        threading.Thread(target=self.call_vlm_api, args=(image_path_str,), daemon=True).start()

    def camera_callback(self, msg):
        if time.time() < self.next_allowed_time:
            return
        if self.timeline_count == 0.0:
            self.publish_zero_output()
            return
        with self.lock:
            if self.is_processing:
                return
            self.is_processing = True

        cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        cv_image = cv2.rotate(cv_image, cv2.ROTATE_180) #pouze otoci kameru
        # h, w = cv_image.shape[:2]
        # offset = 150
        # x1 = max(0, w//4 - offset)
        # x2 = min(w, 3*w//4 - offset)
        # cv_image = cv_image[h//4:3*h//2, x1:x2]
        cv2.imwrite(self.image_path, cv_image)
        
        self.get_logger().info("New frame grabbed. Starting VLM prompt...")

        threading.Thread(target=self.call_vlm_api, args=(self.image_path,), daemon=True).start()

    def call_vlm_api(self, image_path_str):
        start_time = time.time()
        try:
            image_path = Path(image_path_str)
            if not image_path.exists():
                self.get_logger().error(f"Image not found: {image_path}")
                return

            api_url = self.get_parameter('api_url').get_parameter_value().string_value
            model = self.get_parameter('model').get_parameter_value().string_value

            payload = {
                "message": {
                    "text": "Describe the interaction with the guide",
                    "files": [str(image_path)],
                    "model": model,
                }
            }

            self.get_logger().info(f"Sending prompt to {model}...")
            response = requests.post(api_url, json=payload, timeout=120)
            response.raise_for_status()

            result_data = response.json()
            result_data = self.smooth_vlm_output(result_data)
            
            self.publish_vlm_output(result_data)

        except requests.exceptions.RequestException as e:
            self.get_logger().error(f"API Request failed: {e}")
        except Exception as e:
            self.get_logger().error(f"Unexpected error: {e}")
        finally:
            self.next_allowed_time = max(start_time + 10.0, time.time())
            with self.lock:
                self.is_processing = False
                self.get_logger().info("Ready for next frame.")
    
    def smooth_vlm_output(self, result_data):
        if not self.has_complete_analysis(result_data):
            return result_data

        if self.previous_vlm_state is None:
            self.previous_vlm_state = self.extract_analysis_state(result_data)
            return result_data

        new_state = self.extract_analysis_state(result_data)
        changed_fields = [
            field
            for field in ANALYSIS_FIELDS
            if new_state[field] != self.previous_vlm_state[field]
        ]

        if len(changed_fields) >= 2:
            selected_field = next(
                field for field in SMOOTHING_PRIORITY if field in changed_fields
            )
            smoothed_state = deepcopy(self.previous_vlm_state)
            smoothed_state[selected_field] = new_state[selected_field]

            smoothed_result = deepcopy(result_data)
            smoothed_result.update(smoothed_state)
            self.previous_vlm_state = smoothed_state

            self.get_logger().info(
                "LVLM output smoothing: "
                f"{len(changed_fields)} fields changed; applying only '{selected_field}'."
            )
            return smoothed_result

        self.previous_vlm_state = new_state
        return result_data
    
    def has_complete_analysis(self, result_data):
        return (
            isinstance(result_data, dict)
            and all(field in result_data for field in ANALYSIS_FIELDS)
        )

    def extract_analysis_state(self, result_data):
        return {field: result_data[field] for field in ANALYSIS_FIELDS}

    def map_to_float(self, category, text_value):
        return float(self.mapping.get(category, {}).get(text_value, -1.0))

    def publish_vlm_output(self, result_data):
        output_str = json.dumps(result_data, indent=2)
        self.get_logger().info(f"VLM Response:\n{output_str}")
        
        msg_age = Float32()
        msg_age.data = self.map_to_float("Age composition", result_data.get("Age composition", ""))
        self.pub_age.publish(msg_age)

        msg_spatial = Float32()
        msg_spatial.data = self.map_to_float("Spatial formation", result_data.get("Spatial formation", ""))
        self.pub_spatial.publish(msg_spatial)

        msg_interpersonal = Float32()
        msg_interpersonal.data = self.map_to_float("Interpersonal spacing", result_data.get("Interpersonal spacing", ""))
        self.pub_interpersonal.publish(msg_interpersonal)

        msg_postural = Float32()
        msg_postural.data = self.map_to_float("Postural assessment", result_data.get("Postural assessment", ""))
        self.pub_postural.publish(msg_postural)

        msg_engagement = Float32()
        msg_engagement.data = self.map_to_float("Engagement rating", result_data.get("Engagement rating", ""))
        self.pub_engagement.publish(msg_engagement)

        msg_blue = Float32()
        msg_blue.data = float(result_data.get("Area positioning", ""))
        self.pub_area.publish(msg_blue)
        
        self.get_logger().info("Data úspěšně publikována do ROS2 topiců.")

    def publish_zero_output(self):
        msg = Float32()

        msg.data = 0.0
        self.pub_age.publish(msg)

        msg = Float32()
        msg.data = 0.0
        self.pub_spatial.publish(msg)

        msg = Float32()
        msg.data = 0.0
        self.pub_interpersonal.publish(msg)

        msg = Float32()
        msg.data = 0.0
        self.pub_postural.publish(msg)

        msg = Float32()
        msg.data = 0.0
        self.pub_engagement.publish(msg)

        msg = Float32()
        msg.data = 0.0
        self.pub_area.publish(msg)

        self.get_logger().info("No people detected. Published 0.0 to all VLM topics.")


def main(args=None):
    rclpy.init(args=args)
    node = VLMProcessorNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Node stopped gracefully.")
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == '__main__':
    main()