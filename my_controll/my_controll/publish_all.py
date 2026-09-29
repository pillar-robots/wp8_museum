import json
import threading
import time
import os
from copy import deepcopy
from pathlib import Path
import requests
import cv2
import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk
from cv_bridge import CvBridge
from ultralytics import YOLO
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import String, Float32, Bool
from datetime import datetime

# ── KONFIGURACE ───────────────────────────────────────────────────────────────
ANALYSIS_FIELDS = ["Spatial formation", "Interpersonal spacing", "Postural assessment", "Engagement rating"]

SMOOTHING_PRIORITY = ["Postural assessment", "Spatial formation", "Interpersonal spacing", "Engagement rating"]

GUI_TOPICS = [
    ("age", "/vlm/age_composition", 0.0),
    ("guide", "/exhibition/guide", 0.0),
    ("timeline", "/exhibition/timeline", 0.0),
    ("people", "/exhibition/people", 0.0),
]

TARGET_DEVICE_NAME = "wireless microphone"
RATE = 48000
BLOCK_SIZE = 1024
RMS_MIN = 0.003
LOUD_RMS = 0.015 #for pulse was 0.035
RMS_MAX = 0.1

PUBLISH_PERIOD = 2.0  # Jak často se vše publikuje (v sekundách)

TURNON_TOPIC = "/turnon"

# Detekce modrého boxu (HSV rozsah, lze doladit podle konkrétního odstínu modré)
BLUE_LOWER = np.array([90, 80, 80])
BLUE_UPPER = np.array([130, 255, 255])
POSE_MODEL_PATH = "/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/picture/yolov8n-pose.pt"


