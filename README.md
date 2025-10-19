# Autonomous Driving with Computer Vision and AI

This repo contains the code developed for the 'Treball de Recerca'  - Final-year research project in Batxillerat (Catalan pre-university studies).

The aim of the project was to develop an Autonomous Driving System based on cameras. The main aspects developed were:
 - Lane detection and following
 - Object detection

Finally, it was all implemented into a simulation environment (in this case the game BeamNG) by capturing images from the computer and emulating a controller to drive the vehicle and also into a robot car with a Raspberry Pi 4.

### Project setup

The requirements can be installed by using:
```bash
pip install -r requirements.txt
```

Note: the setup for the robot car has its own requirements file.

****


## Lane detection an following
This subsystem has the objective of detecting and delimiting the lanes from the images, as well as calculating the relative position and direction of the vehicle and, finally estimate the steering needed in order to keep the vehicle centered within the lane

### Lane_Detection/lane_detection.py

This is the script used in order to process videos and images with the lane detection system. Its usage is:

```bash
python lane_detection.py input save_path --frame_rate [frame_rate] --width [width] --height [height] --beamng --port [port]
```

Note: the options --beamng and --port are only used to enable the implementation of the system into the game BeamNG (see [BeamNG Implementation](#BeamNG-Implementation)).

When running the script, a window will popup showing the detections that are made:

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/imgs/LaneDetection/BNG1_ALL.jpg" width="49.5%"/> 
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/imgs/LaneDetection/BNG2_ALL.jpg" width="49.5%"/> 
</p>

It is also possible to capture a specific individual frames by pressing the key `t`. They will automatically be saved to `save_path`. By pressing the key `b`the script will stop.

### BeamNG Implementation
The lane detection system can be implemented into BeamNG.

#### Setup
In order to implement the system into BeamNG, it is necessary to record the game feed in real time. To do so OBS's Virtual Camera can be used: [Open Broadcaster Software](https://obsproject.com)

Once it has been installed and configured, the game screen has to be added to OBS's scene and finally the virtual camera can be enabled.

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/imgs/Setup/captura_escena.jpg" width="49.5%"/> 
</p>

For the best performance of the lane detection system, the camera should be positioned on front and on top of the car's hood. To do so the game's "free camera" can be used by pressing the `4` key and then moving the camera with `w` and the mouse. Any objects that are within the green surface shown in the system's visualisation screen will interfere with the detection of the lanes, so it might be necessary to hide the *HUD*.

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/imgs/Setup/captura_beamng.jpg" width="49.5%"/> 
</p>

#### How to run
There are two scripts that should be running at the same time:

The first one is `lane_detection.py [camera index] --beamng (port)`. The default port is 5455, and it must be the same as in the other script.

The second one is `control_system_beamng.py (port)`. This script emulates the controller that is used ingame to steer the vehicle.

Once both scripts are running, the autonomous driving system can be activated or deactivated by pressing `l`, and the vehicle will start steering on its own in order to keep itself within the lanes.

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/gifs/lane_det.gif" width="49.5%"/> 
</p>


****

## Object detection
The objective of this subsystem is to detect objects within the road, mainly other vehicles, traffic lights and pedestrians. To do so the dataset '[COCO Traffic](https://github.com/daved01/cocoTraffic)' (a subset of [COCO](https://cocodataset.org/#home)) has been used. It has been trained on YOLO-v8 segmentation model. The trained weights are available [here](https://drive.google.com/file/d/1gcNM_fOjNqVvq6JlG9w0AcTk5Qvnsyqb/view).

Before traning this object detector, I also attempted training a model to recognise street signs using the [German Traffic Sign Detection Benchmark](https://benchmark.ini.rub.de/gtsdb_dataset.html). The trained weights are also available [here](https://drive.google.com/file/d/1Usx_yGCzuvc_gF7RaQlVNrUGLFFWtBxX/view).

The script to run predictions on the model is `Object_Detection/predict.py`. When running it, it creates a file selection popup to select the model. After that, until it receives a `stop` input it asks for the input media to process and displays the results.

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/imgs/Everything_example.jpg" width="49.5%"/> 
</p>

****

## Robot car implementation
As mentioned previously, the autonomous driving system was also implemented into a robot car. The car is able to detect lane markings on a circuit track and follow them.

<p align="center">
<img src="https://github.com/Algreen333/TR_AutonomousDriving/blob/main/Resources/gifs/picar.gif" width="49.5%"/> 
</p>


### Setup
First and foremost the raspberry pi has to be setup with a compatible os, preferrably a 64 bit one. The required libraries can be installed with the requirements file found in the `Picar` folder. The scripts will need to be modified in order to set the correct pins to control the motors and the steering.
Another thing to take into account is that for this project I have used the Raspberry Pi Camera 3 Wide, other parameters might have to be changed if using another camera.

### Scripts
The scripts can be found in `Picar`:

#### main.py
This is the main script which lets the robot car run on its own. When running the script, a Flask server is opened on port 5000. Then the server can be accessed through any browser (`http://raspberry_ip:5000/route`). Once any route is accessed, the robot will start moving and the camera's footage will be viewed on the webpage. There are various routes that can be accessed:

- `/raw`: This displays the raw footage from the camera
- `/video_feed`: This displays the raw footage with text for the servos steering values.
- `/canny`: This displays the canny edge output.
- `/blurred`: This displays the blurred output from the preprocessing stage.
- `/histequ`: This displays the CLAHE histogram equalization output from the preprocessing stage.

Apart from dislpaying the camera footage, it will also be saved to `./video/VID_YYYYMMDD_HH-MM-SS.mp4` inside the raspberry's working directory.

#### client.py and server.py
These two scripts are an additional tool i built to control the robot car remotely from another computer using a controller.

The server script must be run from the computer, which also has the controller conected:
```bash
    python server.py <adress>
```
The client script must be run from the Raspbery Pi:
```bash
    python client.py <adress>
```
The address must be of the form `computer_ip:port`.

When the two scripts are running and connected, the robot car can start to be driven with the controller.