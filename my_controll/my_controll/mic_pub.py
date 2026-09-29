import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
import sounddevice as sd
import numpy as np


TARGET_DEVICE_NAME = "pulse" 

RATE = 48000
BLOCK_SIZE = 1024

RMS_MIN = 0.003
LOUD_RMS = 0.03
RMS_MAX = 0.1

PUBLISH_PERIOD = 5.0  # seconds

class AudioVolumePublisher(Node):

    def __init__(self):
        super().__init__('audio_volume_publisher')

        self.publisher_ = self.create_publisher(Float32, '/room/noise_level', 0)
        self.device_id = self.select_device()
        self.rms_samples = []
        self.timer = self.create_timer(PUBLISH_PERIOD, self.publish_average)

        try:
            self.stream = sd.InputStream(
                device=self.device_id,
                channels=1,
                samplerate=RATE,
                blocksize=BLOCK_SIZE,
                callback=self.audio_callback
            )
            self.stream.start()
            self.get_logger().info(f'Mic is on with ID {self.device_id}')

        except Exception as e:
            self.get_logger().error(f'FATAL ERROR: {e}')
            # Vypíšeme dostupná zařízení pro debug
            self.print_devices()
            raise

    def select_device(self):
        try:
            devices = sd.query_devices()
            for i, dev in enumerate(devices):
                if TARGET_DEVICE_NAME in dev['name'] and dev['max_input_channels'] > 0:
                    return i
        except Exception:
            pass
        return None


    def audio_callback(self, indata, frames, time_info, status):
        try:
            audio_data = indata[:, 0].copy()
            rms = np.sqrt(np.mean(audio_data ** 2))
            self.rms_samples.append(rms)

        except Exception as e:
            pass
    
    def publish_average(self):
        if not self.rms_samples:
            return
    
        avg_rms = np.mean(self.rms_samples)
        self.rms_samples.clear()
    
        # Piecewise normalization
        if avg_rms <= LOUD_RMS:
            norm = 0.5 * (avg_rms - RMS_MIN) / (LOUD_RMS - RMS_MIN)
        else:
            norm = 0.5 + 0.5 * (avg_rms - LOUD_RMS) / (RMS_MAX - LOUD_RMS)
    
        norm = np.clip(norm, 0.0, 1.0)
    
        msg = Float32()
        msg.data = float(norm)
        self.publisher_.publish(msg)
    
        self.get_logger().info(
            f"Average RMS: {avg_rms:.4f} -> Noise level topic: {norm:.3f}"
        )

    def destroy_node(self):
        try:
            self.stream.stop()
            self.stream.close()
        except:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AudioVolumePublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except SystemExit:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()