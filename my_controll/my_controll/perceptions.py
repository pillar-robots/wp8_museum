import rclpy
import numpy as np
from cognitive_nodes.perception import Perception
from core.container import Container


class MuseumPerception(Perception):
    """Museum / Tiago Perception class"""

    def __init__(self, name='perception', class_name='cognitive_nodes.perception.Perception',
                 default_msg=None, default_topic=None, normalize_data=None, **params):
        super().__init__(name=name, class_name=class_name, default_msg=default_msg, default_topic=default_topic, normalize_data=normalize_data, **params)

    def process_and_send_reading(self):
        """
        Publishes the current perception value (Float32) to its topic.
        The value should already be set externally in self.value.
        """
        if isinstance(self.reading, list):
            if len(self.reading) == 0:
                return # No reading to process, return immediately
            for perception in self.reading:
                noise_level=perception.noise_level
                age=perception.age
                blue_area=perception.blue_area
                spatial=perception.spatial
                posture_state=perception.posture_state
                interpersonal_spacing=perception.interpersonal_spacing
                guide=perception.guide
                engage=perception.engage
                timeline=perception.timeline
                people=perception.people
                data = np.array([noise_level, age, blue_area, spatial, posture_state, interpersonal_spacing, guide, engage, timeline, people])
                labels = ["noise_level", "age", "blue_area", "spatial", "posture_state", "interpersonal_spacing", "guide", "engage", "timeline", "people"]

        else:
            data = np.array([self.reading.data])
            labels = ["data"]
        
        if self.container is None:
            self.container = Container(self.name, max_size=1, container_type="perception", labels=labels)
        self.container.push(data, labels, timestamps=self.get_clock().now().nanoseconds)


        self.get_logger().debug("Publishing normalized " + self.name + " = " + str(self.container))
        sensor_msg = self.container.to_msg()
        self.perception_publisher.publish(sensor_msg)