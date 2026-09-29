import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

import requests
import os
import json
import threading
import time

class VlmApiNode(Node):
    def __init__(self):
        super().__init__('vlm_api_publisher')
        
        # 1. Vytvoření ROS publisherů (Float32)
        self.pub_age = self.create_publisher(Float32, 'vlm/age_composition', 2)
        self.pub_spatial = self.create_publisher(Float32, 'vlm/spatial_formation', 2)
        self.pub_interpersonal = self.create_publisher(Float32, 'vlm/interpersonal_spacing', 2)
        self.pub_postural = self.create_publisher(Float32, 'vlm/postural_assessment', 2)
        self.pub_area = self.create_publisher(Float32, 'vlm/blue_area', 2)
        self.pub_engagement = self.create_publisher(Float32, 'vlm/engagement_rating', 2)
        
        # 2. Slovník pro převod textu na Float
        # Zde si doplň všechny možné varianty odpovědí od tvého modelu
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
                "In a Row": 0.9,
                "Not in a Row": 0.1,
                "Not Observed": -1.0
            },
            "Interpersonal spacing": {
                "Close": 0.9,
                "Separated": 0.1,
                "Not Observed": -1.0
            },
            "Postural assessment": {
                "Standing Only": 0.9,
                "Mixed (Standing/Seated)": 0.5,
                "Primarily Seated": 0.1,
                "Not Observed": -1.0
            },
            "Blue area positioning": {
                "Inside Blue Area": 1.0,
                "Outside Blue Area": 0.1,
                "Mixed/On Boundary": 0.5,
                "Not Blue Area Visible": -1.0,
                "Not Observed": -1.0
            },
            "Engagement rating": {
                "High Engagement": 1.0,
                "Moderate Engagement": 0.6,
                "Low Engagement": 0.3,
                "Passive/Observation Only": 0.0,
                "Not Observed": -1.0
            }
        }
        
        # Nastavení
        self.url = "http://127.0.0.1:5555/api/relations"
        #self.output_folder = "output_frames"
        #self.image_name = "frame_0002.png"
        self.filename = "/home/citic_lab/qwen3_museum/output_frames/art.jpg"

        
        # Data k odeslání
        self.data = {
            "message": {
                "text": "Describe the interaction with the guide",
                "files": [self.filename]
            }
        }

        # 3. Spuštění API smyčky v samostatném vlákně, aby neblokovala ROS spin
        self.get_logger().info("Spouštím VLM API Node...")
        self.api_thread = threading.Thread(target=self.api_loop, daemon=True)
        self.api_thread.start()

    def map_to_float(self, category, text_value):
        """Převede textovou odpověď na float podle slovníku. Pokud nenajde, vrátí -1.0"""
        return float(self.mapping.get(category, {}).get(text_value, -1.0))

    def api_loop(self):
        """Nekonečná smyčka, která posílá dotazy na API a publikuje výsledky."""
        while rclpy.ok():
            if not os.path.exists(self.filename):
                self.get_logger().error(f"Soubor '{self.filename}' nebyl nalezen. Čekám 2s...", throttle_duration_sec=2)
                time.sleep(2)
                continue

            try:
                self.get_logger().info("Odesílám prompt na API...")
                res = requests.post(self.url, json=self.data) 
                
                if res.status_code == 200:
                    self.process_and_publish(res.json())
                    print(res.json())
                else:
                    self.get_logger().error(f"Chyba API: {res.status_code} - {res.text}")
                    timeout_data = {
                        "Age composition": "Not Observed",
                        "Spatial formation": "Not Observed",
                        "Interpersonal spacing": "Not Observed",
                        "Postural assessment": "Not Observed",
                        "Blue area positioning": "Not Observed",
                        "Engagement rating": "Not Observed"
                    }
                    self.process_and_publish(timeout_data)
                    
            except requests.exceptions.ConnectionError:
                self.get_logger().error("Nepodařilo se připojit k API. Běží server na portu 5555?", throttle_duration_sec=5)
            except Exception as e:
                self.get_logger().error(f"Nečekaná chyba: {str(e)}")

    def process_and_publish(self, raw_data):
        """Zpracuje JSON a vy-publikuje float hodnoty do topiců."""
        processed_entry = {}
        
        # Očištění případného markdownu, pokud AI ignorovala "No Markdown" pravidlo
        if isinstance(raw_data, str):
            try:
                clean_str = raw_data.replace("```json", "").replace("```", "").strip()
                raw_data = json.loads(clean_str)
            except:
                raw_data = {}

        if "results" in raw_data and isinstance(raw_data["results"], list):
            for part in raw_data["results"]:
                processed_entry.update(part)
        else:
            processed_entry = raw_data

        # Vytvoření a publikování zpráv
        msg_age = Float32()
        msg_age.data = self.map_to_float("Age composition", processed_entry.get("Age composition", ""))
        self.pub_age.publish(msg_age)

        msg_spatial = Float32()
        msg_spatial.data = self.map_to_float("Spatial formation", processed_entry.get("Spatial formation", ""))
        self.pub_spatial.publish(msg_spatial)

        msg_interpersonal = Float32()
        msg_interpersonal.data = self.map_to_float("Interpersonal spacing", processed_entry.get("Interpersonal spacing", ""))
        self.pub_interpersonal.publish(msg_interpersonal)

        msg_postural = Float32()
        msg_postural.data = self.map_to_float("Postural assessment", processed_entry.get("Postural assessment", ""))
        self.pub_postural.publish(msg_postural)

        msg_blue = Float32()
        msg_blue.data = self.map_to_float("Blue area positioning", processed_entry.get("Blue are positioning", ""))
        self.pub_area.publish(msg_blue)

        msg_engagement = Float32()
        msg_engagement.data = self.map_to_float("Engagement rating", processed_entry.get("Engagement rating", ""))
        self.pub_engagement.publish(msg_engagement)
        
        self.get_logger().info("Data úspěšně publikována do ROS2 topiců.")

def main(args=None):
    rclpy.init(args=args)
    node = VlmApiNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Ukončuji node...")
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()