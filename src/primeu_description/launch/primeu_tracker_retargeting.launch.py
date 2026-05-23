from __future__ import annotations

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    package_share = get_package_share_directory("primeu_description")
    default_model = os.path.join(package_share, "urdf", "primeu_robot.urdf")
    default_config = os.path.join(package_share, "config", "tracker_retargeting.yaml")

    model = open(default_model, "r", encoding="utf-8").read()

    use_robot_state_publisher_arg = DeclareLaunchArgument(
        "use_robot_state_publisher",
        default_value="true",
        description="Publish the PrimeU URDF to TF.",
    )
    waist_tracker_frame_arg = DeclareLaunchArgument(
        "waist_tracker_frame",
        default_value="LHR-31C9C2E6",
        description="TF child frame for the waist tracker.",
    )
    left_tracker_frame_arg = DeclareLaunchArgument(
        "left_tracker_frame",
        default_value="LHR-6E8EC1F7",
        description="TF child frame for the left hand tracker.",
    )
    right_tracker_frame_arg = DeclareLaunchArgument(
        "right_tracker_frame",
        default_value="LHR-4622FDDD",
        description="TF child frame for the right hand tracker.",
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        condition=IfCondition(LaunchConfiguration("use_robot_state_publisher")),
        parameters=[{"robot_description": model}],
        output="screen",
    )

    retargeting_node = Node(
        package="primeu_description",
        executable="primeu_tracker_retargeting_node",
        name="primeu_tracker_retargeting",
        parameters=[
            default_config,
            {
                "waist_tracker_frame": LaunchConfiguration("waist_tracker_frame"),
                "left_tracker_frame": LaunchConfiguration("left_tracker_frame"),
                "right_tracker_frame": LaunchConfiguration("right_tracker_frame"),
            },
        ],
        output="screen",
    )

    return LaunchDescription(
        [
            use_robot_state_publisher_arg,
            waist_tracker_frame_arg,
            left_tracker_frame_arg,
            right_tracker_frame_arg,
            robot_state_publisher,
            retargeting_node,
        ]
    )
