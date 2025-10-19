from threading import Thread
import cv2
from flask import Flask, Response
import numpy as np
import math
import string
import random
from simple_pid import PID
from gpiozero import AngularServo, Motor
from gpiozero.pins.native import NativeFactory
import time as t
from picamera2 import Picamera2
from libcamera import controls


# Pins and Raspi stuff
factory = NativeFactory()
steer = AngularServo(4, min_angle=-90, max_angle=90, pin_factory=factory)
m1 = Motor(14, 15)
m2 = Motor(18, 17)

h, w = (720, 1280)

triangle = np.array([[(0,h-math.floor(h*0.35)),(0, h), (w, h), (w,h-math.floor(h*0.35)),(math.floor(w/2+(w*0.2)), math.floor(h*0.55)), (math.floor(w/2-(w*0.2)), math.floor(h*0.55))]])

config_offset = [-10, -5, 3], [1, 1] #Offsets for the servos and direction of the motors

slope_weight = 120
dist_weight = 0.8
one_line_slope_weight = 140
one_line_dist_weight = 0.8


kP, kI, kD = 0.004, 0, 0.002
max_err, min_err, error_mult = 400, -400, 0.3
clamp_val = 0.95
    
pid = PID(kP, kI, kD, setpoint=0, output_limits=(-1,1))

def clamp(a, amin, amax):
    if a < amin: return amin
    elif a > amax: return amax
    else: return a

class VideoStreamWidget(object):
    def __init__(self):
        self.picam2 = Picamera2()
        self.picam2.configure(self.picam2.create_preview_configuration({"size":(1280, 720), "format":"RGB888"}))
        self.picam2.set_controls({"AeExposureMode": controls.AeExposureModeEnum.Normal, "AfSpeed":controls.AfSpeedEnum.Fast, "FrameRate":56.03})
        self.picam2.start()

        # Start the thread to read frames from the video stream
        self.thread = Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        # Read the next frame from the stream in a different thread
        while True:
            start_time = t.time()
            im = self.picam2.capture_array()
            if not im.any():
                self.success = False
                self.frame = im
            else:
                self.success = True
                resized = cv2.resize(im, (w, h))
                self.frame = cv2.rotate(resized, cv2.ROTATE_180)
                self.img, self.error, self.slope, self.intersect, self.lines_n = main_processing(self.success, self.frame)
            self.delta_time = t.time()-start_time
            
    def show_frame(self):
        # Display frames in main program
        cv2.imshow('frame', self.frame)
        key = cv2.waitKey(1)
        if key == ord('q'):
            self.capture.release()
            cv2.destroyAllWindows()
            exit(1)

    def out_frame(self):
        return (self.success, self.frame, self.delta_time)
    
    def out_vals(self):
        return self.img, self.error, self.slope, self.intersect, self.lines_n


#Make image of the mask
def poly_image(image):
   h,w = image.shape[:2]
   copy = image.copy()
   cv2.fillPoly(copy, triangle, color=(0, 255, 0))
   return cv2.addWeighted(image, 0.85, copy, 0.15, 0)
#Gaussian blur to reduce noise and smoothen the image
def gauss(image, kernel=(5,5)):
  return cv2.GaussianBlur(image,kernel,0)
#Canny edge detection
def canny(image):
    edges = cv2.Canny(image,50,150)
    return edges
#Area of interest (detect filter lanes)
def area_of_interest(image, poly=triangle):
   mask = np.zeros_like(image)
   cv2.fillPoly(mask, poly, 255)
   masked_image = cv2.bitwise_and(image, mask)
   return masked_image
#Draw lines on image
def display_lines(image, lines, color=(255,0,0)):
   try:
    if lines is not None:
       for line in lines:
          x1,y1,x2,y2 = line.reshape(4)
          cv2.line(image,(x1,y1),(x2,y2),color,10)
   except:
      pass
   return image
#Line optimisation
def average_slope_intercept(image,lines):
    try:
        leftFit= []
        rightFit = []
        wrong_lines = [(638,479,638,288), (638, 479, 638, 400)]
        for line in lines:
            x1, y1, x2, y2 = line.reshape(4)
            if not (x1, y1, x2, y2) in wrong_lines and x1 != x2:
                parameters = np.polyfit((x1,x2),(y1,y2), 1)
                slope = parameters[0]
                intercept = parameters[1]
                if slope < 0:
                    leftFit.append((slope, intercept))
                else:
                    rightFit.append((slope, intercept))
        leftFitAVG = np.average(leftFit, axis=0)
        rightFitAVG = np.average(rightFit, axis=0)
        l_line, leftLine = make_coords(image, leftFitAVG)
        r_line, rightLine = make_coords(image, rightFitAVG)
        if l_line == "no_line" and r_line == "no_line":
            return 0, None
        elif l_line == "no_line":
            return 1, np.array([rightLine])
        elif r_line == "no_line":
            return 1, np.array([leftLine])
        else:
            return 2, np.array([leftLine, rightLine])
    except:
        return 0, None
#Make coordinates of the lines from slope and intercept
def make_coords(image, line_parameters):
   try:
      slope, intercept = line_parameters
      y1 = image.shape[0]
      y2 = int(y1*(3/5))
      x1 = int((y1-intercept)/slope)
      x2 = int((y2-intercept)/slope)
      return "line", np.array([x1,y1,x2,y2])
   except:
      return "no_line", None
