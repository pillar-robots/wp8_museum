import rclpy
from rclpy.time import Time
from rclpy.qos import QoSProfile, qos_profile_sensor_data, ReliabilityPolicy, HistoryPolicy
from rclpy.callback_groups import ReentrantCallbackGroup, MutuallyExclusiveCallbackGroup

from core.container import Container, consolidate_containers

from core_interfaces.msg import Container as ContainerMsg
from cognitive_nodes.world_model import WorldModel

from std_msgs.msg import Float32

class MuseumYoungPeople(WorldModel):
    def __init__(self, name='KIDS', class_name='cognitive_nodes.world_model.WorldModel', **params):
        super().__init__(name=name, class_name=class_name, **params)

        self.configure_activation_inputs(self.neighbors)
        self.perception = None
        self.cbgroup_activation = getattr(self, "cbgroup_activation", MutuallyExclusiveCallbackGroup())

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list is not None:
            data = [activation_list[sensor]['data'] for sensor in activation_list]
            if self.perception is None and len(data)>0:
                self.perception = consolidate_containers(data, name="perception", container_type="perception")
            elif len(data)==0: # Activation list may be empty when initializing the P-Node.
                self.activation.activation = 0.0
                self.activation.timestamp = self.get_clock().now().to_msg()
                return self.activation
            else:
                consolidate_containers(data, write_container=self.perception)
            perception = self.perception
        
        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["age:data"]).values[-1] if "age:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if 0.0 < value <= 0.35:
                activation_value = 1.0

            else:
                activation_value = 0.0

        perception_timestamp = self.perception.data.coords["timestamp"].values[-1]
        self.activation.activation = activation_value
        self.activation.timestamp = Time(nanoseconds=perception_timestamp).to_msg()
        return self.activation
    
    def create_activation_input(self, node: dict):
        """Añade suscripciones con QoS de sensor para baja latencia."""
        name = node['name']
        node_type = node['node_type']
        if node_type == "Perception":
            sub = self.create_subscription(
                ContainerMsg,
                f"perception/{name}/value",
                self.read_activation_callback,
                qos_profile_sensor_data,  # OPT: QoS de sensores
                callback_group=self.cbgroup_activation
            )
            # OPT: no crear nuevos objetos por callback; usa referencias in-place
            self.activation_inputs[name] = dict(
                subscriber=sub,
                data=None,             # placeholder reutilizable
                updated=False
            )


    def read_activation_callback(self, msg: ContainerMsg):
        """
        Callback method that reads a perception and stores it in the activation inputs list.

        :param msg: PerceptionStamped message that contains the perception and its timestamp.
        :type msg: cognitive_node_interfaces.msg.PerceptionStamped
        """        
        if msg.max_size>1:
            self.get_logger().error(f'Received perception with multiple readings: ({msg.name}). Perception messages should (currently) include only one reading!')
        elif msg.max_size==1:
            node_name=msg.name
            if node_name in self.activation_inputs:
                if self.activation_inputs[node_name]['data'] is None:
                    self.activation_inputs[node_name]['data']=Container.from_msg(msg)
                else:
                    self.activation_inputs[node_name]['data'].push_from_msg(msg)
                self.activation_inputs[node_name]['updated']=True
            else:
                self.get_logger().error(
                    "Received perception not registered in local perception cache!!!"
                )
        else:
            self.get_logger().warn("Empty perception recieved in P-Node")

