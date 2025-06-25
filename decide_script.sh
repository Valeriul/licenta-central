#!/bin/bash

# Set environment variables for graphical applications
export DISPLAY=:0
export XAUTHORITY=/home/licenta/.Xauthority
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Wait for 10 seconds to ensure the display is up
sleep 30

# Define the base directory (adjust if needed)
BASE_DIR="/home/licenta/boot_scripts"

# Check internet connection once
if ping -c 1 -W 3 8.8.8.8 > /dev/null 2>&1; then
    # Start required services
    sudo systemctl start connect_to_pico.service
    sudo systemctl start nginx.service
    sudo systemctl start raspberryApi.service

    # Run Chromium kiosk mode
    cd "$BASE_DIR/internet/chromium" || { echo "Directory not found: $BASE_DIR/internet/chromium"; exit 1; }
    bash start_chormium.sh
else
    cd "$BASE_DIR/no_internet" || { echo "Directory not found: $BASE_DIR/no_internet"; exit 1; }
    python advertise_adress.py
fi
systemctl list-units --type=service