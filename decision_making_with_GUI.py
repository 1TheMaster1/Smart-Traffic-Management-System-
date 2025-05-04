import serial
import time
import threading
import tkinter as tk
from tkinter import ttk
from ai_module import main as get_lane_counts

# Serial setup
ser = serial.Serial('COM3', 9600, timeout=1)
time.sleep(2)

lane_weights = [1.2, 1, 1.2, 1]
max_capacity = [2, 3, 2, 3]

# --- Functions from your code ---

def set_car_counts():
    counts = get_lane_counts()
    if counts is None:
        counts = [0, 0, 0, 0]
    return counts

def parse_ultrasonic_line(line):
    parts = line.split(',')
    return [int(parts[i + 1]) for i in range(1, len(parts), 2)]

def update_car_counts(car_counts):
    line = ser.readline().decode().strip()
    if line.startswith("Ultra"):
        ultra_check = parse_ultrasonic_line(line)
        for i in range(4):
            if ultra_check[i] == 1:
                car_counts[i] = max_capacity[i]
        update_status_labels(car_counts, ultra_check)

def sort_lanes_by_priority(car_counts, lane_weights):
    lane_priorities = [(i, car_counts[i] * lane_weights[i]) for i in range(4)]
    lane_priorities.sort(key=lambda x: x[1], reverse=True)
    return [lane[0] for lane in lane_priorities]

def get_green_duration(car_counts):
    return [2 * c for c in car_counts]

def send_to_esp32(lane_order, lane_times):
    ser.write(f"Times,{','.join(map(str, lane_times))}\n".encode())
    time.sleep(0.1)
    ser.write(f"Order,{','.join(map(str, lane_order))}\n".encode())

# --- GUI-related functions ---

def update_status_labels(counts, sensors=None):
    for i in range(4):
        car_labels[i]['text'] = f"Lane {i+1} Cars: {counts[i]}"
        if sensors:
            sensor_labels[i]['text'] = f"Ultrasonic: {'Yes' if sensors[i] else 'No'}"

def update_phase_label(lane, phase):
    status_label['text'] = f"Lane {lane+1} → {phase}"

def traffic_light_loop():

    # --- Reset & update car counts
    counts = [0, 0, 0, 0]
    counts = set_car_counts()
    update_car_counts(counts)

    # --- Determine order and durations
    lane_order = sort_lanes_by_priority(counts, lane_weights)
    durations = get_green_duration(counts)

    # --- Send to ESP32
    send_to_esp32(lane_order, durations)

    # --- Update GUI with lane order and durations
    order_label['text'] = f"Lane Order: {[lane+1 for lane in lane_order]}"
    duration_label['text'] = f"Green Durations: {durations}"


    # --- Display lane phases
    for lane in lane_order:
        update_phase_label(lane, f"GREEN ({durations[lane]}s)")
        time.sleep(durations[lane])
        update_phase_label(lane, "YELLOW (2s)")
        time.sleep(2)
        update_phase_label(lane, "RED (1s)")
        time.sleep(1)

    status_label['text'] = "Waiting for ESP32..."

def wait_for_ready_and_start():
    while True:
        line = ser.readline().decode().strip()
        if "Ready" in line:
            traffic_light_loop()

def start_traffic_loop():
    threading.Thread(target=wait_for_ready_and_start, daemon=True).start()

# --- Tkinter GUI Setup ---

root = tk.Tk()
root.title("Smart Traffic Controller")
root.geometry("400x400")

frame = ttk.Frame(root, padding=20)
frame.pack(fill=tk.BOTH, expand=True)

car_labels = []
sensor_labels = []

for i in range(4):
    lbl_car = ttk.Label(frame, text=f"Lane {i+1} Cars: 0")
    lbl_sensor = ttk.Label(frame, text=f"Ultrasonic: N/A")
    lbl_car.pack()
    lbl_sensor.pack()
    car_labels.append(lbl_car)
    sensor_labels.append(lbl_sensor)

status_label = ttk.Label(frame, text="Waiting for Start...", font=('Arial', 14, 'bold'))
status_label.pack(pady=20)

order_label = ttk.Label(frame, text="Lane Order: N/A")
order_label.pack()

duration_label = ttk.Label(frame, text="Green Durations: N/A")
duration_label.pack()

start_button = ttk.Button(frame, text="Start Traffic Loop", command=start_traffic_loop)
start_button.pack()

root.mainloop()
