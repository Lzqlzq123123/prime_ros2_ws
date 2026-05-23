cmake_minimum_required(VERSION 3.10.2)
project(primeu_description)

find_package(ament_cmake REQUIRED)

install(DIRECTORY assets urdf mjcf launch config
  DESTINATION share/${PROJECT_NAME})

install(PROGRAMS
  scripts/primeu_tracker_retargeting_node
  DESTINATION lib/${PROJECT_NAME}
)

ament_package()
