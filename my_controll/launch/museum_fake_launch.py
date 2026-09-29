import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription, LaunchContext
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import AppendEnvironmentVariable, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction, RegisterEventHandler, Shutdown
from launch.event_handlers import OnProcessExit
from launch.substitutions import (
    LaunchConfiguration,
    FindExecutable,
    PathJoinSubstitution,
    Command,
)


def launch_setup(context: LaunchContext, *args, **kwargs):

    logger = LaunchConfiguration("log_level")
    random_seed = LaunchConfiguration("random_seed")
    experiment_file = LaunchConfiguration("experiment_file")
    experiment_package = LaunchConfiguration("experiment_package")
    config_package = LaunchConfiguration("config_package")
    config_file = LaunchConfiguration("config_file")


    # mic_pub_node = Node(
    #     package='my_controll',          # název balíčku, kde je age_test.py
    #     executable='mic_pub',         # jméno z console_scripts
    #     name='mic_pub_node',          # jméno nodu
    #     output='screen'
    # )


    core_node = Node(
        package="core",
        executable="commander",
        output="screen",
        arguments=["--ros-args", "--log-level", logger],
        parameters=[{"random_seed": random_seed}],
    )

    ltm_node = Node(
        package="core",
        executable="ltm",
        output="screen",
        arguments=["0", "--ros-args", "--log-level", logger],
    )

    
    # simulator_node = Node(
    #     package="my_controll",
    #     executable="museum_sim_discrete",
    #     output="screen",
    #     parameters=[
    #         {
    #             "random_seed": random_seed,
    #             "config_file": PathJoinSubstitution(
    #                 [FindPackageShare(experiment_package), "experiments", experiment_file]
    #             ),
    #         }
    #     ],
    # )

    config_service_call = ExecuteProcess(
        cmd=[
            [
                FindExecutable(name="ros2"),
                " ",
                "service call",
                " ",
                "commander/load_config",
                " ",
                "core_interfaces/srv/LoadConfig",
                " ",
                '"{file:',
                " ",
                PathJoinSubstitution(
                    [FindPackageShare(config_package), "config", config_file]
                ),
                '}"',
            ]
        ],
        shell=True,
    )

    experiment_service_call = ExecuteProcess(
        cmd=[
            [
                FindExecutable(name="ros2"),
                " ",
                "service call",
                " ",
                "commander/load_experiment",
                " ",
                "core_interfaces/srv/LoadConfig",
                " ",
                '"{file:',
                " ",
                PathJoinSubstitution(
                    [FindPackageShare(experiment_package), "experiments", experiment_file]
                ),
                '}"',
            ]
        ],
        shell=True,
    )

    shutdown_on_exit = RegisterEventHandler(
        OnProcessExit(
            target_action=core_node,  # Nodo que supervisar
            on_exit=[Shutdown()],  # Acción: Cerrar todos los nodos
        )
    )

    nodes_to_start = [config_service_call, core_node, ltm_node, shutdown_on_exit] #, mic_pub_node]
    load_experiment_after_core = TimerAction(period=5.0, actions=[experiment_service_call])


    return nodes_to_start + [load_experiment_after_core]


def generate_launch_description():

    declared_arguments = []

    declared_arguments.append(
        DeclareLaunchArgument(
            "log_level",
            default_value=["info"],
            description="Logging level",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "random_seed",
            default_value="0",
            description="The seed to the random numbers generator",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "experiment_file",
            default_value="museum_fake.yaml",
            description="The file that loads the experiment config",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "config_file",
            default_value="commander.yaml",
            description="The file that loads the commander config",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "config_package",
            default_value="core",
            description="Package where the config file is located",
        )
    )

    declared_arguments.append(
        DeclareLaunchArgument(
            "experiment_package",
            default_value="my_controll",
            description="Package where the experiment file is located",
        )
    )

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         "image_topic",
    #         default_value="/camera/image_raw",
    #         description="Topic for the input camera stream (raw images)",
    #     )
    # )

    # declared_arguments.append(
    #     DeclareLaunchArgument(
    #         'face_publish_every',
    #         default_value='1.0',
    #         description='Seconds between publishing face events'
    #     )
    # )

    return LaunchDescription(
        declared_arguments + [OpaqueFunction(function=launch_setup)]
    )
