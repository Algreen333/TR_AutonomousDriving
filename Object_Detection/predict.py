from ultralytics import YOLO
from tkinter import filedialog
print("imported")

model_path = filedialog.askopenfilename()

model = YOLO(model_path)
print("model loaded")

print("input stop to break...")

while True:
    if input() == "stop":
        break
    else:
        try:
            input_image = filedialog.askopenfilename()
            results = model.predict(input_image, device="cpu", imgsz=[1280, 720], show=True, save=True)
            print(results)
        except: pass