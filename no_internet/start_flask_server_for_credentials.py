from flask import Flask, render_template_string, request
import subprocess
import os

app = Flask(__name__)

# HTML Template for Wi-Fi configuration page
wifi_page = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wi-Fi Configuration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f4f4f9;
        }
        .container {
            max-width: 400px;
            margin: 0 auto;
            background: #fff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        h2 {
            text-align: center;
        }
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
        }
        select, input, button {
            width: 100%;
            padding: 10px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
        }
        button {
            background: #007BFF;
            color: #fff;
            border: none;
            cursor: pointer;
        }
        button:hover {
            background: #0056b3;
        }
    </style>
</head>
<body>
    <div class="container">
        <h2>Wi-Fi Configuration</h2>
        <form method="POST">
            <label for="ssid">Available Networks:</label>
            <select id="ssid" name="ssid" required>
                {% for ssid in ssids %}
                <option value="{{ ssid }}">{{ ssid }}</option>
                {% endfor %}
            </select>
            <label for="password">Password:</label>
            <input type="password" id="password" name="password" placeholder="Enter Password" required>
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>
"""

def scan_wifi():
    """Scans for available Wi-Fi networks using iwlist and returns a list of SSIDs."""
    try:
        result = subprocess.run(
            ["sudo", "iwlist", "wlan0", "scan"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        output = result.stdout
        ssids = set()
        for line in output.split("\n"):
            line = line.strip()
            if "ESSID:" in line:
                ssid = line.split("ESSID:")[1].strip().strip('"')
                if ssid:
                    ssids.add(ssid)
        return sorted(ssids)
    except Exception as e:
        print(f"Error scanning Wi-Fi: {e}")
        return []

def connect_to_wifi(ssid, password):
    """Connect to a Wi-Fi network using a helper script."""
    try:
        result = subprocess.run(
            ["sudo", "./connect_wifi.sh", ssid, password],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except Exception as e:
        return False, str(e)

@app.route("/", methods=["GET", "POST"])
def wifi_config():
    ssids = scan_wifi()
    if request.method == "POST":
        ssid = request.form["ssid"]
        password = request.form["password"]

        success, message = connect_to_wifi(ssid, password)
        if success:
            return f"<h2>Successfully connected to {ssid}. Rebooting...</h2>"
        else:
            return f"<h2>Failed to connect to {ssid}: {message}</h2>"

    return render_template_string(wifi_page, ssids=ssids)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
