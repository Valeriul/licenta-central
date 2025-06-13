#!/bin/bash

# Set the display environment for GUI applications
export DISPLAY=:0
export XAUTHORITY=/home/licenta/.Xauthority
export XDG_RUNTIME_DIR=/run/user/$(id -u)

# Get the Tailscale IP
TAILSCALE_IP=$(tailscale ip -4)

# Construct the WebSocket URL
WS_URL="ws://$TAILSCALE_IP:5002/ws"

# Encode the WebSocket URL in Base64 (URL-safe format)
BASE64_WS_URL=$(echo -n "$WS_URL" | base64 | tr -d '=' | tr '/+' '_-')

echo $(echo -n "$WS_URL" | base64 | tr -d '=' | tr '/+' '_-');

# Open Chromium in kiosk mode with the modified URL
chromium-browser --kiosk --noerrdialogs --disable-gpu --disable-software-rasterizer --disable-infobars --incognito "https://licenta.stefandanieluta.ro/control-panel?uuid=$BASE64_WS_URL"
