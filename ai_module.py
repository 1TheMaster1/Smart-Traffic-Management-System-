from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("best.pt")  # Load YOLOv8 model

def capture_frame(ip, port):
  url=f'http://{ip}:{port}/shot.jpg'  #construct url for webcam stream
  cap = cv2.VideoCapture(url) #connect to webcam stream
  ret, frame = cap.read() #fetch latest frame
  if ret:
    cv2.imwrite("capture.jpg", frame)  #save image locally
    return frame  #NumPy array representing image
  else:
    print("Failed to capture image")
    return None
  

def detect_cars(frame_path="capture.jpg"):
  results = model(frame_path)
  return results[0]

def extract_boxes(result):
  boxes = []
  for box in result.boxes:
    x1, y1, x2, y2 = box.xyxy[0]
    boxes.append((float(x1), float(y1), float(x2), float(y2))) #convert tensor elements to float
    print(f"Box coordinates: ({x1}, {y1}, {x2}, {y2})")
  return boxes

