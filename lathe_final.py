import serial
import time
import re
import socket
import numpy as np

# --- Configuration Settings ---
SERIAL_PORT = 'COM8'
BAUD_RATE = 115200
TARGET_DUTY = 80.0          
DUTY_TOLERANCE = 3.0        
RMS_WINDOW_SIZE = 5         

# --- ADJUST THIS THRESHOLD BASED ON YOUR REAL WORKBENCH READINGS ---
# If your motor hovers around 0.3A - 0.5A at 80%, set this to 1.00A or 1.20A.
RMS_ANOMALY_THRESHOLD = 0.7 

# --- Networking Setup (UDP) ---
UDP_IP = "127.0.0.1"  
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01) 
    time.sleep(1.5)
    print(f"[STEP 1] Connected to {SERIAL_PORT} successfully!")
    print(f"-> Safety Anomaly Baseline Window Bound: {RMS_ANOMALY_THRESHOLD} A")
except Exception as e:
    print(f"Serial Connection Failed: {e}")
    exit()

live_current_buffer = []
buzzer_state = False

def parse_serial(line):
    v = re.search(r"V:([\d.]+)", line)
    a = re.search(r"A:([\d.]+)", line)
    p = re.search(r"P:([\d.]+)", line)
    d = re.search(r"D:([\d.]+)", line)
    if v and a and p and d:
        return float(v.group(1)), float(a.group(1)), float(p.group(1)), float(d.group(1))
    return None

print(f"\n[STEP 2] Adjust lathe potentiometer speed to target {TARGET_DUTY}%...")

try:
    while True:
        if ser.in_waiting > 0:
            if ser.in_waiting > 150:
                ser.reset_input_buffer()
                
            raw_line = ser.readline().decode('utf-8', errors='ignore').strip()
            data = parse_serial(raw_line)
            
            if data:
                voltage, current, power, duty = data
                
                # Always stream data to the separate graph window over UDP
                network_packet = f"{current},{power},{duty}"
                sock.sendto(network_packet.encode(), (UDP_IP, UDP_PORT))
                
                # Check if we are inside our 80% operation speed gate
                if abs(duty - TARGET_DUTY) <= DUTY_TOLERANCE:
                    
                    # Append current to the moving buffer array
                    live_current_buffer.append(current)
                    if len(live_current_buffer) > RMS_WINDOW_SIZE:
                        live_current_buffer.pop(0)
                        
                    # --- FIXED: WARM-UP SENSOR RULE ---
                    # We need at least 4 samples (around 0.5 seconds of running data) 
                    # to establish a real baseline before we start checking for anomalies.
                    if len(live_current_buffer) >= 4:
                        np_live = np.array(live_current_buffer)
                        live_rms = np.sqrt(np.mean(np_live**2))
                        
                        # Dynamic comparison matrix
                        if live_rms > RMS_ANOMALY_THRESHOLD:
                            print(f"⚠️ ANOMALY! RMS: {live_rms:.2f}A | Limit: {RMS_ANOMALY_THRESHOLD:.2f}A -> ALARM ACTIVE ", end='\r')
                            if not buzzer_state:
                                ser.write(b"ANOMALY_ON\n")
                                buzzer_state = True
                        else:
                            print(f"✅ Telemetry Nominal | RMS: {live_rms:.2f}A | Limit: {RMS_ANOMALY_THRESHOLD:.2f}A       ", end='\r')
                            if buzzer_state:
                                ser.write(b"ANOMALY_OFF\n")
                                buzzer_state = False
                    else:
                        print(f"Stabilizing tracking filter data stream... ({len(live_current_buffer)}/4)", end='\r')
                        
                else:
                    # Outside target speed -> reset and suppress alarm triggers immediately
                    print(f"Monitoring Standby: Speed is {duty:.1f}% (Bring dial to 80%)                  ", end='\r')
                    if buzzer_state:
                        ser.write(b"ANOMALY_OFF\n")
                        buzzer_state = False
                    # We clear the buffer when completely outside the speed window 
                    # to prevent stale data spikes from lingering.
                    live_current_buffer.clear() 
                    
except KeyboardInterrupt:
    print("\nTerminating background monitor threads...")
finally:
    ser.write(b"ANOMALY_OFF\n")
    ser.close()
    sock.close()
    print("Session terminated cleanly.")
