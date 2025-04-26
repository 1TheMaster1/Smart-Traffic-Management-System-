from ultralytics import YOLO
import cv2
import numpy as np
import requests


model = YOLO("best.pt")  # Load YOLOv8 model

lanes = None  

def letterbox_image(image, target_size=(640, 640), color=(0,0,0)):
    """
    Resize image to fit inside target_size while preserving aspect ratio.
    Pads with black color.
    """
    original_h, original_w = image.shape[:2]
    target_w, target_h = target_size

    scale = min(target_w / original_w, target_h / original_h)
    new_w = int(original_w * scale)
    new_h = int(original_h * scale)

    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # Compute padding
    top = (target_h - new_h) // 2
    bottom = target_h - new_h - top
    left = (target_w - new_w) // 2
    right = target_w - new_w - left

    # Add border
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return padded

def capture_frame(ip, port):
  url=f'http://{ip}:{port}/shot.jpg'  #construct url for webcam stream
  try:
    response = requests.get(url, timeout=5) #http GET request for jpg img
    if response.status_code == 200: #success

      #response.content -> raw byte data
      #uint8 -> unsigned 8-bit ints -> (0,255) -> standard for greycale/rgb
      img_arr = np.asarray(bytearray(response.content), np.uint8)

      frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR) #IMREAD_COLOR -> read img in color instead of greyscale
      frame = cv2.resize(frame, (640,640))

      #good for debugging but bad for performance and unnecessary --> detect_cars() can take the actual frame as a parameter (yolo supports numpy arrays too)
      """filename = f"capture_{int(time.time())}.jpg"
      cv2.imwrite(filename, frame)"""

      return frame 

    else:
      print(f"failed to fetch img -> status code = {response.status_code}")
      return None
  
  except requests.exceptions.RequestException as e:
        print(f"exception occured ->\n{e}")
        return None

def detect_cars(frame):
  if frame is None:
        print("no frame to run inference on")
        return None
  try:
    results = model(frame)
  except Exception as e:
        print(f"exception occurred during inference ->\n{e}")
        return None
  if results[0] is not None:
      results[0].show()
  return results[0]

def extract_boxes(result):
  boxes = []  

  if not hasattr(result, 'boxes'): 
        print("problem inference")
        return None

  if len(result.boxes)==0:
      print("no boxes in image")
      return None

  for box in result.boxes:
    try:
      cx, cy, w, h = box.xywh[0]
      boxes.append((cx.item(), cy.item()))  #convert tensor elements to float
    except (IndexError,ValueError, AttributeError, TypeError) as e:
            print(f"box skipped -> exception occurred ->\n{e}")
  
  return boxes

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
    
 
    print("Lane Definitions (Polygons):")
    for i, poly in enumerate(lanes_polygons):
        print(f"Lane {i}: {poly}")
    
    return lanes_polygons

def get_lane_counts(boxes,lanes): 
    lane_counts = [0, 0, 0, 0]
    for cx, cy in boxes:
        for i, lane in enumerate(lanes):
            contour = np.array(lane, dtype=np.int32) #Convert the polygon point list into a NumPy array (OpenCV expects contours as NumPy arrays).
            if cv2.pointPolygonTest(contour, (cx, cy), False) >= 0:
                lane_counts[i] += 1
                break
    return lane_counts

def process_frame(ip, port, lanes=None, frame=None):
    frame = capture_frame(ip, port)
    result = detect_cars(frame)
    boxes = extract_boxes(result)
    lane_counts = get_lane_counts(boxes,lanes)
    return lane_counts

def main():
    global lanes
    ip = "192.168.1.57"
    port = 8080
    print("Capturing image from camera...")
    frame = capture_frame(ip, port)
    if frame is None:
        print("Failed to capture frame. Please check your IP/stream.")
        return
    saved = cv2.imwrite("capture.jpg", frame)
    if saved:
        print("capture.jpg successfully saved.")
    else:
        print("Failed to save capture.jpg.")
        return
    
    if lanes is None:
        print("Opening interactive lane definition tool...")
        lanes = define_lanes_interactively("capture.jpg")
        print("Lanes defined:", lanes)
        
    counts = process_frame("192.168.1.100", 8080, lanes=lanes, frame=frame)
    if counts is None:
      print("Failed to process frame.")
    else:
      print(f"Cars detected per lane: {counts}")
    return counts


if __name__ == "__main__":
    main()