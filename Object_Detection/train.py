import argparse
from ultralytics import YOLO

print("loaded yolo")

parser = argparse.ArgumentParser(prog="Yolo model trainer", description="Trains yolo model using the ultralytics/yolo library.")
parser.add_argument("train_file", type=str)
parser.add_argument("-w", "--weights", type=str, help="Weights path.", required=True)
parser.add_argument("-e", "--epochs", type=int, help="Epoch count.", required=True)
parser.add_argument("-s", "--imgsz", type=int, help="Image size.", required=True)
parser.add_argument("-d", "--device", type=int, help="Device id to use when training", required=False)

args = parser.parse_args()

yaml_file = args.train_file
model = YOLO(args.weights)

if args.device:
    model.train(data=yaml_file, epochs=args.epochs, imgsz=args.imgsz, device=args.device)
else:
    model.train(data=yaml_file, epochs=args.epochs, imgsz=args.imgsz, device="cpu")