from enum import Enum
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from collections import deque
import ast  # to parse string messages as dicts

class OrchestrationState(Enum):
    IDLE = 0
    PARSING_INTENT = 1
    OBJECT_DETECTION = 2
    PICKING = 3
    NAVIGATE_TO_HANDOFF = 4
    HANDOFF = 5
    NAVIGATE_TO_USER = 6
    DELIVERING = 7
    RETURN = 8
    ERROR_RECOVERY = 9

class TaskState(Enum):
    PENDING = 0
    ACTIVE = 1
    PICKING = 2
    COMPLETE = 3
    FAILED = 4
    CANCELLED = 5
    WAITING_FOR_DELIVERY = 6
    DELIVERING = 7

class Task:
    def __init__(self, task_id, object_name, user_location):
        self.task_id = task_id
        self.object_name = object_name
        self.user_location = user_location
        self.status = TaskState.PENDING
        self.object_pose = None
        self.pick_complete = False
        self.delivery_complete = False

class Create:
    def __init__(self):
        self.busy = False
        self.current_location = None
        self.status = OrchestrationState.IDLE

class Kinova:
    def __init__(self):
        self.busy = False
        self.status = OrchestrationState.IDLE
        self.holding_object = False

class OrchestrationFSM(Node):
    def __init__(self):
        super().__init__('orchestrator')
        self.task_queue = deque()
        self.create = Create()
        self.kinova = Kinova()

        self.kinova_feedback_sub = self.create_subscription(String, '/manipulation/feedback', self.handle_kinova_feedback, 10)
        self.create_feedback_sub = self.create_subscription(String, '/navigation/feedback', self.handle_create_feedback, 10)

        self.timer = self.create_timer(1.0, self.run_state_machine)

        # Example: pre-load a task
        self.add_task(Task("T1", "apple", "Zubin's Desk"))

    def add_task(self, task):
        self.task_queue.append(task)
        self.get_logger().info(f"Added task {task.task_id} to queue")

    def run_state_machine(self):
        if not self.task_queue:
            return

        current_task = self.task_queue[0]

        if not self.kinova.busy and current_task.status == TaskState.PENDING:
            self.get_logger().info("[Orch] Sending pick command to manipulation node")
            current_task.status = TaskState.ACTIVE
            self.kinova.busy = True
            self.kinova.status = OrchestrationState.PICKING

        elif current_task.status == TaskState.WAITING_FOR_DELIVERY and not self.create.busy:
            self.get_logger().info("[Orch] Sending delivery command to navigation node")
            current_task.status = TaskState.DELIVERING
            self.create.status = OrchestrationState.DELIVERING
            self.create.busy = True

    def handle_kinova_feedback(self, msg: String):
        feedback = msg.data.lower()
        if "success" in feedback and "true" in feedback:
            self.get_logger().info("Pick complete by Kinova")
            self.kinova.busy = False
            self.kinova.status = OrchestrationState.IDLE

            current_task = self.task_queue[0]
            current_task.status = TaskState.WAITING_FOR_DELIVERY
        else:
            self.get_logger().error(f"Kinova error or failure: {msg.data}")

    def handle_create_feedback(self, msg: String):
        feedback = msg.data.lower()
        current_task = self.task_queue[0] if self.task_queue else None

        if "success" in feedback and "true" in feedback:
            self.create.busy = False
            self.create.status = OrchestrationState.IDLE

            if "delivery" in feedback and current_task.status == TaskState.DELIVERING:
                current_task.status = TaskState.COMPLETE
                self.get_logger().info(f"Task {current_task.task_id} completed successfully")
                self.task_queue.popleft()

            elif "base" in feedback:
                self.get_logger().info("Robot returned to base, ready for new tasks")
        else:
            self.get_logger().error(f"Navigation error or failure: {msg.data}")

def main(args=None):
    rclpy.init(args=args)
    node = OrchestrationFSM()
    rclpy.spin(node)
    rclpy.shutdown()

if __name__ == '__main__':
    main()
