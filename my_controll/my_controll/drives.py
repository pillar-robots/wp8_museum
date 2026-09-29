import rclpy
from copy import copy
from cognitive_nodes.drive import DriveTopicInput, Drive
from builtin_interfaces.msg import Time as TimeMsg
import random
from core.utils import class_from_classname


from math import exp, isclose

class DriveTopicListInput(Drive):
    """
    Drive class that reads one or more input topics to obtain its evaluation value.
    """
    def __init__(self, name="drive", class_name="cognitive_nodes.drive.Drive", input_topic=None, input_msg=None, min_eval=0.0, **params):
        """Constructor of the DriveTopicInput class.
        Initializes a base class Drive instance and creates subscriptions to the input topic(s).
        :param name: The name of the drive instance.
        :type name: str
        :param class_name: The name of the base Drive class.
        :type class_name: str
        :param input_topic: Topic or list of topics where the input will be published.
        :type input_topic: str or list[str]
        :param input_msg: Message type of the input topic(s).
        :type input_msg: ROS2 Interface
        :param min_eval: Minimum evaluation value as input reaches 1.0, defaults to 0.0.
        :type min_eval: float
        """        
        super().__init__(name, class_name, **params)
        self.min_eval = min_eval
        self.input_subscriptions = []
        self.input = 0.0

        if input_topic:
            # Normalize to list
            topics = input_topic if isinstance(input_topic, list) else [input_topic]
            msgs = input_msg if isinstance(input_msg, list) else [input_msg] * len(topics)
            # Per-topic state
            self.inputs = {topic: 0.0 for topic in topics}
            self.input_flags = {topic: False for topic in topics}

            for topic, msg_type in zip(topics, msgs):
                sub = self.create_subscription(
                    class_from_classname(msg_type),
                    topic,
                    lambda msg, t=topic: self.read_input_callback(msg, t),
                    1,
                    callback_group=self.cbgroup_evaluation
                )
                self.input_subscriptions.append(sub)

    def read_input_callback(self, msg, topic):
        """Reads a message from an input topic and updates the evaluation and reward.
        :param msg: Input data message.
        :type msg: Configurable (Typically std_msgs.msg.Float32)
        :param topic: The topic the message was received on.
        :type topic: str
        """
        self.inputs[topic] = msg.data
        self.input_flags[topic] = True
        self.input = sum(self.inputs.values()) / len(self.inputs)  # Average across all topics
        self.evaluate()
        self.calculate_reward()
        self.reward_timestamp = self.get_clock().now().to_msg()

    def calculate_reward(self):
        """
        Calculates the reward depending if the evaluation value increases or decreases.
        """        
        if self.evaluation.evaluation < self.old_evaluation.evaluation:
            self.get_logger().info(f"REWARD DETECTED. Drive: {self.name}, eval: {self.evaluation.evaluation}, old_eval: {self.old_evaluation.evaluation}")
            self.reward = 1.0
        elif self.evaluation.evaluation > self.old_evaluation.evaluation:
            self.get_logger().info(f"RESETTING REWARD. Drive: {self.name}, eval: {self.evaluation.evaluation}, old_eval: {self.old_evaluation.evaluation}")
            self.reward = 0.0

    def get_reward(self):
        """Returns the latest reward obtained.
        :return: Reward and timestamp.
        :rtype: Tuple (float, builtin_interfaces.msg.Time)
        """        
        return self.reward, self.reward_timestamp

    async def publish_activation_callback(self):
        """
        Timed publish of the activation value. This method will calculate the activation based on
        the evaluation of the drive and the activation of its neighbors, and then publish it
        in the corresponding topic.
        """
        if self.activation_topic:
            self.get_logger().debug(f'Activation Inputs: {str(self.activation_inputs)}')
            updated_activations = all((self.activation_inputs[node_name]['updated'] for node_name in self.activation_inputs))
            updated_evaluations = all(self.input_flags.values())  # All topics must have fired at least once
            if updated_activations and updated_evaluations:
                self.calculate_activation(perception=None, activation_list=self.activation_inputs)
                for node_name in self.activation_inputs:
                    self.activation_inputs[node_name]['updated'] = False
                self.input_flags = {topic: False for topic in self.input_flags}  # Reset all flags
            self.publish_activation(self.activation)

class DriveExponential(DriveTopicListInput):
    def evaluate(self, perception=None):
        """
        Evaluates the drive value according to an exponential function.

        :param perception: The given normalized perception.
        :type perception: dict
        :return: The valuation of the perception and its timestamp.
        :rtype: cognitive_node_interfaces.msg.Evaluation
        """
        self.old_evaluation=copy(self.evaluation)
        if self.input>=0:
            a = 1-self.min_eval 
            self.evaluation.evaluation = a*exp(-5*self.input)+self.min_eval
            if isclose(self.input, 1.0, ):
                self.evaluation.evaluation = 0.0
        else:
            self.evaluation.evaluation = 1.0
        self.evaluation.timestamp = self.get_clock().now().to_msg()

        return self.evaluation

class DriveMuseum(DriveTopicInput):
    def evaluate(self, perception=None):
        """
        Evaluates the drive value according to an exponential function.

        :param perception: The given normalized perception.
        :type perception: dict
        :return: The valuation of the perception and its timestamp.
        :rtype: cognitive_node_interfaces.msg.Evaluation
        """
        self.old_evaluation=copy(self.evaluation)
        #pridat sem m log abych videl co se deje
        if self.input == 1.0:
            self.evaluation.evaluation = 0.0
        else:
            self.evaluation.evaluation = 1.0
        self.evaluation.timestamp = self.get_clock().now().to_msg()

        return self.evaluation

class DriveExponentialOpo(DriveTopicInput):
    def evaluate(self, perception=None):
        """
        Evaluates the drive value according to an inverted exponential function.
        """
        self.old_evaluation = copy(self.evaluation)
        if self.input >= 0:
            a = 1-self.min_eval
            self.evaluation.evaluation = a*exp(-5*self.input) + self.min_eval
            if isclose(self.input, 1.0, ):
                self.evaluation.evaluation = 1.0
        else:
            self.evaluation.evaluation = 0.0
        self.evaluation.timestamp = self.get_clock().now().to_msg()

        return self.evaluation