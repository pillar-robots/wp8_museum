import threading
import tkinter as tk
from tkinter import ttk

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32


# ── Topic configuration ──────────────────────────────────────────────────────
TOPICS = [
    ("age",          "/vlm/age_composition",        0.0),
    ("spatial",      "/vlm/spatial_formation",      0.4),
    ("interpersonal","/vlm/interpersonal_spacing",  0.1),
    ("postural",     "/vlm/postural_assessment",    0.8),
    ("area",         "/vlm/blue_area",              0.2),
    ("engagement",   "/vlm/engagement_rating",      0.2),
    ("noise",        "/room/noise_level",           0.8),
    ("guide",        "/exhibition/guide",           0.0),
    ("timeline",     "/exhibition/timeline",        0.2),
    ("people",       "/exhibition/people",          0.0),
]


# ── ROS2 Node ────────────────────────────────────────────────────────────────
class ManualPublisher(Node):
    def __init__(self):
        super().__init__("manual_vlm_publisher")

        self.publishers_ = {}
        self.values: dict[str, float] = {}

        for key, topic, default in TOPICS:
            self.publishers_[key] = self.create_publisher(Float32, topic, 2)
            self.values[key] = default

        self.create_timer(1.0, self._publish)

    def _publish(self):
        msg = Float32()
        for key, pub in self.publishers_.items():
            msg.data = float(self.values[key])
            pub.publish(msg)


# ── Tkinter GUI ──────────────────────────────────────────────────────────────
class SliderApp:
    # Palette
    BG        = "#0d0d0f"
    PANEL     = "#16161a"
    ACCENT    = "#00e5ff"
    ACCENT2   = "#ff4081"
    TEXT      = "#e8eaf6"
    SUBTEXT   = "#6c7a93"
    TRACK_BG  = "#1e2030"
    FONT_MONO = ("Courier New", 10)
    FONT_LABEL= ("Courier New", 11, "bold")
    FONT_TITLE= ("Courier New", 18, "bold")

    def __init__(self, root: tk.Tk, node: ManualPublisher):
        self.root = root
        self.node = node

        root.title("ROS2 Manual Publisher")
        root.configure(bg=self.BG)
        root.resizable(False, False)

        self._build_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self.root, bg=self.BG)
        header.pack(fill="x", padx=24, pady=(20, 4))

        tk.Label(
            header,
            text="Topic  Publisher",
            font=self.FONT_TITLE,
            fg=self.ACCENT,
            bg=self.BG,
        ).pack(side="left")

        self._status_dot = tk.Label(
            header, text="●", font=("Courier New", 14), fg="#444", bg=self.BG
        )
        self._status_dot.pack(side="right", padx=(0, 4))
        tk.Label(header, text="publishing", font=self.FONT_MONO,
                 fg=self.SUBTEXT, bg=self.BG).pack(side="right")

        # separator
        tk.Frame(self.root, bg=self.ACCENT, height=1).pack(fill="x", padx=24, pady=(0, 16))

        # ── Slider rows ──
        container = tk.Frame(self.root, bg=self.BG)
        container.pack(padx=24, pady=(0, 20))

        self._vars: dict[str, tk.DoubleVar] = {}

        for i, (key, topic, default) in enumerate(TOPICS):
            self._add_row(container, i, key, topic, default)

        # ── Footer ──
        tk.Frame(self.root, bg="#222", height=1).pack(fill="x", padx=24)
        footer = tk.Frame(self.root, bg=self.BG)
        footer.pack(fill="x", padx=24, pady=(8, 16))
        tk.Label(
            footer,
            text="Values published every 1 s  ·  drag sliders to update",
            font=("Courier New", 9),
            fg=self.SUBTEXT,
            bg=self.BG,
        ).pack(side="left")

        # Blink the status dot
        self._blink()

    def _add_row(self, parent: tk.Frame, row: int, key: str, topic: str, default: float):
        # alternating row tint
        row_bg = self.PANEL if row % 2 == 0 else self.BG

        frame = tk.Frame(parent, bg=row_bg, padx=10, pady=6)
        frame.pack(fill="x", pady=1)

        # ── Topic label (fixed width) ──
        lbl = tk.Label(
            frame,
            text=f"{topic:<35}",
            font=self.FONT_MONO,
            fg=self.TEXT,
            bg=row_bg,
            anchor="w",
            width=35,
        )
        lbl.pack(side="left")

        # ── Slider ──
        var = tk.DoubleVar(value=default)
        self._vars[key] = var

        style_name = f"Accent{row}.Horizontal.TScale"
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            style_name,
            background=row_bg,
            troughcolor=self.TRACK_BG,
            sliderthickness=16,
            sliderrelief="flat",
        )

        slider = ttk.Scale(
            frame,
            from_=0.0,
            to=1.0,
            orient="horizontal",
            variable=var,
            length=320,
            style=style_name,
            command=lambda val, k=key: self._on_change(k, val),
        )
        slider.pack(side="left", padx=(12, 8))

        # ── Value readout ──
        val_label = tk.Label(
            frame,
            text=f"{default:.3f}",
            font=self.FONT_LABEL,
            fg=self.ACCENT,
            bg=row_bg,
            width=6,
            anchor="e",
        )
        val_label.pack(side="left")

        # Store label reference so we can update it
        var.trace_add(
            "write",
            lambda *_, k=key, lbl=val_label: self._update_label(k, lbl),
        )

    # ── Callbacks ────────────────────────────────────────────────────────────
    def _on_change(self, key: str, val: str):
        self.node.values[key] = float(val)

    def _update_label(self, key: str, label: tk.Label):
        v = self._vars[key].get()
        # colour gradient: low→accent2, high→accent
        r1, g1, b1 = 0xff, 0x40, 0x81   # accent2 (pink)  at 0.0
        r2, g2, b2 = 0x00, 0xe5, 0xff   # accent  (cyan)  at 1.0
        t = v
        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)
        label.config(text=f"{v:.3f}", fg=f"#{r:02x}{g:02x}{b:02x}")

    def _blink(self):
        current = self._status_dot.cget("fg")
        next_color = self.ACCENT if current != self.ACCENT else "#444"
        self._status_dot.config(fg=next_color)
        self.root.after(800, self._blink)


# ── Entry-point ──────────────────────────────────────────────────────────────
def main(args=None):
    rclpy.init(args=args)
    node = ManualPublisher()

    # Spin ROS2 in a background daemon thread
    ros_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    ros_thread.start()

    # Run tkinter on the main thread (required on most platforms)
    root = tk.Tk()
    SliderApp(root, node)

    try:
        root.mainloop()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()