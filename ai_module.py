from ultralytics import YOLO
import cv2

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