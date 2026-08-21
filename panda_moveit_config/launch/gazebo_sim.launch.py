import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.actions import SetParameter

def generate_launch_description():
    # Use simulation time
    set_sim_time = SetParameter(name='use_sim_time', value=True)

    # World path
    world_file = os.path.join(
        get_package_share_directory('moveit_resources_panda_moveit_config'),
        'worlds',
        'warehouse.world'
    )

    # Declare the world argument for gazebo
    world_arg = DeclareLaunchArgument(
        'world',
        default_value=world_file,
        description='Path to the Gazebo world file'
    )

    # Gazebo launch
    ros_gz_sim_pkg = get_package_share_directory('ros_gz_sim')
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_pkg, 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': ['-r ', LaunchConfiguration('world')]}.items()
    )

    # Spawn robot
    # The robot description will be published by demo.launch.py
    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'panda',
            '-topic', 'robot_description',
            '-z', '0.0'
        ],
        output='screen'
    )

    # Include demo.launch.py from moveit_resources_panda_moveit_config
    demo_launch_pkg = get_package_share_directory('moveit_resources_panda_moveit_config')
    demo_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(demo_launch_pkg, 'launch', 'demo.launch.py')
        ),
        launch_arguments={
            'ros2_control_hardware_type': 'gazebo'
        }.items()
    )

    # Bridge for clock (important for use_sim_time)
    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock'],
        output='screen'
    )

    # Controller spawners
    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    panda_arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "panda_arm_controller",
            "-c",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    panda_hand_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "panda_hand_controller",
            "-c",
            "/controller_manager",
            "--controller-manager-timeout",
            "60",
        ],
    )

    # Sequenced controller loading after delay for Gazebo physics to start
    delayed_spawners = TimerAction(
        period=5.0,
        actions=[
            joint_state_broadcaster_spawner,
        ]
    )

    load_panda_arm_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[panda_arm_controller_spawner],
        )
    )

    load_panda_hand_controller = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=panda_arm_controller_spawner,
            on_exit=[panda_hand_controller_spawner],
        )
    )

    # Include TP-GMM and Deformed GMM nodes
    tp_gmm_pkg = get_package_share_directory('tp_gmm')
    lfd_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(tp_gmm_pkg, 'launch', 'lfd_launch.py')
        )
    )

    return LaunchDescription([
        set_sim_time,
        world_arg,
        gazebo,
        bridge,
        demo_launch,
        spawn_entity,
        delayed_spawners,
        load_panda_arm_controller,
        load_panda_hand_controller,
        lfd_launch
    ])
