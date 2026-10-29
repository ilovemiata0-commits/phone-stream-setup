import subprocess
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
active_streams = {}

def get_device_telemetry(ip):
    try:
        subprocess.run(["adb", "connect", f"{ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        status_res = subprocess.run(["adb", "-s", f"{ip}:5555", "get-state"], capture_output=True, text=True, timeout=2)
        if status_res.returncode != 0 or "device" not in status_res.stdout:
            return {"status": "Offline", "battery": "N/A", "temp": "N/A", "power": "Unknown"}
        
        batt_res = subprocess.run(["adb", "-s", f"{ip}:5555", "shell", "dumpsys battery"], capture_output=True, text=True, timeout=2)
        battery = "N/A"
        power = "Unplugged"
        temp = "28.0°C"
        for line in batt_res.stdout.splitlines():
            if "level:" in line:
                battery = f"{line.split(':')[1].strip()}%"
            if "AC powered: true" in line or "USB powered: true" in line:
                power = "Plugged In"
            if "temperature:" in line:
                try:
                    t_val = int(line.split(':')[1].strip()) / 10.0
                    temp = f"{t_val}°C"
                except:
                    pass
        return {"status": "Online", "battery": battery, "temp": temp, "power": power}
    except Exception:
        return {"status": "Offline", "battery": "N/A", "temp": "N/A", "power": "Unknown"}

DEVICES = [{"name": "Phone 2", "ip": "192.168.1.221"}]

@app.route("/")
def index():
    device_cards = []
    for dev in DEVICES:
        telemetry = get_device_telemetry(dev["ip"])
        device_cards.append({**dev, **telemetry})
        
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Multi-Phone Remote Monitoring</title>
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 40px; }
            h1 { text-align: center; color: #38bdf8; margin-bottom: 40px; }
            .grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
            .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; width: 320px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
            .card-title { color: #38bdf8; font-size: 1.5rem; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
            .row { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 1rem; }
            .label { color: #94a3b8; }
            .value { font-weight: 600; }
            .value.online { color: #4ade80; }
            .value.offline { color: #f87171; }
            .value.battery { color: #fbbf24; }
            .value.temp { color: #fb923c; }
            .value.power { color: #38bdf8; }
            .btn-container { display: flex; gap: 10px; margin-top: 24px; }
            .btn { flex: 1; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; text-align: center; transition: opacity 0.2s; }
            .btn:hover { opacity: 0.9; }
            .btn-rear { background-color: #0284c7; }
            .btn-front { background-color: #0d9488; }
        </style>
    </head>
    <body>
        <h1>Multi-Phone Remote Monitoring</h1>
        <div class="grid">
            {% for dev in devices %}
            <div class="card">
                <div class="card-title">{{ dev.name }}</div>
                <div class="row"><span class="label">Status:</span><span class="value {{ 'online' if dev.status == 'Online' else 'offline' }}">{{ dev.status }}</span></div>
                <div class="row"><span class="label">Target IP:</span><span class="value" style="font-size: 0.9rem;">{{ dev.ip }}:5555</span></div>
                <div class="row"><span class="label">Battery:</span><span class="value battery">{{ dev.battery }}</span></div>
                <div class="row"><span class="label">Temperature:</span><span class="value temp">{{ dev.temp }}</span></div>
                <div class="row"><span class="label">Power:</span><span class="value power">{{ dev.power }}</span></div>
                <div class="btn-container">
                    <button class="btn btn-rear" onclick="startStream('{{ dev.ip }}', 'Rear')">Rear Cam</button>
                    <button class="btn btn-front" onclick="startStream('{{ dev.ip }}', 'Front')">Front Cam</button>
                </div>
            </div>
            {% endfor %}
        </div>
        <script>
            function startStream(ip, camType) {
                fetch('/stream/start/' + ip + '/' + camType, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => alert(data.message))
                    .catch(err => console.error('Error:', err));
            }
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template, devices=device_cards)

@app.route("/stream/start/<device_ip>/<cam_type>", methods=["POST"])
def start_stream(device_ip, cam_type):
    title = f"{cam_type} Cam - {device_ip}"
    cmd = f"""
    while true; do
        echo "[Camera Watchdog] Connecting to {device_ip}..."
        adb connect {device_ip}:5555
        adb -s {device_ip}:5555 wait-for-device
        scrcpy -s {device_ip}:5555 --window-title "{title}" --max-size 1024 --max-fps 30
        echo "[Camera Watchdog] Stream ended. Reconnecting in 2s..."
        sleep 2
    done
    """
    process = subprocess.Popen(cmd, shell=True, executable="/bin/bash")
    active_streams[device_ip] = process
    return jsonify({"status": "success", "message": f"Started {cam_type} stream with auto-recovery for {device_ip}"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
