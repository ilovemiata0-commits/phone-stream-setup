import subprocess
from flask import Flask, jsonify, request

app = Flask(__name__)

# Track active stream processes so you can terminate them if needed
active_streams = {}

@app.route("/")
def index():
    return """
    <h2>📷 Android Security Camera Dashboard</h2>
    <p>Status: <b>Online & Ready</b></p>
    <p>Use your dashboard interface or API endpoints to manage streams.</p>
    """

@app.route("/stream/start/<device_ip>", methods=["POST"])
def start_stream(device_ip):
    title = f"Camera - {device_ip}"
    
    # Bash command wrapper that auto-reconnects on crash
    cmd = f"""
    while true; do
        echo "[Camera Watchdog] Connecting to {device_ip}..."
        adb connect {device_ip}:5555
        adb -s {device_ip}:5555 wait-for-device
        
        scrcpy -s {device_ip}:5555 --window-title "{title}" --max-size 1024 --max-fps 30
        
        echo "[Camera Watchdog] Stream for {device_ip} ended or crashed. Reconnecting in 2s..."
        sleep 2
    done
    """
    
    # Launch as a non-blocking background process
    process = subprocess.Popen(cmd, shell=True, executable="/bin/bash")
    active_streams[device_ip] = process
    
    return jsonify({"status": "success", "message": f"Auto-reconnecting stream started for {device_ip}"})

@app.route("/stream/stop/<device_ip>", methods=["POST"])
def stop_stream(device_ip):
    if device_ip in active_streams:
        active_streams[device_ip].terminate()
        del active_streams[device_ip]
        subprocess.run(["pkill", "-f", f"-s {device_ip}:5555"])
        return jsonify({"status": "success", "message": f"Stopped stream for {device_ip}"})
    
    return jsonify({"status": "error", "message": "Stream not found"}), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
