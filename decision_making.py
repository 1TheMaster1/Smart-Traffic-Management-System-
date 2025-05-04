import serial
import time
from ai_module import main as get_lane_counts

ser = serial.Serial('COM3', 9600, timeout=1)  # Change COM port as needed
time.sleep(2)  # Wait for connection

lane_weights = [1.2, 1, 1.2, 1]  # Weight of each lane (e.g., Lane 1: weight 1, Lane 2: weight 2, etc.)

max_capacity = [2, 3, 2, 3]

#Function to get car counts from CV model
def set_car_counts():
    car_counts = get_lane_counts()
    if car_counts is None:
        print("Failed to get car counts.")
        car_counts = [0, 0, 0, 0]  # fallback values
    print(f"car counts = {car_counts}")    

    return car_counts

def parse_ultrasonic_line(line):
    parts = line.split(',')
    # Format: "Ultra,L1,1,L2,0,L3,0,L4,1"
    values = [int(parts[i + 1]) for i in range(1, len(parts), 2)]
    return values

# Function to read data from ESP32 and update car counts
def update_car_counts(car_counts):
    line = ser.readline().decode().strip()
    if line.startswith("Ultra"):
            ultra_check = parse_ultrasonic_line(line)

    # For each lane, if status is 1 (indicating a car), set the count to max_capacity
    for i in range(4):       
        # If car is detected, set lane to maximum capacity
        if ultra_check[i] == 1:
            car_counts[i] = max_capacity[i]

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
def send_to_esp32(lane_order, lane_times):
    print(lane_times)
    print([x + 1 for x in lane_order])
    ser.write(f"Times,{','.join(map(str, lane_times))}\n".encode())
    time.sleep(0.1)
    ser.write(f"Order,{','.join(map(str, lane_order))}\n".encode())

def traffic_light_loop():
    # Start the traffic light cycle
    traffic_cycle_counter = 0  # To keep track of how many traffic cycles have passed

    traffic_cycle_counter += 1
    print(f"Traffic cycle: {traffic_cycle_counter}")

    #--- Reset car counts
    car_counts = [0, 0, 0, 0]

    #--- Get car counts from CV
    car_counts = set_car_counts()

    #--- Update car count based on ultrasonic
    update_car_counts(car_counts)

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

        #--- Yellow light phase
        print(f"Lane {lane_index + 1} -> YELLOW for 2 seconds")

        #--- Red light phase
        print(f"All lanes -> RED for 1 second")     

while True:
    # Wait for ESP32 to send "Ready"
    while True:
        line = ser.readline().decode().strip()
        print("ESP:", line)
        if "Ready" in line:
            break

    traffic_light_loop()