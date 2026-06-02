import socket
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Networking Setup ---
UDP_IP = "127.0.0.1"  # Listen locally
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(0.01) # Low timeout prevents window from hanging

print(f"[GRAPHIC ENGINE] Listening for data streams on Port {UDP_PORT}...")

# Data lists for dynamic plotting arrays
time_indices = []
current_history = []
power_history = []
max_data_points = 50  # Number of visible points moving across the screen display
counter = 0

# Set up the Matplotlib Figure Dual Subplots Layout
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6))
fig.suptitle("CNC Lathe Real-Time Telemetry Dashboard", fontsize=14, fontweight='bold')

# Configure Current Plot
ax1.set_ylabel("Current (Amps)", color="cyan", fontweight='bold')
ax1.tick_params(axis='y', labelcolor="cyan")
ax1.grid(True, linestyle="--", alpha=0.5)
line1, = ax1.plot([], [], color="cyan", linewidth=2, label="Live Current")
ax1.legend(loc="upper left")

# Configure Power Plot
ax2.set_xlabel("Time (Samples Index)", fontweight='bold')
ax2.set_ylabel("Power (Watts)", color="orange", fontweight='bold')
ax2.tick_params(axis='y', labelcolor="orange")
ax2.grid(True, linestyle="--", alpha=0.5)
line2, = ax2.plot([], [], color="orange", linewidth=2, label="Live Power")
ax2.legend(loc="upper left")

plt.tight_layout()

def update_graph(frame):
    global counter
    try:
        # Check network loop packet line strings
        data, addr = sock.recvfrom(1024)
        message = data.decode()
        
        # Parse: "current,power,duty"
        current, power, duty = map(float, message.split(","))
        
        # Append data parameters
        counter += 1
        time_indices.append(counter)
        current_history.append(current)
        power_history.append(power)
        
        # Manage maximum width window display limits
        if len(time_indices) > max_data_points:
            time_indices.pop(0)
            current_history.pop(0)
            power_history.pop(0)
            
        # Dynamically update plot line data streams
        line1.set_data(time_indices, current_history)
        line2.set_data(time_indices, power_history)
        
        # Auto-rescale view frames seamlessly 
        ax1.relim()
        ax1.autoscale_view()
        ax2.relim()
        ax2.autoscale_view()
        
        # Keep horizontal window sliding nicely
        ax1.set_xlim(min(time_indices), max(time_indices))
        ax2.set_xlim(min(time_indices), max(time_indices))
        
    except socket.timeout:
        pass # No data arrived in this fraction of a millisecond frame loop -> keep rendering
        
    return line1, line2

# Initialize smooth background animation sweep loop loops
ani = FuncAnimation(fig, update_graph, interval=50, blit=True, cache_frame_data=False)
plt.show()