#Calcuate coords of average slope and intercept
def center_line(image, averaged_lines):
   left, right = averaged_lines
   lx1, y1, lx2, y2 = left.reshape(4)
   rx1, y1, rx2, y2 = right.reshape(4)
   x1 = math.floor((rx1+lx1) / 2)
   x2 = math.floor((rx2+lx2) / 2)
   line = np.array([x1,y1,x2,y2])
   return line
#Calculate the error of the vehicle based on the slope and intercept
def get_error(image, line):
   try:
      h, w = image.shape[:2]
      x1, y1, x2, y2 = line.reshape(4)
      m = (y2-y1)/(x2-x1)
      dist = w/2 - x1
      slope_error = (1/m)*slope_weight
      dist_error = dist*dist_weight
      error = slope_error + dist_error
      return error, m, dist
   except:
      return 0, 0, 0

#Processing of the image
def main_processing(success, frame):
    lane_image = np.copy(frame)
    canny_image = cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(lane_image,cv2.COLOR_RGB2GRAY),(5,5),0),50,150)
    cropped = area_of_interest(canny_image)
    lines = cv2.HoughLinesP(cropped,2,np.pi/180,80,np.array([]),minLineLength=40,maxLineGap=5)
    lines_n, averaged_lines = average_slope_intercept(frame, lines)
    if lines_n == 2:
        center = center_line(frame, averaged_lines)
        avg_line_img = display_lines(lane_image, averaged_lines, (255,0,0))
        output = display_lines(avg_line_img, [center], (0,255,255))
        error, m, intersect = get_error(frame, center)
    elif lines_n == 1:
        output = display_lines(lane_image, [averaged_lines], (255,0,0))
        x1, y1, x2, y2 = averaged_lines[0].reshape(4)
        m = (y2-y1)/(x2-x1)
        if m < 0:
            intersect = w/4 - x1
            dist_error = intersect*one_line_dist_weight
            try:
                slope_error = (1/m)*one_line_slope_weight
            except:
                slope_error = (1/m-0.01)*one_line_slope_weight
        else:
            intersect = 3*w/4 - x1
            dist_error = intersect*one_line_dist_weight
            try:
                slope_error = (1/m)*one_line_slope_weight
            except:
                slope_error = (1/m-0.01)*one_line_slope_weight
                
        error = slope_error + dist_error
    else:
        output = frame
        error = 0
        m = 0
        intersect = 0
    poly_img = poly_image(output)
    return (poly_img, error, m, intersect, lines_n)

#Generate frames for web display and control vehicle
def generate_frames(mode):
    try:
        file_name = t.strftime("./video/VID_%Y%m%d_%H-%M-%S.mp4", t.localtime())
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_vid = cv2.VideoWriter(file_name, fourcc, 6, (1280, 720))
        start_time = t.time()
        while True:
            prev_time = t.time()
            success, frame, deltaT = video_stream_widget.out_frame()
            if success:
                img, error, slope, intersect, lines_n  = video_stream_widget.out_vals()
                if mode == "main":
                    output = img
                elif mode == "canny":
                    output = cv2.cvtColor(cv2.Canny(cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY),(5,5),0),50,150), cv2.COLOR_GRAY2BGR)
                elif mode == "blurred":
                    output = cv2.GaussianBlur(cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY),(5,5),0)
                elif mode == "hist-equ":
                    hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                    h, s, v = cv2.split(hsv_image)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
                    v = clahe.apply(v)
                    hsv_image = cv2.merge([h, s, v])
                    output = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2BGR)
                elif mode == "raw":
                    output = frame
                control = clamp(pid(error*error_mult), -clamp_val, clamp_val)
                if mode != "raw":
                    cv2.putText(output, f"Control: {round(control, 3)} Error: {round(error, 3)}" , (4,20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
                    cv2.putText(output, f"Intersect: {round(intersect, 3)} Slope: {round(slope, 3)}", (4, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
                    cv2.putText(output, f"Time: {round((t.time()-start_time), 2)}", (4, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,255), 1)
                out_vid.write(output)
                _, jpeg = cv2.imencode('.jpg', output)
                frame_bytes = jpeg.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                if lines_n == 2:
                    m1.forward(0.35)
                    m2.forward(0.35)
                elif lines_n == 1:
                    m1.forward(0.3)
                    m2.forward(0.3)
                else:
                    m1.forward(0)
                    m2.forward(0)
            else: control = 0
            steer.angle = control*90
            print(f'Success: {success}; NumberOfLines: {lines_n}; Control: {round(control, 3)}; Error: {round(error, 3)}; Time: {round(deltaT, 3)}')
    finally: 
        m1.forward(0)
        m2.forward(0)
        steer.angle = 0
        out_vid.release()

letters = string.ascii_lowercase

def save_images(img):
    name = ''.join(random.choice(letters) for i in range(5))
    print(cv2.imwrite(f"./images/{name}.jpg", img))

video_stream_widget = VideoStreamWidget()

app = Flask(__name__)

@app.route('/')
def index():
    return """
<body>
<div class="container">
    <div class="row">
        <div class="col-lg-8  offset-lg-2">
            <h3 class="mt-5">Live Streaming</h3>
            <img src="/video_feed" width="70%">
        </div>
    </div>
</div>
</body>        
    """


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames("main"), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/canny")
def canny():
    return Response(generate_frames("canny"), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/blurred")
def blurred():
    return Response(generate_frames("blurred"), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/histequ")
def histequ():
    return Response(generate_frames("hist-equ"), mimetype='multipart/x-mixed-replace; boundary=frame')
@app.route("/raw")
def raw():
    return Response(generate_frames("raw"), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    video_stream_widget = VideoStreamWidget()
