import tkinter as tk
from PIL import Image, ImageTk, ImageSequence
import threading
import subprocess
import time
import qrcode

import subprocess
import time

def wait_for_hotspot():
    """Wait indefinitely until 'HotSpot' appears in the list of available connections."""
    print("Waiting for 'HotSpot' to appear in available connections...")
    while True:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        connections = result.stdout.splitlines()
        if "HotSpot" in connections:
            print("'HotSpot' is now available.")
            return True

def start_hotspot():
    """Start the Wi-Fi hotspot."""
    try:
        print("Starting HotSpot...")
        result = subprocess.run(
            ["sudo", "nmcli", "connection", "up", "HotSpot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Failed to start HotSpot: {result.stderr}")
            return False

        print("HotSpot started successfully.")
        return True
    except Exception as e:
        print(f"Error starting HotSpot: {e}")
        return False

def start_flask_server():
    """Start the Flask server."""
    try:
        subprocess.run(["python3", "./start_flask_server_for_credentials.py"])
    except Exception as e:
        print(f"Error starting Flask server: {e}")

def get_ip_address():
    """Get the local IP address of wlan0 using nmcli without the subnet mask."""
    try:
        result = subprocess.run(
            ["nmcli", "device", "show", "wlan0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = result.stdout
        for line in output.split("\n"):
            if "IP4.ADDRESS" in line:
                ip_with_subnet = line.split(":")[1].strip()
                return ip_with_subnet.split("/")[0]
        return "IP address not found"
    except Exception as e:
        return f"Error: {str(e)}"

def generate_qr_code(url):
    """Generate a QR code image from the provided URL and return a Tkinter PhotoImage."""
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return ImageTk.PhotoImage(img)

def display_message():
    """Create a fullscreen tkinter window displaying instructions, a loading animation, and a QR code."""
    root = tk.Tk()
    root.title("Remote Access Info")
    root.attributes("-fullscreen", True)
    root.configure(background="black")

    # Create a frame to hold the dynamic content (instructions and QR code)
    content_frame = tk.Frame(root, bg="black")
    content_frame.pack(expand=True)

    # Label for the loading animation (initially visible)
    loading_label = tk.Label(content_frame, bg="black")
    loading_label.pack(side=tk.TOP, anchor="center")

    # Label for the instruction message (initially empty)
    instruction_label = tk.Label(content_frame, text="", font=("Arial", 18), fg="white", bg="black")
    instruction_label.pack(side=tk.TOP, anchor="center")

    # Load the loading GIF frames
    gif_frames = []
    try:
        gif = Image.open("loading.gif")  # Replace with your GIF file path
        for frame in ImageSequence.Iterator(gif):
            frame_image = ImageTk.PhotoImage(frame.copy().convert("RGBA"))
            gif_frames.append(frame_image)
    except Exception as e:
        print("Error loading GIF:", e)

    def play_gif():
        """Animate the loading GIF."""
        if gif_frames:
            frame = gif_frames[play_gif.current_frame]
            play_gif.current_frame = (play_gif.current_frame + 1) % len(gif_frames)
            loading_label.configure(image=frame)
        root.after(100, play_gif)
    play_gif.current_frame = 0

    def update_display_with_ip():
        """Start services, get the IP address, update instructions, and display a QR code."""
        print("Starting Hotspot...")
        wait_for_hotspot()
        hotspot_started = start_hotspot()

        print("Starting Flask server...")
        threading.Thread(target=start_flask_server, daemon=True).start()

        time.sleep(5)  # Allow time for initialization

        ip_address = get_ip_address()
        port = 8080
        url = f"http://{ip_address}:{port}"

        message = (
            "Please connect to the \"Input Wifi Here\" hotspot.\n"
            f"Then open your browser and navigate to:\n\n{url}\n\n"
            " or scand the QR Code to input your Wi-Fi credentials.\n"
        )
        # Remove the loading animation and update the instructions
        loading_label.pack_forget()
        instruction_label.config(text=message)

        # Generate and display the QR code directly below the instruction text
        qr_img = generate_qr_code(url)
        qr_label = tk.Label(content_frame, image=qr_img, bg="black")
        qr_label.image = qr_img  # Prevent garbage collection
        qr_label.pack(side=tk.TOP, anchor="center")
    
    play_gif()
    threading.Thread(target=update_display_with_ip, daemon=True).start()

    root.mainloop()

if __name__ == "__main__":
    display_message()
