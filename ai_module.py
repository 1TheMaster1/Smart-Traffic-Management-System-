from ultralytics import YOLO
import cv2
import numpy as np

model = YOLO("best.pt")  # Load YOLOv8 model
lanes=[]

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
  

def detect_cars():
  frame_path="capture.jpg"
  results = model(frame_path)
  return results[0]

def extract_boxes(result):
  boxes = []
  for box in result.boxes:
    x1, y1, x2, y2 = box.xyxy[0]
    boxes.append((float(x1), float(y1), float(x2), float(y2))) #convert tensor elements to float
    print(f"Box coordinates: ({x1}, {y1}, {x2}, {y2})")
  return boxes

def poly_to_rect(points): #change interactive tool output to rectangle format
    if not points:
        raise ValueError("no points detected")
    
    x_values = [p[0] for p in points]
    y_values = [p[1] for p in points]
    return(min(x_values), min(y_values), max(x_values), max(y_values))

def define_lanes_interactively(image_path): #interactive tool to define lane boundaries
    lane_points = []
    current_lane = []
    lanes_polygons = []
    
    def click_event(event, x, y, flags, params):
        nonlocal current_lane, lanes_polygons, img_copy
        
        if event == cv2.EVENT_LBUTTONDOWN:
            # Add point to current lane
            current_lane.append((x, y))
            # Draw point on image
            cv2.circle(img_copy, (x, y), 5, (0, 0, 255), -1)
            cv2.imshow('Lane Definition Tool', img_copy)
            print(f"Added point: ({x}, {y})")
            
        elif event == cv2.EVENT_RBUTTONDOWN:
            # Complete the current lane if it has enough points
            if len(current_lane) >= 3:
                lanes_polygons.append(current_lane.copy())
                
                # Draw the completed polygon
                pts = np.array(current_lane, np.int32).reshape((-1, 1, 2))
                cv2.polylines(img_copy, [pts], True, (0, 255, 0), 2)
                cv2.imshow('Lane Definition Tool', img_copy)
                
                # Reset for next lane
                current_lane = []
                print(f"Lane {len(lanes_polygons)} completed. Right-click again for next lane.")
    
    # Load the image
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image {image_path}")
        return []
        
    img_copy = img.copy()
    
    # Create window and set mouse callback
    cv2.imshow('Lane Definition Tool', img)
    cv2.setMouseCallback('Lane Definition Tool', click_event)
    
    print("Left-click to add points. Right-click to complete a lane.")
    print("Press any key when done with all lanes.")
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    
    # Convert polygons to rectangles
    rectangles = []
    for poly in lanes_polygons:
        rect = poly_to_rect(poly)
        rectangles.append(rect)
   
    print("Lane Definitions (Rectangles):")
    for i, rect in enumerate(rectangles):
        print(f"Lane {i}: {rect}")
    
    return rectangles

def get_lane_counts(boxes): 
    lane_counts = [0, 0, 0, 0]

    for box in boxes:
       x1, y1, x2, y2 = box
       center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2

       for i, lane in enumerate(lanes):
          lane_x1, lane_y1, lane_x2, lane_y2 = lane
          if lane_x1 <= center_x <= lane_x2 and lane_y1 <= center_y <= lane_y2:
              lane_counts[i] += 1
              break
    return lane_counts

def process_frame(ip, port):
    frame = capture_frame(ip, port)
    if frame is None:
        print("Error: No frame captured.")
        return None 
    result = detect_cars()
    boxes = extract_boxes(result)
    lane_counts = get_lane_counts(boxes)
    return lane_counts

if __name__ == "__main__":
    # To define lanes first time, uncomment the lines below:
    # frame = capture_frame("192.168.1.100", 8080)
    # cv2.imwrite("capture.jpg", frame)
    # lanes = define_lanes_interactively("capture.jpg")

    counts = process_frame("192.168.1.100", 8080)
    if counts is None:
      print("Failed to process frame.")
    else:
      print(f"Cars detected per lane: {counts}")