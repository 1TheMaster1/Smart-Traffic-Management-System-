import serial
import time

ser = serial.Serial('COM3', 9600, timeout=1)  # Change COM port as needed
time.sleep(2)  # Wait for connection

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

    line = ser.readline().decode().strip()

    #--- Get the dynamic lane order based on current traffic (update in each cycle)
    lane_order = [0, 1, 2, 3]

    #--- Get green duration for each lane 
    green_duration = [10, 10, 10, 10]

    #--- Send data to ESP32
    send_to_esp32(lane_order, green_duration)

    # --- Start rotating traffic lights based on dynamic lane order
    for lane_index in lane_order:
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