#!/bin/bash

SSID="$1"
PASSWORD="$2"

if [ -z "$SSID" ] || [ -z "$PASSWORD" ]; then
    echo "Usage: $0 <SSID> <PASSWORD>"
    exit 1
fi

# Check if the network already exists
if nmcli connection show | grep -q "$SSID"; then
    echo "Connection for SSID $SSID already exists. Attempting to connect..."
    nmcli connection up "$SSID"
else
    # Add and save the new connection
    echo "Adding new connection for SSID $SSID..."
    nmcli dev wifi connect "$SSID" password "$PASSWORD" --ask
fi

# Check if the connection was successful
if nmcli connection show --active | grep -q "$SSID"; then
    echo "Successfully connected to $SSID. Rebooting the system..."
    sudo reboot
else
    echo "Failed to connect to $SSID. Please check the SSID and password."
    exit 1
fi
