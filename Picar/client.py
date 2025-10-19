import socket
import ast
from gpiozero import Servo, Motor
import time as t

#Argparse
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("address", type=str, default="192.168.1.53:8000", nargs="?", action="store",
                    help="Server address and port. Default is '192.168.1.53:8000'")
args = parser.parse_args()

address = args.address
address = address.split(":")
host = address[0]
port = int(address[1])


# Pins and Raspi stuff
st_PIN = 4

steer = Servo(st_PIN)
m1 = Motor(14, 15)
m2 = Motor(18, 17)

speed_mult = 0.8
steer_mult = 0.9
threshold = 0.1



# Socket stuff
clientsocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientsocket.connect((host, port))



def picar_control(status, axis={}, buttons={}):
    if status == True:
        try:
            throt = (axis[5]+1)/2
            brake = (axis[4]+1)/2
            steer = axis[0]
        except: 
            throt = 0
            brake = 0
            steer = 0
    else: 
        throt = 0
        brake = 0
        steer = 0
    return throt, brake, steer



# Main loop
while True:
    start_time = t.time()
    message = "test".encode()
    clientsocket.send(b'test')
    response = clientsocket.recv(1024)
    msg = response.decode()
    if msg != "500":
        axis_data, button_data = msg.split("; ")
        axis = ast.literal_eval(axis_data)
        buttons = ast.literal_eval(button_data)
        end_time = t.time()
        controls = picar_control(True, axis, buttons)
        steer.value = controls[2]*steer_mult
        if controls[0]>threshold:
            m1.forward(controls[0]*speed_mult)
            m2.forward(controls[0]*speed_mult)
        elif controls[1]>threshold:
            m1.backward(controls[1]*speed_mult)
            m2.backward(controls[1]*speed_mult)
        else:
            m1.stop()
            m2.stop()
        print(f"{controls};   Elapsed time: {end_time - start_time}")
    else: print(msg)

clientsocket.close()