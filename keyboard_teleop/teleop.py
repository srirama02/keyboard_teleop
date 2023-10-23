import atexit
import sys
from abc import ABC, abstractmethod

from geometry_msgs.msg import Twist, TwistStamped
from rclpy.node import Node
from rclpy.qos import qos_profile_system_default
from chrono_ros_interfaces.msg import CobraSpeedDriver


class Teleop(Node, ABC):
    def __init__(self):
        atexit.register(self._emergency_stop)
        Node.__init__(self, "keyboard_teleop")

        self.declare_parameter("twist_stamped_enabled", False)
        self.declare_parameter("robot_base_frame", "base_link")
        self.declare_parameter("linear_max", 1.0)
        self.declare_parameter("angular_max", 1.0)
        self.declare_parameter("publish_rate", 10.0)
        self.LINEAR_MAX = self.get_parameter("linear_max").value

        self.ANGULAR_MAX = self.get_parameter("angular_max").value

        self._robot_base_frame = self.get_parameter("robot_base_frame").value

        # if self.get_parameter("twist_stamped_enabled").value:
        #     self.publisher_ = self.create_publisher(
        #         TwistStamped, "cmd_vel", qos_profile_system_default
        #     )
        #     self._make_twist = self._make_twist_stamped
        # else:
        #     self.publisher_ = self.create_publisher(
        #         Twist, "cmd_vel", qos_profile_system_default
        #     )
        #     self._make_twist = self._make_twist_unstamped

        self.publisher_ = self.create_publisher(
                CobraSpeedDriver, "/chrono_ros_node/input/driver_inputs", qos_profile_system_default
            )

        rate = 1 / self.get_parameter("publish_rate").value
        self.create_timer(rate, self._publish)
        self.linear = 0.0
        self.angular = 0.0

    @abstractmethod
    def update_twist(self, *args):
        pass

    def write_twist(self, linear=None, angular=None):
        if linear is not None:
            if abs(linear) <= self.LINEAR_MAX:
                self.linear = linear
            else:
                self.get_logger().error(
                    f"Trying to set a linear speed {linear} outside of allowed range of [{-self.LINEAR_MAX}, {self.LINEAR_MAX}]"
                )
        if angular is not None:
            if abs(angular) <= self.ANGULAR_MAX:
                self.angular = angular
            else:
                self.get_logger().error(
                    f"Trying to set a angular speed {angular} outside of allowed range of [{-self.ANGULAR_MAX}, {self.ANGULAR_MAX}]"
                )
        self._update_screen()

    def _make_twist_unstamped(self, linear, angular):
        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        return twist

    def _make_twist_stamped(self, linear, angular):
        twist_stamped = TwistStamped()
        twist_stamped.header.stamp = self.get_clock().now().to_msg()
        twist_stamped.header.frame_id = self._robot_base_frame
        twist_stamped.twist = self._make_twist_unstamped(linear, angular)
        return twist_stamped

    def _cobra_speed(self, linear, angular):
        cobra_msg = CobraSpeedDriver()
        cobra_msg.steering = angular
        cobra_msg.speed = linear
        return cobra_msg

    def _publish(self):
        # twist = self._make_twist(self.linear, self.angular)

        cobra_msg = self._cobra_speed(self.linear, self.angular)
        self.publisher_.publish(cobra_msg)

    def _update_screen(self):
        sys.stdout.write(f"Linear: {self.linear:.2f}, Angular: {self.angular:.2f}\r")

    def _emergency_stop(self):
        self.publisher_.publish(self._cobra_speed(0.0, 0.0))
