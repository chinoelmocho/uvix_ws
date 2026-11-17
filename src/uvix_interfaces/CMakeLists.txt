cmake_minimum_required(VERSION 3.8)
project(uvix_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(std_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(action_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  # Mensajes
  "msg/KeyValue.msg"
  "msg/Person.msg"
  "msg/UserCommand.msg"
  "msg/ClarificationRequest.msg"
  "msg/CommandEvent.msg"
  "msg/MissionSpec.msg"
  "msg/MissionStatus.msg"
  "msg/RobotActivity.msg"
  "msg/Alert.msg"
  "msg/SystemStatus.msg"
  "msg/PowerStatus.msg"
  "msg/IdentityVerification.msg"
  # M1-03 visual observation contracts
  "msg/ImageBox.msg"
  "msg/PersonObservation.msg"
  "msg/PeopleObservations.msg"
  "msg/BodyKeypoint.msg"
  "msg/BodyPose.msg"
  "msg/BodyPoseArray.msg"
  "msg/FaceMatch.msg"
  "msg/FaceMatchArray.msg"
  "msg/GestureEvent.msg"
  # Servicios
  "srv/RegisterMission.srv"
  "srv/CancelMission.srv"
  "srv/AckAlert.srv"
  "srv/GetPerson.srv"
  "srv/GetRequestIdentity.srv"
  # Acciones
  "action/ExecuteMission.action"
  "action/SpeakText.action"
  DEPENDENCIES std_msgs builtin_interfaces sensor_msgs action_msgs geometry_msgs
)

ament_export_dependencies(rosidl_default_runtime)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
