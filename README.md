# prime_ros2_ws

This repository contains the `src/` tree from a ROS 2 workspace used for PrimeU tracking, retargeting, URDF visualization, Lighthouse tracking, and MANUS glove integration.

## Packages

### `libsurvive_ros2`

ROS 2 wrapper around `libsurvive` for SteamVR/Lighthouse tracking hardware.

Main role:

- Publishes tracker and base-station TF data from Lighthouse devices.
- Provides the tracking frames consumed by the PrimeU retargeting pipeline.
- Uses `libsurvive_world` as the tracking-side world frame in the current setup.

In this workspace, `primeu_tracker_retargeting_node` expects TF frames from this package.

### `primeu_description`

PrimeU robot description and tracker-to-robot retargeting package.

Main contents:

- PrimeU URDF files under `urdf/`
- PrimeU MJCF files under `mjcf/`
- Robot meshes under `assets/`
- Launch and parameter files for tracker retargeting
- The executable node `primeu_tracker_retargeting_node`

This is the core package that maps waist and hand tracker motion into PrimeU arm joint targets.

### `primeu_urdf_check`

Minimal visualization and sanity-check package for the PrimeU URDF.

Main role:

- Launches `robot_state_publisher`
- Launches `joint_state_publisher` or `joint_state_publisher_gui`
- Optionally opens RViz with a preset config

Use this package when you want to inspect the PrimeU model itself without the tracker retargeting stack.

### `manus_ros2_msgs`

ROS 2 message definitions for MANUS glove data.

Defined interfaces:

- `ManusGlove`: aggregated glove state
- `ManusRawNode`: raw hand skeleton node pose
- `ManusErgonomics`: ergonomic feature/value pair
- `ManusVibrationCommand`: five-channel finger vibration command

This package is a dependency of `manus_ros2`.

### `manus_ros2`

ROS 2 node that connects to the MANUS SDK and republishes glove data.

Main role:

- Starts a `manus_data_publisher` node.
- Connects to MANUS Core or integrated SDK mode.
- Publishes one topic per discovered glove, named like `manus_glove_0`, `manus_glove_1`, etc.
- Each `ManusGlove` message includes raw skeleton nodes, ergonomics values, and raw sensor poses.
- Dynamically creates vibration command subscribers so callers can send `ManusVibrationCommand` messages back to each glove.

This package is independent from the PrimeU retargeting node in the current repository, but it is useful for hand-sensing or glove-driven extensions.

## `primeu_tracker_retargeting_node`

Source: `src/primeu_description/scripts/primeu_tracker_retargeting_node`

This node is the main tracker-to-robot bridge in the repository. It takes waist and hand tracker TFs, calibrates them against the PrimeU robot model, converts tracker motion into robot-relative hand targets, solves PrimeU arm inverse kinematics, and publishes the resulting target poses and joint commands.

### What it consumes

The node reads three tracker transforms from TF:

- waist tracker frame
- left hand tracker frame
- right hand tracker frame

By default these are looked up relative to:

- `tracking_world_frame = libsurvive_world`

The launch file `src/primeu_description/launch/primeu_tracker_retargeting.launch.py` passes the tracker frame names as parameters and can also start `robot_state_publisher` for the PrimeU URDF.

### Coordinate convention handling

Tracking systems do not always use ROS REP-103 axes directly. The node supports a `tracking_coordinate_convention` parameter:

- `ros`: no basis conversion
- `openxr` / `openvr` / `steamvr`: converts tracker poses into ROS-style axes

This matters because `libsurvive` or VR stacks may expose poses in a right-handed Y-up convention, while the robot retargeting logic assumes ROS base-frame conventions.

### Calibration model

The node maintains a calibration snapshot with four key pieces of state:

- the calibrated waist pose in world coordinates
- left/right tracker poses relative to the waist at calibration time
- left/right robot wrist poses in world coordinates at calibration time
- left/right robot wrist poses relative to the robot waist at calibration time

Calibration can happen in two ways:

- automatically on startup if `auto_calibrate=true`
- manually through the `calibrate_now` service of type `std_srvs/srv/Trigger`

During calibration:

1. The current waist tracker pose is corrected by `waist_tracker_correction_xyz/rpy`.
2. The corrected waist pose is used to infer `world -> robot_base`.
3. The left and right tracker poses are corrected by their per-hand correction transforms.
4. Tracker-relative hand anchors and robot-relative hand anchors are stored for later retargeting.

The robot-side nominal waist pose comes from:

- `robot_waist_xyz`
- `robot_waist_rpy`

These values define where the robot waist is expected to sit relative to `body_base_link` when calibration is captured.

### Retargeting logic

At runtime the node does not directly copy world-space hand poses onto the robot. Instead, it retargets hand motion relative to the current waist pose.

The runtime flow is:

1. Read current waist/left/right tracker poses from TF.
2. Apply tracker-to-ROS basis conversion if configured.
3. Apply waist and hand mounting correction transforms.
4. Compute current left/right hand poses relative to the current waist tracker frame.
5. Compare those relative poses against the calibration anchors.
6. Map tracker-relative motion into the robot waist frame using `tracker_to_robot_relative_rpy`.
7. Build robot targets:
   - `waist_target`: from the calibrated robot waist plus yaw-only waist change
   - `left_base_target`: left wrist target in robot base frame
   - `right_base_target`: right wrist target in robot base frame

Two design details are important here:

- Waist motion is reduced to yaw-only before being applied to the robot waist target.
- Hand translation is decoupled from hand orientation during relative retargeting, so rotating a tracker in place does not cause large unintended wrist position swings.

### Inverse kinematics

The node contains an internal IK solver class, `_PrimeUIK`, implemented directly in the script.

Key characteristics:

- Parses `primeu_robot.urdf` with `lxml`
- Builds a kinematic tree from the URDF joints
- Uses `scipy.optimize.least_squares`
- Solves for a configured subset of arm joints
- Supports joint limits from the URDF
- Locks the waist yaw joint to the waist target when possible

Default active IK joints:

- `waist_yaw_joint`
- left shoulder pitch/roll/yaw
- left elbow pitch
- left wrist roll/pitch/yaw
- right shoulder pitch/roll/yaw
- right elbow pitch
- right wrist roll/pitch/yaw

Default IK tip links:

- `left_wrist_yaw_link`
- `right_wrist_yaw_link`

The objective combines:

- waist orientation error
- left/right wrist position error
- left/right wrist orientation error
- regularization term on joint values
- smoothing term relative to the previous solution

Relevant tuning parameters:

- `ik_position_weight`
- `ik_orientation_weight`
- `ik_waist_orientation_weight`
- `ik_regularization_weight`
- `ik_smooth_weight`
- `ik_max_iterations`

Because the solver is inside the node, this package does not depend on MoveIt for the current retargeting path.

### Outputs

The node can publish both geometric targets and joint-level outputs.

Pose topics:

- `waist_pose`
- `left_hand_pose`
- `right_hand_pose`
- `left_hand_relative_pose`
- `right_hand_relative_pose`

TF frames:

- `tracking_world_frame -> robot_base_frame`
- `robot_base_frame -> waist_target_frame`
- `waist_target_frame -> left_target_frame`
- `waist_target_frame -> right_target_frame`
- `robot_base_frame -> primeu_left_ik_hand`
- `robot_base_frame -> primeu_right_ik_hand`

Joint-level outputs:

- `arm_joint_targets` as `sensor_msgs/JointState`
- `/joint_states` as `sensor_msgs/JointState` when `publish_joint_states=true`
- `arm_joint_trajectory` as `trajectory_msgs/JointTrajectory` when `publish_joint_trajectory=true`

The `arm_joint_targets` message contains the configured IK joint list in solver order. The `/joint_states` message contains all movable URDF joints known to the internal kinematics model.

### Parameters worth tuning first

For a new hardware setup, the most important parameters are usually:

- `waist_tracker_frame`
- `left_tracker_frame`
- `right_tracker_frame`
- `tracking_coordinate_convention`
- `waist_tracker_correction_rpy`
- `left_hand_correction_rpy`
- `right_hand_correction_rpy`
- `tracker_to_robot_relative_rpy`
- `robot_waist_xyz`
- `robot_waist_rpy`

In the current config:

- the tracking world is `libsurvive_world`
- the tracker convention is `openxr`
- the robot base frame is `body_base_link`
- the waist tracker has a `-1.5708` yaw correction
- tracker-relative hand motion is additionally rotated by `-1.5708` yaw into the robot-relative frame

These settings are specific to the present tracker mounting and PrimeU frame definitions.

### Launch entry point

Use:

```bash
ros2 launch primeu_description primeu_tracker_retargeting.launch.py
```

Useful launch arguments:

- `use_robot_state_publisher`
- `waist_tracker_frame`
- `left_tracker_frame`
- `right_tracker_frame`

### Runtime dependencies and assumptions

This node assumes:

- valid TF data already exists for all three trackers
- the PrimeU URDF is available from `primeu_description`
- `scipy`, `numpy`, and `lxml` are installed
- the configured tracker frames correspond to the actual physical mounting arrangement

If TF lookup fails temporarily, the node can reuse cached transforms and throttles warning logs with `log_throttle_sec`.

## Notes

- The repository only contains the uploaded `src/` tree, not the original workspace `build/`, `install/`, or `log/` directories.
- The MANUS SDK shared libraries originally present under `src/ROS2/ManusSDK/lib/` were omitted from GitHub because they exceeded GitHub's file size limit. See that directory's `README.md`.