# ── ROS 2 MASTER NODE ─────────────────────────────────────────────────────────
class UnifiedExhibitionNode(Node):
    def __init__(self):
        super().__init__('unified_exhibition_node')

        # --- Parametry ---
        self.declare_parameter('image_path', '/home/citic_lab/Pictures/Webcam/2026-06-25-153254.jpg')
        self.declare_parameter('api_url', 'http://127.0.0.1:5555/api/relations')
        self.declare_parameter('model', 'qwen3.5:9b')

        self.bridge = CvBridge()
        self.image_path = "/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/picture/image.jpg"

        # --- Sdílený stav (Paměť) ---
        self.gui_values = {key: default for key, _, default in GUI_TOPICS}
        self.audio_rms_samples = []
        self.latest_audio_norm = 0.0
        self.audio_last_calc_time = time.time()
        self.vlm_latest_result = {}
        self.previous_vlm_state = None
        self.blue_area_score = 0.0

        self.video_dir = "/home/citic_lab/my_controll_migration_ws/src/my_controll/my_controll/picture"  # <-- tvoje složka
        os.makedirs(self.video_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.video_path = os.path.join(
            self.video_dir,
            f"camera_{timestamp}.mp4"
        )

        self.video_writer = None

        # --- Pose model pro detekci lidí v modrém boxu ---
        try:
            self.pose_model = YOLO(POSE_MODEL_PATH)
            self.get_logger().info(f"Pose model '{POSE_MODEL_PATH}' loaded.")
        except Exception as e:
            self.pose_model = None
            self.get_logger().error(f"Nepodařilo se načíst pose model: {e}")

        # --- Stav publikačního gatu (/turnon) ---
        # Dokud na /turnon nepřijde žádná zpráva (topic je "prázdný"),
        # bereme to jako by byl zapnutý -> publikuje se.
        self.turnon_enabled = True
        self.turnon_received = False

        # Zámky pro bezpečnost vláken
        self.vlm_processing_lock = threading.Lock()
        self.data_lock = threading.Lock()

        self.is_vlm_processing = False
        self.next_allowed_time = 0.0

        # --- GUI Publishery ---
        self.gui_pubs = {}
        for key, topic, _ in GUI_TOPICS:
            self.gui_pubs[key] = self.create_publisher(Float32, topic, 0)

        # --- Audio Publisher ---
        self.pub_noise = self.create_publisher(Float32, '/room/noise_level', 0)

        # --- VLM Publishery ---
        self.pub_vlm_str = self.create_publisher(String, 'vlm/output', 0)
        self.pub_spatial = self.create_publisher(Float32, 'vlm/spatial_formation', 0)
        self.pub_interpersonal = self.create_publisher(Float32, 'vlm/interpersonal_spacing', 0)
        self.pub_postural = self.create_publisher(Float32, 'vlm/postural_assessment', 0)
        self.pub_area = self.create_publisher(Float32, 'vlm/blue_area', 0)
        self.pub_engagement = self.create_publisher(Float32, 'vlm/engagement_rating', 0)

        # --- Kamera Subscriber ---
        self.image_sub = self.create_subscription(Image, '/camera/camera/color/image_raw', self.camera_callback, 0)

        # --- /turnon Subscriber (gate pro publikování) ---
        self.turnon_sub = self.create_subscription(Bool, TURNON_TOPIC, self.turnon_callback, 10)

        # --- Audio Setup ---
        self.device_id = self.select_audio_device()
        try:
            self.stream = sd.InputStream(
                device=self.device_id, channels=1, samplerate=RATE,
                blocksize=BLOCK_SIZE, callback=self.audio_callback
            )
            self.stream.start()
            self.get_logger().info(f'Mic is on with ID {self.device_id}')
        except Exception as e:
            self.get_logger().error(f'Audio INIT ERROR: {e}')

        # VLM Mapping tabulka
        self.mapping = {
            #"Age composition": {"Kids": 0.1, "Adolescents": 0.2, "Primarily Young Adults": 0.3, "Primarily Middle-Aged": 0.4, "Seniors/Older Adults": 0.7, "Mixed People": 0.5, "Mixed Adults": 0.6, "Not Observed": -1.0},
            "Spatial formation": {"In a Row": 0.7, "Not in a Row": 0.3, "Not Observed": -1.0},
            "Interpersonal spacing": {"Close": 0.8, "Separate": 0.2, "Not Observed": -1.0},
            "Postural assessment": {"Standing Only": 0.8, "Mixed (Standing/Seated)": 0.5, "Sitting Only": 0.2, "Not Observed": -1.0},
            "Engagement rating": {"High Engagement": 0.8, "Passive Engagement": 0.4, "Low Engagement": 0.2, "Not Observed": -1.0}
        }

        # --- Centrální Master Timer pro publikování VŠEHO ---
        self.master_timer = self.create_timer(PUBLISH_PERIOD, self.publish_all_data)
        self.get_logger().info("Unified Node started. Master timer running.")

    # ─── /turnon LOGIKA ───────────────────────────────────────────────────────
    def turnon_callback(self, msg: Bool):
        self.turnon_received = True
        self.turnon_enabled = bool(msg.data)
        self.get_logger().info(f"/turnon changed -> {self.turnon_enabled}")

    # ─── AUDIO LOGIKA ─────────────────────────────────────────────────────────
    def select_audio_device(self):
        try:
            for i, dev in enumerate(sd.query_devices()):
                if TARGET_DEVICE_NAME in dev['name'] and dev['max_input_channels'] > 0:
                    return i
        except Exception:
            pass
        return None

    def audio_callback(self, indata, frames, time_info, status):
        try:
            rms = np.sqrt(np.mean(indata[:, 0] ** 2))
            with self.data_lock:
                self.audio_rms_samples.append(rms)
        except Exception:
            pass

    # ─── BLUE BOX / POSE LOGIKA ───────────────────────────────────────────────
    def _detect_blue_box(self, image: np.ndarray):
        """Detekuje modrý obdélník (box) v obrázku a vrátí jeho bounding box (x1, y1, x2, y2)."""
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, BLUE_LOWER, BLUE_UPPER)

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.dilate(mask, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None

        largest = max(contours, key=lambda c: cv2.arcLength(c, True))
        x, y, w, h = cv2.boundingRect(largest)
        return x, y, x + w, y + h

    @staticmethod
    def _point_in_box(point, box):
        x, y = point
        x1, y1, x2, y2 = box
        return x1 <= x <= x2 and y1 <= y <= y2

    def _person_in_box(self, keypoints_xy, box, min_visible_points=1):
        """Rozhodne, jestli je osoba uvnitř boxu (podle kotníků, fallback na všechny keypointy)."""
        ankles_idx = [15, 16]  # levý a pravý kotník v COCO pose formátu
        ankle_points = [
            keypoints_xy[i] for i in ankles_idx
            if i < len(keypoints_xy) and not np.allclose(keypoints_xy[i], [0, 0])
        ]

        ref_points = ankle_points if ankle_points else [
            p for p in keypoints_xy if not np.allclose(p, [0, 0])
        ]
        if not ref_points:
            return False

        inside_count = sum(1 for p in ref_points if self._point_in_box(p, box))
        return inside_count >= min_visible_points

    def evaluate_blue_area(self, image: np.ndarray) -> float:
        """
        Spočítá poměr lidí uvnitř modrého boxu (stejná logika jako yolo_test.py):
        - detekuje modrý box
        - spustí pose model na obrázku
        - jedna osoba mimo box se odečte jako operátor
        - vrátí 0.8 pokud je uvnitř >= 50 % lidí, jinak 0.3 (0.0 pokud box nenalezen)
        """
        if self.pose_model is None:
            return 0.0

        box = self._detect_blue_box(image)
        if box is None:
            return 0.0

        results = self.pose_model(image, verbose=False)

        people_total = 0
        people_inside = 0
        for result in results:
            if result.keypoints is None:
                continue
            keypoints_all = result.keypoints.xy.cpu().numpy()
            people_total = len(keypoints_all)
            for kpts in keypoints_all:
                if self._person_in_box(kpts, box):
                    people_inside += 1

        people_outside = people_total - people_inside
        if people_outside > 0:
            people_total -= 1  # odečet operátora

        if people_total == 0:
            return 0.3

        ratio_inside = people_inside / people_total
        return 0.8 if ratio_inside >= 0.5 else 0.3

    def _update_blue_area(self, cv_image: np.ndarray):
        try:
            score = self.evaluate_blue_area(cv_image)
        except Exception as e:
            self.get_logger().error(f"Blue area evaluation error: {e}")
            score = 0.0
        with self.data_lock:
            self.blue_area_score = score

    # ─── KAMERA A VLM LOGIKA ──────────────────────────────────────────────────
    def camera_callback(self, msg):
        cv_image = self.bridge.imgmsg_to_cv2(msg,desired_encoding="bgr8")
        cv_image = cv2.rotate(cv_image, cv2.ROTATE_180)
        
        if self.video_writer is None:
            h, w = cv_image.shape[:2]
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")

            self.video_writer = cv2.VideoWriter(self.video_path,fourcc,30.0, (w, h))

            self.get_logger().info(
                f"Starting video recording: {self.video_path}")

        self.video_writer.write(cv_image)

        if time.time() < self.next_allowed_time:
            return

        # Nyní bereme hodnotu timeline přímo z paměti GUI!
        if self.gui_values["timeline"] == 0.0:
            with self.data_lock:
                self.vlm_latest_result = {}  # Vynutí publikování 0.0
            return

        with self.vlm_processing_lock:
            if self.is_vlm_processing:
                return
            self.is_vlm_processing = True

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
        threading.Thread(target=self._update_blue_area, args=(cv_image.copy(),), daemon=True).start()

    def call_vlm_api(self, image_path_str):
        start_time = time.time()
        try:
            image_path = Path(image_path_str)
            if not image_path.exists():
                return

            api_url = self.get_parameter('api_url').get_parameter_value().string_value
            model = self.get_parameter('model').get_parameter_value().string_value

            payload = {
                "message": {"text": "Describe the interaction with the guide", "files": [str(image_path)], "model": model}
            }

            response = requests.post(api_url, json=payload, timeout=120)
            response.raise_for_status()

            result_data = self.smooth_vlm_output(response.json())

            # Místo přímého publikování uložíme výsledek. Publikuje ho Master Timer.
            with self.data_lock:
                self.vlm_latest_result = result_data
                output_str = json.dumps(result_data, indent=2)
                self.get_logger().info(f"VLM Response:\n{output_str}")

            self.get_logger().info("VLM analysis complete and ready for next sync tick.")

        except Exception as e:
            self.get_logger().error(f"VLM API Error: {e}")
        finally:
            self.next_allowed_time = max(start_time + 10.0, time.time())
            with self.vlm_processing_lock:
                self.is_vlm_processing = False

    def smooth_vlm_output(self, result_data):
        if not (isinstance(result_data, dict) and all(f in result_data for f in ANALYSIS_FIELDS)):
            return result_data

        new_state = {f: result_data[f] for f in ANALYSIS_FIELDS}
        if self.previous_vlm_state is None:
            self.previous_vlm_state = new_state
            return result_data

        changed_fields = [f for f in ANALYSIS_FIELDS if new_state[f] != self.previous_vlm_state[f]]

        if len(changed_fields) >= 2:
            selected_field = next(f for f in SMOOTHING_PRIORITY if f in changed_fields)
            smoothed_state = deepcopy(self.previous_vlm_state)
            smoothed_state[selected_field] = new_state[selected_field]

            smoothed_result = deepcopy(result_data)
            smoothed_result.update(smoothed_state)
            self.previous_vlm_state = smoothed_state
            return smoothed_result

        self.previous_vlm_state = new_state
        return result_data

    def map_to_float(self, category, text_value):
        return float(self.mapping.get(category, {}).get(text_value, -1.0))

    # ─── MASTER PUBLISHER (Spouští se každé PUBLISH_PERIOD vteřiny) ───────────
    def publish_all_data(self):
        # ── Sběr / výpočet dat probíhá VŽDY, bez ohledu na /turnon ──
        current_time = time.time()

        # Výpočet audio průměru proběhne jen jednou za 6 vteřin (stejně jako doteď)
        if current_time - self.audio_last_calc_time >= 6.0:
            with self.data_lock:
                samples = list(self.audio_rms_samples)
                self.audio_rms_samples.clear()

            if samples:
                avg_rms = np.mean(samples)
                if avg_rms <= LOUD_RMS:
                    norm = 0.5 * (avg_rms - RMS_MIN) / (LOUD_RMS - RMS_MIN)
                else:
                    norm = 0.5 + 0.5 * (avg_rms - LOUD_RMS) / (RMS_MAX - LOUD_RMS)

                latest_audio = float(np.clip(norm, 0.0, 1.0))
                if latest_audio > 0.5:
                    self.latest_audio_norm = 0.8
                else:
                    self.latest_audio_norm = 0.3

            # Resetujeme časovač pro další výpočet audia
            self.audio_last_calc_time = current_time

        with self.data_lock:
            vlm_data = deepcopy(self.vlm_latest_result)

        # ── Od tohoto místa se pouze PUBLIKUJE ──
        # Publikuje se, když je /turnon True, NEBO když na něj ještě nikdy
        # nic nepřišlo (prázdný topic bez "data:" = bereme jako zapnuto).
        if self.turnon_received and not self.turnon_enabled:
            return

        msg = Float32()

        # 1. Publikování GUI dat
        for key, pub in self.gui_pubs.items():
            msg.data = float(self.gui_values[key])
            pub.publish(msg)

        # 2. Publikování hluku - pokud je timeline 0.0, vynutíme 0.0
        if self.gui_values["timeline"] == 0.0:
            msg.data = 0.0
        else:
            msg.data = self.latest_audio_norm

        self.pub_noise.publish(msg)

        # 3. Publikování VLM dat (Pokud je timeline 0, vypublikuje nuly)
        if not vlm_data or self.gui_values["timeline"] == 0.0:
            msg.data = 0.0
            #self.pub_age.publish(msg)
            self.pub_spatial.publish(msg)
            self.pub_interpersonal.publish(msg)
            self.pub_postural.publish(msg)
            self.pub_engagement.publish(msg)
        else:
            #self.pub_age.publish(Float32(data=self.map_to_float("Age composition", vlm_data.get("Age composition", ""))))
            self.pub_spatial.publish(Float32(data=self.map_to_float("Spatial formation", vlm_data.get("Spatial formation", ""))))
            self.pub_interpersonal.publish(Float32(data=self.map_to_float("Interpersonal spacing", vlm_data.get("Interpersonal spacing", ""))))
            self.pub_postural.publish(Float32(data=self.map_to_float("Postural assessment", vlm_data.get("Postural assessment", ""))))
            self.pub_engagement.publish(Float32(data=self.map_to_float("Engagement rating", vlm_data.get("Engagement rating", ""))))
            
            if 0.6 >= self.gui_values["age"] >= 0.4:
                msg.data = 0.0
                self.pub_spatial.publish(msg)
                self.pub_interpersonal.publish(msg)
                self.pub_postural.publish(msg)

            vlm_msg = String()
            vlm_msg.data = json.dumps(vlm_data)
            self.pub_vlm_str.publish(vlm_msg)

        # 4. Publikování blue area (poměr lidí v modrém boxu, počítáno z kamery přes YOLO pose)
        if self.gui_values["timeline"] == 0.0:
            self.pub_area.publish(Float32(data=0.0))
        else:
            with self.data_lock:
                area_score = self.blue_area_score
            self.pub_area.publish(Float32(data=float(area_score)))

    def destroy_node(self):
        try:
            if self.video_writer is not None:
                self.video_writer.release()
                self.video_writer = None
                self.get_logger().info(
                f"Video saved: {self.video_path}"
                )
            self.stream.stop()
            self.stream.close()
        except:
            pass
        super().destroy_node()


# ── GUI APLIKACE ──────────────────────────────────────────────────────────────
class SliderApp:
    BG = "#0d0d0f"
    PANEL = "#16161a"
    ACCENT = "#00e5ff"
    TEXT = "#e8eaf6"
    SUBTEXT = "#6c7a93"
    TRACK_BG = "#1e2030"
    FONT_MONO = ("Courier New", 10)
    FONT_LABEL = ("Courier New", 11, "bold")
    FONT_TITLE = ("Courier New", 18, "bold")

    def __init__(self, root: tk.Tk, node: UnifiedExhibitionNode):
        self.root = root
        self.node = node
        root.title("ROS 2 Unified Publisher")
        root.configure(bg=self.BG)
        root.resizable(False, False)
        self._vars = {}
        self._build_ui()

    def _build_ui(self):
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=24, pady=(20, 4))
        tk.Label(header, text="Unified Control", font=self.FONT_TITLE, fg=self.ACCENT, bg=self.BG).pack(side="left")

        self._status_dot = tk.Label(header, text="●", font=("Courier New", 14), fg="#444", bg=self.BG)
        self._status_dot.pack(side="right", padx=(0, 4))
        tk.Label(header, text="syncing", font=self.FONT_MONO, fg=self.SUBTEXT, bg=self.BG).pack(side="right")
        tk.Frame(self.root, bg=self.ACCENT, height=1).pack(fill="x", padx=24, pady=(0, 16))

        container = tk.Frame(self.root, bg=self.BG)
        container.pack(padx=24, pady=(0, 20))

        for i, (key, topic, default) in enumerate(GUI_TOPICS):
            self._add_row(container, i, key, topic, default)

        tk.Frame(self.root, bg="#222", height=1).pack(fill="x", padx=24)
        footer = tk.Frame(self.root, bg=self.BG)
        footer.pack(fill="x", padx=24, pady=(8, 16))
        tk.Label(footer, text="Values published every 1 s synchronously", font=("Courier New", 9), fg=self.SUBTEXT, bg=self.BG).pack(side="left")

        self._blink()

    def _add_row(self, parent: tk.Frame, row: int, key: str, topic: str, default: float):
        row_bg = self.PANEL if row % 2 == 0 else self.BG
        frame = tk.Frame(parent, bg=row_bg, padx=10, pady=6)
        frame.pack(fill="x", pady=1)

        tk.Label(frame, text=f"{topic:<25}", font=self.FONT_MONO, fg=self.TEXT, bg=row_bg, anchor="w", width=25).pack(side="left")

        var = tk.DoubleVar(value=default)
        self._vars[key] = var

        style_name = f"Accent{row}.Horizontal.TScale"
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass
        style.configure(style_name, background=row_bg, troughcolor=self.TRACK_BG, sliderthickness=16, sliderrelief="flat")

        slider = ttk.Scale(frame, from_=0.0, to=1.0, orient="horizontal", variable=var, length=320, style=style_name, command=lambda val, k=key: self._on_change(k, val))
        slider.pack(side="left", padx=(12, 8))

        val_label = tk.Label(frame, text=f"{default:.3f}", font=self.FONT_LABEL, fg=self.ACCENT, bg=row_bg, width=6, anchor="e")
        val_label.pack(side="left")

        var.trace_add("write", lambda *_, k=key, lbl=val_label: self._update_label(k, lbl))

    def _on_change(self, key: str, val: str):
        # Aktualizace hodnoty přímo v node, aby si ji vzal Master Timer
        with self.node.data_lock:
            self.node.gui_values[key] = float(val)

    def _update_label(self, key: str, label: tk.Label):
        v = self._vars[key].get()
        r1, g1, b1 = 0xff, 0x40, 0x81
        r2, g2, b2 = 0x00, 0xe5, 0xff
        r = int(r1 + (r2 - r1) * v)
        g = int(g1 + (g2 - g1) * v)
        b = int(b1 + (b2 - b1) * v)
        label.config(text=f"{v:.3f}", fg=f"#{r:02x}{g:02x}{b:02x}")

    def _blink(self):
        current = self._status_dot.cget("fg")
        next_color = self.ACCENT if current != self.ACCENT else "#444"
        self._status_dot.config(fg=next_color)
        self.root.after(1000, self._blink)


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = UnifiedExhibitionNode()

    # ROS spinner běží na pozadí a řídí veškeré callbacky kamery a Master Timer
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()

    # GUI běží v hlavním vlákně (Main thread)
    root = tk.Tk()
    app = SliderApp(root, node)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()

if __name__ == "__main__":
    main()