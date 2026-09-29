import math
from cognitive_nodes.pnode import PNode
from core.container import Container, consolidate_containers


class PNodeBlue(PNode):
    """
    PNode that represents a silence
    """
    def __init__(self, name='blue', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)
        

    def calculate_activation(self, perception=None, activation_list=None):
        """
        Calculate the new activation value for a given perception.

        :param perception: The perception for which P-Node activation is calculated.
        :type perception: dict
        :param activation_list: The list of activations to be used for the calculation.
        :type activation_list: list
        :return: If there is space, returns the activation of the P-Node. If not, returns 0. 
            It also returs the timestamp.
        :rtype: cognitive_node_interfaces.msg.Activation
        """
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

        activation_value = 0.0
        if perception:
            value_raw = perception.read().sel(features=["blue_area:data"]).values[-1] if "blue_area:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            if value < 0.5:
                self.activation.activation = 0.95
            else:
                self.activation.activation = 0.0
            
            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodePosture(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='posture', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["posture_state:data"]).values[-1] if "posture_state:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value > 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeSilence(PNode):
    """
    PNode that represents a silence
    """
    def __init__(self, name='silence', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["noise_level:data"]).values[-1] if "noise_level:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value > 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation

class PNodeEngageExp(PNode):
    """
    PNode that represents a engage
    """
    def __init__(self, name='engage', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["engage:data"]).values[-1] if "engage:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)
            value_raw_2 = perception.read().sel(features=["guide:data"]).values[-1] if "guide:data" in perception.feature_labels else 0.0
            value_2 = round(float(value_raw_2), 1)

            # Apply your activation logic
            if value < 0.5 and value_2 < 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeEngageNov(PNode):
    """
    PNode that represents a engage
    """
    def __init__(self, name='engage', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["engage:data"]).values[-1] if "engage:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)
            value_raw_2 = perception.read().sel(features=["guide:data"]).values[-1] if "guide:data" in perception.feature_labels else 0.0
            value_2 = round(float(value_raw_2), 1)

            # Apply your activation logic
            if value < 0.5 and value_2 >= 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeEngageLow(PNode):
    """
    PNode that represents a engage
    """
    def __init__(self, name='engagelowlow', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["engage:data"]).values[-1] if "engage:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if  0.25 <= value < 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeEngageLowLow(PNode):
    """
    PNode that represents a engage
    """
    def __init__(self, name='engagelowlow', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["engage:data"]).values[-1] if "engage:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value < 0.25:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeSpatial(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='spatial', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["spatial:data"]).values[-1] if "spatial:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if value < 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeScript(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='script', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["timeline:data"]).values[-1] if "timeline:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if 0.85 < value < 1.0:
                self.activation.activation = 0.5
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodePoint(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='point', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["timeline:data"]).values[-1] if "timeline:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if 0.5 <= value < 0.65:
                self.activation.activation = 0.5
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeScreen(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='point', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["timeline:data"]).values[-1] if "timeline:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)

            # Apply your activation logic
            if 0.65 <= value < 0.85:
                self.activation.activation = 0.5
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodePostureSepar(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='posture_separ', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["posture_state:data"]).values[-1] if "posture_state:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)
            value_raw_2 = perception.read().sel(features=["interpersonal_spacing:data"]).values[-1] if "interpersonal_spacing:data" in perception.feature_labels else 0.0
            value_2 = round(float(value_raw_2), 1)

            # Apply your activation logic
            if value > 0.5 or value_2 > 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeSpatialSepar(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='spatial_separ', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["spatial:data"]).values[-1] if "spatial:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)
            value_raw_2 = perception.read().sel(features=["interpersonal_spacing:data"]).values[-1] if "interpersonal_spacing:data" in perception.feature_labels else 0.0
            value_2 = round(float(value_raw_2), 1)

            # Apply your activation logic
            if value < 0.5 or value_2 > 0.5:
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeRest(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='rest', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["timeline:data"]).values[-1] if "timeline:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)


            # Apply your activation logic
            if value < 0.5:
                self.activation.activation = 0.85
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodePeople(PNode):
    """
    PNode that represents a posture
    """
    def __init__(self, name='people', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name=name, class_name=class_name, space_class=space_class, space=space, history_size=history_size, **params)

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

        activation_value = 0.0

        if perception:
            value_raw = perception.read().sel(features=["guide:data"]).values[-1] if "guide:data" in perception.feature_labels else 0.0
            value = round(float(value_raw), 1)
            value_raw_2 = perception.read().sel(features=["age:data"]).values[-1] if "age:data" in perception.feature_labels else 0.0
            value_2 = round(float(value_raw_2), 1)

            # Apply your activation logic
            if value < 0.1 or value_2 < 0.1: #znamena ze lidi dorazili
                self.activation.activation = 0.8
                self.get_logger().debug(f"PNODE DEBUG: Loud value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation

#---------

class PNodeStrictGuide(PNode):
    """
    PNode that represents a strict guide
    """
    def __init__(self, name='strict_guide', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name, class_name, space_class, space, history_size, **params)

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list!=None:
            perception={}
            for sensor in activation_list:
                activation_list[sensor]['updated']=False
                perception[sensor]=activation_list[sensor]['data']

        if perception:
            value = next(iter(perception.values()), None)
            value = value[0]['data']
            value = round(value, 1)

            # Apply your activation logic
            if value == 0.6:
                self.activation.activation = 0.98
                self.get_logger().debug(f"PNODE DEBUG: Guide value: {value}")

            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation

class PNodeChillGuide(PNode):
    """
    PNode that represents a chill guide
    """
    def __init__(self, name='chill_guide', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name, class_name, space_class, space, history_size, **params)

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list!=None:
            perception={}
            for sensor in activation_list:
                activation_list[sensor]['updated']=False
                perception[sensor]=activation_list[sensor]['data']

        if perception:
            value = next(iter(perception.values()), None)
            value = value[0]['data']
            value = round(value, 1)

            # Apply your activation logic
            if value == 0.2:
                self.activation.activation = 0.98
                self.get_logger().debug(f"PNODE DEBUG: Guide value: {value}")
                
            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation
    
class PNodeNewGuide(PNode):
    """
    PNode that represents a new guide
    """
    def __init__(self, name='new_guide', class_name='cognitive_nodes.pnode.PNode', space_class=None, space=None, history_size=100, **params):
        super().__init__(name, class_name, space_class, space, history_size, **params)

    def calculate_activation(self, perception=None, activation_list=None):
        if activation_list!=None:
            perception={}
            for sensor in activation_list:
                activation_list[sensor]['updated']=False
                perception[sensor]=activation_list[sensor]['data']
                
        if perception:
            value = next(iter(perception.values()), None)
            value = value[0]['data']
            value = round(value, 1)

            # Apply your activation logic
            if value == 0.4:
                self.activation.activation = 0.98
                self.get_logger().debug(f"PNODE DEBUG: Guide value: {value}")
                
            else:
                self.activation.activation = 0.0

            self.activation.timestamp = self.get_clock().now().to_msg()
        return self.activation