class MuseumMajorPeople(WorldModel):
    def __init__(self, name='OLD', class_name='cognitive_nodes.world_model.WorldModel', **params):
        super().__init__(name=name, class_name=class_name, **params)

        self.configure_activation_inputs(self.neighbors)
        self.perception = None
        self.cbgroup_activation = getattr(self, "cbgroup_activation", MutuallyExclusiveCallbackGroup())

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list is not None:
            data = [activation_list[sensor]['data'] for sensor in activation_list]
            if self.perception is None and len(data)>0:
                self.perception = consolidate_containers(data, name="perception", container_type="perception")
            elif len(data)==0: # Activation list may be empty when initializing the P-Node.
                self.activation.activation = 0.0
                self.activation.timestamp = self.get_clock().now().to_msg()
                return self.activation
            else:
                consolidate_containers(data, write_container=self.perception)
            perception = self.perception
        
        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["age:data"]).values[-1] if "age:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value > 0.55:
                activation_value = 1.0
            else:
                activation_value = 0.0

        perception_timestamp = self.perception.data.coords["timestamp"].values[-1]
        self.activation.activation = activation_value
        self.activation.timestamp = Time(nanoseconds=perception_timestamp).to_msg()
        return self.activation
    
    def create_activation_input(self, node: dict):
        """Añade suscripciones con QoS de sensor para baja latencia."""
        name = node['name']
        node_type = node['node_type']
        if node_type == "Perception":
            sub = self.create_subscription(
                ContainerMsg,
                f"perception/{name}/value",
                self.read_activation_callback,
                qos_profile_sensor_data,  # OPT: QoS de sensores
                callback_group=self.cbgroup_activation
            )
            # OPT: no crear nuevos objetos por callback; usa referencias in-place
            self.activation_inputs[name] = dict(
                subscriber=sub,
                data=None,             # placeholder reutilizable
                updated=False
            )


    def read_activation_callback(self, msg: ContainerMsg):
        """
        Callback method that reads a perception and stores it in the activation inputs list.

        :param msg: PerceptionStamped message that contains the perception and its timestamp.
        :type msg: cognitive_node_interfaces.msg.PerceptionStamped
        """        
        if msg.max_size>1:
            self.get_logger().error(f'Received perception with multiple readings: ({msg.name}). Perception messages should (currently) include only one reading!')
        elif msg.max_size==1:
            node_name=msg.name
            if node_name in self.activation_inputs:
                if self.activation_inputs[node_name]['data'] is None:
                    self.activation_inputs[node_name]['data']=Container.from_msg(msg)
                else:
                    self.activation_inputs[node_name]['data'].push_from_msg(msg)
                self.activation_inputs[node_name]['updated']=True
            else:
                self.get_logger().error(
                    "Received perception not registered in local perception cache!!!"
                )
        else:
            self.get_logger().warn("Empty perception recieved in P-Node")

class MuseumMixPeople(WorldModel):
    def __init__(self, name='MIX', class_name='cognitive_nodes.world_model.WorldModel', **params):
        super().__init__(name=name, class_name=class_name, **params)

        self.configure_activation_inputs(self.neighbors)
        self.perception = None
        self.cbgroup_activation = getattr(self, "cbgroup_activation", MutuallyExclusiveCallbackGroup())

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list is not None:
            data = [activation_list[sensor]['data'] for sensor in activation_list]
            if self.perception is None and len(data)>0:
                self.perception = consolidate_containers(data, name="perception", container_type="perception")
            elif len(data)==0: # Activation list may be empty when initializing the P-Node.
                self.activation.activation = 0.0
                self.activation.timestamp = self.get_clock().now().to_msg()
                return self.activation
            else:
                consolidate_containers(data, write_container=self.perception)
            perception = self.perception
        
        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["age:data"]).values[-1] if "age:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if 0.35 < value < 0.55:
                activation_value = 1.0
            else:
                activation_value = 0.0

        perception_timestamp = self.perception.data.coords["timestamp"].values[-1]
        self.activation.activation = activation_value
        self.activation.timestamp = Time(nanoseconds=perception_timestamp).to_msg()
        return self.activation
    
    def create_activation_input(self, node: dict):
        """Añade suscripciones con QoS de sensor para baja latencia."""
        name = node['name']
        node_type = node['node_type']
        if node_type == "Perception":
            sub = self.create_subscription(
                ContainerMsg,
                f"perception/{name}/value",
                self.read_activation_callback,
                qos_profile_sensor_data,  # OPT: QoS de sensores
                callback_group=self.cbgroup_activation
            )
            # OPT: no crear nuevos objetos por callback; usa referencias in-place
            self.activation_inputs[name] = dict(
                subscriber=sub,
                data=None,             # placeholder reutilizable
                updated=False
            )


    def read_activation_callback(self, msg: ContainerMsg):
        """
        Callback method that reads a perception and stores it in the activation inputs list.

        :param msg: PerceptionStamped message that contains the perception and its timestamp.
        :type msg: cognitive_node_interfaces.msg.PerceptionStamped
        """      
        if msg.max_size>1:
            self.get_logger().error(f'Received perception with multiple readings: ({msg.name}). Perception messages should (currently) include only one reading!')
        elif msg.max_size==1:
            node_name=msg.name
            if node_name in self.activation_inputs:
                if self.activation_inputs[node_name]['data'] is None:
                    self.activation_inputs[node_name]['data']=Container.from_msg(msg)
                else:
                    self.activation_inputs[node_name]['data'].push_from_msg(msg)
                self.activation_inputs[node_name]['updated']=True
            else:
                self.get_logger().error(
                    "Received perception not registered in local perception cache!!!"
                )
        else:
            self.get_logger().warn("Empty perception recieved in P-Node")

