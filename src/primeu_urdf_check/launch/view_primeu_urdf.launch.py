from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition, UnlessCondition
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    default_model = PathJoinSubstitution(
        [FindPackageShare("primeu_description"), "urdf", "primeu_robot.urdf"]
    )
    default_rviz = PathJoinSubstitution(
        [FindPackageShare("primeu_urdf_check"), "rviz", "primeu_robot_check.rviz"]
    )

    model_arg = DeclareLaunchArgument(
        "model",
        default_value=default_model,
        description="Absolute path to the URDF file to validate.",
    )
    use_gui_arg = DeclareLaunchArgument(
        "use_joint_state_gui",
        default_value="true",
        description="Whether to launch joint_state_publisher_gui.",
    )
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz",
        default_value="true",
        description="Whether to launch RViz.",
    )
    rviz_config_arg = DeclareLaunchArgument(
        "rvizconfig",
        default_value=default_rviz,
        description="Absolute path to the RViz config file.",
    )

    robot_description = ParameterValue(
        Command(["xacro ", LaunchConfiguration("model")]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        parameters=[{"robot_description": robot_description}],
        output="screen",
    )

    joint_state_publisher_gui = Node(
        package="joint_state_publisher_gui",
        executable="joint_state_publisher_gui",
        condition=IfCondition(LaunchConfiguration("use_joint_state_gui")),
        output="screen",
    )

    joint_state_publisher = Node(
        package="joint_state_publisher",
        executable="joint_state_publisher",
        condition=UnlessCondition(LaunchConfiguration("use_joint_state_gui")),
        output="screen",
    )

    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        condition=IfCondition(LaunchConfiguration("use_rviz")),
        arguments=["-d", LaunchConfiguration("rvizconfig")],
        output="screen",
    )

    return LaunchDescription(
        [
            model_arg,
            use_gui_arg,
            use_rviz_arg,
            rviz_config_arg,
            robot_state_publisher,
            joint_state_publisher_gui,
            joint_state_publisher,
            rviz2,
        ]
    )
