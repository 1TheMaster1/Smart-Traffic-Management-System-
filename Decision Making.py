import serial
import time
from ai_module import main as get_lane_counts

# Serial communication with ESP32
#ser = serial.Serial('COM3', 9600)  # Open the serial port (replace with your actual port)

# Example car counts (These values will be updated dynamically based on the CV model)
car_counts = [1, 2, 2, 3]  # Number of cars detected in each lane (example)

# Example lane weights 
lane_weights = [1.5, 1, 1.5, 1]  # Weight of each lane (e.g., Lane 1: weight 1, Lane 2: weight 2, etc.)

# Example maximum car count per lane
max_capacity = [2, 3, 2, 3]

#Function to get car counts from CV model
def set_car_counts():
    car_counts = get_lane_counts()
    if car_counts is None:
        print("Failed to get car counts.")
        car_counts = [0, 0, 0, 0]  # fallback values
    return car_counts

# Function to read data from ESP32 and update car counts
def update_car_counts():
    # Read the line from ESP32
    line = ser.readline().decode('utf-8').strip()
    print(f"Received data: {line}")

    # Parse the lane status data
    lane_status = line.split('|')

    # For each lane, if status is 1 (indicating a car), set the count to max_capacity
    for i, status in enumerate(lane_status):
        # Extract car status (1 or 0)
        lane_data = status.split(':')
        car_status = int(lane_data[1].strip())
        
        # If car is detected, set lane to maximum capacity
        if car_status == 1:
            car_counts[i] = max_capacity[i]
    
    return car_counts

# Function to sort lanes based on their priority
def sort_lanes_by_priority(car_counts, lane_weights):
    lane_priorities = []
    
    # Calculate priority for each lane
    for i in range(4):
        priority = car_counts[i] * lane_weights[i]
        lane_priorities.append((i, priority))
    
    # Sort lanes by priority (highest priority first)
    lane_priorities.sort(key=lambda x: x[1], reverse=True)
    
    # Return the sorted order of lanes based on priority
    return [lane[0] for lane in lane_priorities]

#Function to calculate the green duration for each lane
def get_green_duration(car_counts):
    green_duration = []
    
    for i in range(4):
        duration = 2 * car_counts[i]
        green_duration.append(duration)

    return green_duration

# Function to send traffic order and durations to ESP32
def send_to_esp32(lane_order, green_durations):
    # Line 1: Order of the lanes (e.g., "3,0,1,2")
    order_line = ','.join(map(str, lane_order)) + '\n'
    ser.write(order_line.encode())

    # Line 2: Green light durations for each lane in that order (e.g., "10,15,8,12")
    duration_line = ','.join(map(str, green_durations)) + '\n'
    ser.write(duration_line.encode())

def traffic_light_loop():
    # Start the traffic light cycle
    traffic_cycle_counter = 0  # To keep track of how many traffic cycles have passed
    while True:
        traffic_cycle_counter += 1
        print(f"Traffic cycle: {traffic_cycle_counter}")

        #--- Get car counts from CV
        car_counts = set_car_counts()

        #--- Update car count based on ultrasonic
        #car_counts = update_car_counts()

        #--- Get the dynamic lane order based on current traffic (update in each cycle)
        dynamic_lane_order = sort_lanes_by_priority(car_counts, lane_weights)

        #--- Get green duration for each lane 
        green_duration = get_green_duration(car_counts)

        #--- Send data to ESP32
        send_to_esp32(dynamic_lane_order, green_duration)

        # --- Start rotating traffic lights based on dynamic lane order
        for lane_index in dynamic_lane_order:
            duration = green_duration[lane_index] # Set a default green duration for each lane, this can be dynamically adjusted

            #--- Greenn light phase
            print(f"Lane {lane_index + 1} -> GREEN for {duration} seconds")
            time.sleep(duration)  # Wait for the green light to finish

            #--- Yellow light phase
            print(f"Lane {lane_index + 1} -> YELLOW for 2 seconds")
            time.sleep(2)  # Keep yellow light on for 2 seconds

            #--- Red light phase
            print(f"All lanes -> RED for 1 second")       
            time.sleep(1)  # Wait for 1 second with all red lights on

        time.sleep(3)  # Small delay before starting the next traffic cycle
