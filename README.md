# WP8 Museum - PILLAR Project

e-MDB implementation of the WP8 Museum use case for the PILLAR project.

## Installation

1. **Install the e-MDB:** Follow the instructions at <https://github.com/pillar-robots/wp5_gii>
2. **Clone this repo inside the e-MDB folder:**

```bash
cd ~/eMDB_ws/src/wp5_gii
git clone https://github.com/pillar-robots/wp8_museum.git
```

3. **Build and source the experiment:**

```bash
source /opt/ros/humble/setup.bash
cd ~/eMDB_ws/
colcon build --packages-select my_controll --symlink-install
source install/setup.bash
```

## Launch the Museum Experiment

To run the full museum use case, you need to open **4 separate terminal windows** and run the following components:

### Terminal 1: Camera
Start the Intel RealSense camera:
```bash
source /opt/ros/humble/setup.bash
ros2 launch realsense2_camera rs_launch.py
```

### Terminal 2: Vision Language Model (VLM)
Activate the conda environment and start the Qwen API application:
```bash
conda activate qwen3-api
python app.py
```

### Terminal 3: Perception
Run the perception module. You have two options depending on your setup:

**Option A (Real Perception):**
```bash
cd ~/eMDB_ws/
source install/setup.bash
ros2 run my_controll publish_all
```

**Option B (Manual Perception):**
```bash
cd ~/eMDB_ws/
source install/setup.bash
ros2 run my_controll manual_publisher
```

### Terminal 4: Main Controller
Finally, launch the main museum controller:
```bash
cd ~/eMDB_ws/
source install/setup.bash
ros2 launch my_controll museum_launch.py
```