class MuseumGeneralPeople(WorldModel):
    def __init__(self, name='GENERAL', class_name='cognitive_nodes.world_model.WorldModel', **params):
        super().__init__(name=name, class_name=class_name, **params)

        self.perception = None
        self.cbgroup_activation = getattr(self, "cbgroup_activation", MutuallyExclusiveCallbackGroup())
        self.configure_activation_inputs(self.neighbors)

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list!=None:
            data = [activation_list[sensor]['data'] for sensor in activation_list]
            if self.perception is None and len(data)>0:
                self.perception = consolidate_containers(data, name="perception", container_type="perception")
            elif len(data)==0: # Activation list may be empty when initializing the P-Node.
                self.activation.activation = 0.0
                self.activation.timestamp = self.get_clock().now().to_msg()
                return self.activation
            else:
                consolidate_containers(data, write_container=self.perception)
            perception = self.perception
        
        activation_value = 1.0

        if perception:
            value_raw = perception.read().sel(features=["age:data"]).values[-1] if "age:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value <= 0.0:
                activation_value = 1.0
            else:
                activation_value = 0.0

        perception_timestamp = self.perception.data.coords["timestamp"].values[-1]
        self.activation.activation = activation_value
        self.activation.timestamp = Time(nanoseconds=perception_timestamp).to_msg()
        return self.activation
    
    def create_activation_input(self, node: dict):
        """Añade suscripciones con QoS de sensor para baja latencia."""
        name = node['name']
        node_type = node['node_type']
        if node_type == "Perception":
            sub = self.create_subscription(
                ContainerMsg,
                f"perception/{name}/value",
                self.read_activation_callback,
                qos_profile_sensor_data,  # OPT: QoS de sensores
                callback_group=self.cbgroup_activation
            )
            # OPT: no crear nuevos objetos por callback; usa referencias in-place
            self.activation_inputs[name] = dict(
                subscriber=sub,
                data=None,             # placeholder reutilizable
                updated=False
            )


    def read_activation_callback(self, msg: ContainerMsg):
        """
        Callback method that reads a perception and stores it in the activation inputs list.

        :param msg: PerceptionStamped message that contains the perception and its timestamp.
        :type msg: cognitive_node_interfaces.msg.PerceptionStamped
        """        
        if msg.max_size>1:
            self.get_logger().error(f'Received perception with multiple readings: ({msg.name}). Perception messages should (currently) include only one reading!')
        elif msg.max_size==1:
            node_name=msg.name
            if node_name in self.activation_inputs:
                if self.activation_inputs[node_name]['data'] is None:
                    self.activation_inputs[node_name]['data']=Container.from_msg(msg)
                else:
                    self.activation_inputs[node_name]['data'].push_from_msg(msg)
                self.activation_inputs[node_name]['updated']=True
            else:
                self.get_logger().error(
                    "Received perception not registered in local perception cache!!!"
                )
        else:
            self.get_logger().warn("Empty perception recieved in P-Node")