import tkinter as tk
from PIL import Image, ImageTk
import threading
import subprocess
import time


def start_hotspot():
    """Start the Wi-Fi hotspot."""
    try:
        result = subprocess.run(
            ["nmcli", "connection", "up", "HotSpot"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            print(f"Failed to start Hotspot: {result.stderr}")
            return False
        print("Hotspot started successfully.")
        return True
    except Exception as e:
        print(f"Error starting Hotspot: {e}")
        return False


def start_flask_server():
    """Start the Flask server."""
    try:
        subprocess.run(["python3", "./start_flask_server_for_credentials.py"])
    except Exception as e:
        print(f"Error starting Flask server: {e}")


def get_ip_address():
    """Get the local IP address of wlan0 using nmcli."""
    try:
        # Run the nmcli command to get the IP address
        result = subprocess.run(
            ["nmcli", "device", "show", "wlan0"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = result.stdout

        # Extract the IP address from the command output
        for line in output.split("\n"):
            if "IP4.ADDRESS" in line:
                return line.split(":")[1].strip()  # Extract and clean up the IP address
        return "IP address not found"
    except Exception as e:
        return f"Error: {str(e)}"


def display_message():
    """Create a fullscreen tkinter window displaying the message."""

    def update_display_with_ip():
        """Update the display after getting the IP address."""
        # Start the Wi-Fi hotspot
        print("Starting Hotspot...")
        hotspot_started = start_hotspot()

        if not hotspot_started:
            message = "Failed to start hotspot. Please check the configuration."
            label.config(text=message)
            return

        # Start the Flask server in a separate thread
        print("Starting Flask server...")
        threading.Thread(target=start_flask_server, daemon=True).start()

        # Simulate waiting for the IP address
        time.sleep(5)  # Allow time for the Flask server to initialize

        # Get the IP address
        ip_address = get_ip_address()
        port = 8080

        # Update the UI with the address
        message = f"Access this device at:\nhttp://{ip_address}:{port}"
        loading_label.pack_forget()  # Remove the loading animation
        label.config(text=message)  # Update label text

    def play_gif():
        """Play the loading GIF."""
        frame = gif_frames[play_gif.current_frame]
        play_gif.current_frame = (play_gif.current_frame + 1) % len(gif_frames)
        loading_label.configure(image=frame)
        root.after(100, play_gif)  # Adjust the delay (ms) between frames as needed

    # Initialize GIF playback
    play_gif.current_frame = 0

    # Create the tkinter window
    root = tk.Tk()
    root.title("Remote Access Info")

    # Make the window fullscreen
    root.attributes("-fullscreen", True)
    root.configure(background="black")

    # Load the GIF frames
    gif_frames = []
    gif = Image.open("loading.gif")  # Replace with your GIF file path
    for frame in range(gif.n_frames):
        gif.seek(frame)
        gif_frames.append(ImageTk.PhotoImage(gif))

    # Add a loading animation
    loading_label = tk.Label(root, bg="black")
    loading_label.pack(expand=True)

    # Add a placeholder label for the message
    label = tk.Label(root, text="", font=("Arial", 30), fg="white", bg="black")
    label.pack(expand=True)

    # Start GIF playback
    play_gif()

    # Start a thread to update the display with the IP address
    threading.Thread(target=update_display_with_ip, daemon=True).start()

    # Start the tkinter main loop
    root.mainloop()


if __name__ == "__main__":
    display_message()
