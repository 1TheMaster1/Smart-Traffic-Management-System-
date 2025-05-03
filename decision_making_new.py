import serial
import time
from ai_module import main as get_lane_counts

# Serial communication with ESP32
ser = None
#ser = serial.Serial('COM5', 9600, timeout=1) # Open the serial port (replace with your actual port)
#time.sleep(2)  # Allow ESP32 time to reset after serial connection

# Example car counts (These values will be updated dynamically based on the CV model)
car_counts = [1, 2, 2, 3]  # Number of cars detected in each lane (example)

# Example lane weights 
lane_weights = [1.5, 1, 1.5, 1]  # Weight of each lane (e.g., Lane 1: weight 1, Lane 2: weight 2, etc.)

# Example maximum car count per lane
max_capacity = [2, 3, 2, 3]

ultra_check = [0, 1, 0, 1]

#Function to get car counts from CV model
def set_car_counts():
    car_counts = get_lane_counts()
    if car_counts is None:
        print("Failed to get car counts.")
        car_counts = [0, 0, 0, 0]  # fallback values
    print(f"car counts = {car_counts}")
    return car_counts

# Function to read data from ESP32 and update car counts
def update_car_counts():
    line = ser.readline().decode().strip()
    if line.startswith("ULTRA:"):
            ultra_check = list(map(int, line.replace("ULTRA:", "").split(',')))

    # For each lane, if status is 1 (indicating a car), set the count to max_capacity
    for i in range(4):       
        # If car is detected, set lane to maximum capacity
        if ultra_check[i] == 1:
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
    message = f"laneTimes:{','.join(map(str, green_durations))};laneOrder:{','.join(map(str, lane_order))}\n"
    ser.write(message.encode())

def traffic_light_loop():
    # Start the traffic light cycle
    traffic_cycle_counter = 0  # To keep track of how many traffic cycles have passed
    while True:
        # Wait until ESP32 sends "READY"
        while True:
            if ser.in_waiting:
                line = ser.readline().decode().strip()
            print(f"ESP32 says: {line}")
            if line.startswith("READY"):
                break

        traffic_cycle_counter += 1
        print(f"Traffic cycle: {traffic_cycle_counter}")

        #--- Reset car counts
        car_counts = [0, 0, 0, 0]

        #--- Get car counts from CV
        car_counts = set_car_counts()

        #--- Update car count based on ultrasonic
        if all(c == 0 for c in car_counts):
            car_counts = update_car_counts()

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

def main():
    print("Starting traffic light control system...")
    try:
        traffic_light_loop()
    except Exception as e:
        print(f"Exception occurred\n{e}")
    finally:
        if ser and ser.is_open:
            ser.close()
            print("Serial port closed.")

if __name__ == "__main__":
    main()