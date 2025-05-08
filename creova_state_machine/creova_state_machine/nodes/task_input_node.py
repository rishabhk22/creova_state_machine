import rclpy
from rclpy.node import Node
from std_msgs.msg import String

class TaskInputNode(Node):
    def __init__(self):
        super().__init__('task_input_node')
        self.publisher = self.create_publisher(String, '/task_input', 10)
        self.timer = self.create_timer(5.0, self.send_task)

    def send_task(self):
        task = {
            "task_id": "001",
            "object": "apple",
            "location": "Zubin's desk",
            "pose": {"x": 1.0, "y": 2.0, "z": 0.5}
        }
        msg = String()
        msg.data = str(task)
        self.publisher.publish(msg)
        self.get_logger().info(f"Published mock task: {msg.data}")

def main(args=None):
    rclpy.init(args=args)
    node = TaskInputNode()
    rclpy.spin(node)
    rclpy.shutdown()
