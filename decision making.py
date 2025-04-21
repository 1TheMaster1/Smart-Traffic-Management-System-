import serial
import time

ser = serial.Serial('COM3', 9600)
time.sleep(2)

def read_signals():
    ultrasonic = [0, 0, 0, 0]
    ir = [0, 0, 0, 0]

    while ser.in_waiting:
        line = ser.readline().decode().strip()
        print("Received:", line)
        if line.startswith("ULTRA:"):
            ultrasonic = list(map(int, line[6:].split(',')))
        elif line.startswith("IR:"):
            ir = list(map(int, line[3:].split(',')))

    return ultrasonic, ir

def calculate_timings(ultra, ir):
    car_counts = {}
    ir_detected = {}

    for i in range(4):
        lane = str(i + 1)
        car_counts[lane] = ultra[i]  # 0 or 1
        ir_detected[lane] = bool(ir[i])

    # Apply weights
    weights = {}
    for lane in car_counts:
        weights[lane] = 1.0 + (2.0 if ir_detected[lane] else 0.0)

    # Green time calculation
    CYCLE_DURATION = 60
    MIN_GREEN = 6
    total_weighted = sum(car_counts[l] * weights[l] for l in car_counts)
    green_times = {}

    for l in car_counts:
        w = car_counts[l] * weights[l]
        green_times[l] = max(MIN_GREEN, int((w / total_weighted) * CYCLE_DURATION)) if total_weighted > 0 else MIN_GREEN

    return green_times

def send_to_esp32(green_times, lane_order):
    lane_times = [green_times['1'], green_times['2'], green_times['3'], green_times['4']]
    ser.write(f"TIMES:{','.join(str(t) for t in lane_times)}\n".encode())
    time.sleep(0.5)
    ser.write(f"ORDER:{','.join(str(i) for i in lane_order)}\n".encode())
    print("✅ Sent timings:", lane_times)

# Main loop
while True:
    ultra, ir = read_signals()
    green_times = calculate_timings(ultra, ir)
    lane_order = [0, 2, 1, 3]  # Customizable
    send_to_esp32(green_times, lane_order)
    time.sleep(60)  # Update every minute
