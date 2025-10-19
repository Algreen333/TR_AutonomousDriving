import socket
from threading import Thread
from controller import PS4Controller

ps4 = PS4Controller()

serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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

serversocket.bind((host, port))


class client(Thread):
    ps4_active = None
    def __init__(self, socket, address, ps4):
        Thread.__init__(self)
        self.sock = socket
        self.addr = address
        self.start()
        self.ps4 = ps4
        try:
            ps4.start()
            self.ps4_active = True
        except:
            self.ps4_active = False

    def run(self):
        while True:
            try:
                message = self.sock.recv(1024)
                if not message:
                    break
                print('Client:', message.decode())
                if self.ps4_active:
                    axis_data, button_data, _ = ps4.read()
                    msg = f"{axis_data}; {button_data}".encode()
                else:
                    msg = b'500'
                self.sock.send(msg)
            except ConnectionResetError:
                print(f'Client disconnected')
                break
        self.sock.close()
        ps4.stop()


serversocket.listen(5)
print(f'Server started and listening on {host}:{port}')
while True:
    clientsocket, address = serversocket.accept()
    print(f'New client connected: {address[0]}:{address[1]}')
    client(clientsocket, address, ps4)

