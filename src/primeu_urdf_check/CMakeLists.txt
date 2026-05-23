cmake_minimum_required(VERSION 3.10)
project(primeu_urdf_check)

find_package(ament_cmake REQUIRED)

install(DIRECTORY launch rviz DESTINATION share/${PROJECT_NAME})

ament_package()
