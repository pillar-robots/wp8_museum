from __future__ import annotations
import rclpy
from conversation import Conversation
from llm import settings

class PolicyGuideConversation():
    """Converse until the guide speaks one of the handover phrases."""

    def __init__(
            self,
            name="guide_conv",
            class_name="cognitive_nodes.policy.Policy",
            service_msg=None,
            service_name=None,
            **params,
            ):
        pass
        #super().__init__(name=name, class_name=class_name, **params)

    def execute_callback(self, request, response):
        conv_node = Conversation()
        conv_node.launch()
        conv_node.destroy_node()
        # response.policy = self.name
        # return response


class PolicyPublicConversation():
    initial_prompt = (
        "Museum visitors are losing engage. Start a brief conversation to gain"
        "their attention back. Ask a simple question about the picture."
    )

    def __init__(
            self,
            name="public_conv",
            class_name="cognitive_nodes.policy.Policy",
            service_msg=None,
            service_name=None,
            **params,
            ):
        self.state_path = settings.STATE_PATH
        #super().__init__(name=name, class_name=class_name, **params)

    def execute_callback(self):
        conv_node = Conversation()
        conv_node.launch(self.state_path)
        conv_node.destroy_node()
        # response.policy = self.name
        # return response

def main(args=None):
    rclpy.init()
    node = PolicyPublicConversation()
    node.execute_callback()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
