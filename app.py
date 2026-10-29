import subprocess
from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)
active_streams = {}

def get_connected_devices():
    """Dynamically discover active wireless ADB devices (port 5555)"""
    devices = []
    try:
        res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=2)
        lines = res.stdout.splitlines()
        
        ip_list = []
        for line in lines:
            if "\tdevice" in line or " device" in line:
                serial = line.split()[0]
                if ":" in serial or "." in serial:
                    ip = serial.split(":")[0]
                    if ip not in ip_list:
                        ip_list.append(ip)
                        
        for i in range(4):
            slot_num = i + 1
            if i < len(ip_list):
                ip = ip_list[i]
                devices.append({"name": f"Phone {slot_num}", "ip": ip, "connected": True})
            else:
                devices.append({"name": f"Phone {slot_num}", "ip": "Waiting for connection...", "connected": False})
    except Exception:
        for i in range(4):
            devices.append({"name": f"Phone {i+1}", "ip": "Waiting for connection...", "connected": False})
            
    return devices

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
        
        level_val = None
        scale_val = 100
        
        for line in batt_res.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("level:"):
                try:
                    level_val = int(line_str.split(':')[1].strip())
                except:
                    pass
            elif line_str.startswith("scale:"):
                try:
                    scale_val = int(line_str.split(':')[1].strip())
                except:
                    pass
            elif "AC powered: true" in line_str or "USB powered: true" in line_str:
                power = "Plugged In"
            elif line_str.startswith("temperature:"):
                try:
                    t_val = int(line_str.split(':')[1].strip()) / 10.0
                    temp = f"{t_val}°C"
                except:
                    pass
                    
        if level_val is not None and scale_val > 0:
            actual_pct = int((level_val / scale_val) * 100)
            battery = f"{actual_pct}%"
            
        return {"status": "Online", "battery": battery, "temp": temp, "power": power}
    except Exception:
        return {"status": "Offline", "battery": "N/A", "temp": "N/A", "power": "Unknown"}

@app.route("/")
def index():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Multi-Phone Remote Monitoring</title>
        <style>
            body { background-color: #0f172a; color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 40px; }
            h1 { text-align: center; color: #38bdf8; margin-bottom: 20px; }
            .top-bar { text-align: center; margin-bottom: 40px; }
            .btn-all { background-color: #7c3aed; color: white; padding: 12px 24px; border: none; border-radius: 8px; font-weight: bold; font-size: 1rem; cursor: pointer; transition: opacity 0.2s; }
            .btn-all:hover { opacity: 0.9; }
            .grid { display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
            .card { background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; width: 320px; padding: 24px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
            .card-title { color: #38bdf8; font-size: 1.5rem; font-weight: bold; margin-bottom: 20px; border-bottom: 1px solid #334155; padding-bottom: 10px; }
            .row { display: flex; justify-content: space-between; margin-bottom: 12px; font-size: 1rem; }
            .label { color: #94a3b8; }
            .value { font-weight: 600; }
            .value.online { color: #4ade80; }
            .value.offline { color: #f87171; }
            .value.waiting { color: #64748b; font-style: italic; font-size: 0.85rem; }
            .value.battery { color: #fbbf24; }
            .value.temp { color: #fb923c; }
            .value.power { color: #38bdf8; }
            .btn-container { display: flex; gap: 10px; margin-top: 24px; }
            .btn { flex: 1; padding: 10px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; text-align: center; transition: opacity 0.2s; }
            .btn:hover { opacity: 0.9; }
            .btn-rear { background-color: #0284c7; }
            .btn-front { background-color: #0d9488; }
            .btn:disabled { background-color: #334155; color: #64748b; cursor: not-allowed; }
        </style>
    </head>
    <body>
        <h1>Multi-Phone Remote Monitoring</h1>
        <div class="top-bar">
            <button class="btn-all" onclick="startAllRearCams()">📹 Watch All Rear Cams</button>
        </div>
        <div class="grid" id="device-grid">
            <!-- Dynamically populated via JS polling -->
        </div>
        <script>
            function fetchTelemetry() {
                fetch('/api/devices')
                    .then(response => response.json())
                    .then(devices => {
                        const grid = document.getElementById('device-grid');
                        grid.innerHTML = '';
                        devices.forEach(dev => {
                            let statusClass = dev.status === 'Online' ? 'online' : (dev.status === 'Offline' ? 'offline' : 'waiting');
                            let ipDisplay = dev.connected ? dev.ip + ':5555' : dev.ip;
                            
                            let btnHtml = dev.connected ? 
                                `<button class="btn btn-rear" onclick="startStream('${dev.ip}', 'Rear')">Rear Cam</button>
                                 <button class="btn btn-front" onclick="startStream('${dev.ip}', 'Front')">Front Cam</button>` :
                                `<button class="btn" disabled>Waiting...</button>`;

                            let card = `
                            <div class="card">
                                <div class="card-title">${dev.name}</div>
                                <div class="row"><span class="label">Status:</span><span class="value ${statusClass}">${dev.status}</span></div>
                                <div class="row"><span class="label">Target IP:</span><span class="value" style="font-size: 0.9rem;">${ipDisplay}</span></div>
                                <div class="row"><span class="label">Battery:</span><span class="value battery">${dev.battery}</span></div>
                                <div class="row"><span class="label">Temperature:</span><span class="value temp">${dev.temp}</span></div>
                                <div class="row"><span class="label">Power:</span><span class="value power">${dev.power}</span></div>
                                <div class="btn-container">${btnHtml}</div>
                            </div>`;
                            grid.innerHTML += card;
                        });
                    })
                    .catch(err => console.error('Telemetry fetch error:', err));
            }

            function startStream(ip, camType) {
                fetch('/stream/start/' + ip + '/' + camType, { method: 'POST' })
                    .then(response => response.json())
                    .then(data => console.log(data.message))
                    .catch(err => console.error('Error:', err));
            }

            function startAllRearCams() {
                fetch('/stream/start-all-rear', { method: 'POST' })
                    .then(response => response.json())
                    .then(data => console.log(data.message))
                    .catch(err => console.error('Error:', err));
            }

            // Initial load and poll every 10 seconds for live battery/temp/power updates
            fetchTelemetry();
            setInterval(fetchTelemetry, 10000);
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template)

@app.route("/api/devices")
def api_devices():
    discovered_devices = get_connected_devices()
    device_cards = []
    for dev in discovered_devices:
        if dev["connected"]:
            telemetry = get_device_telemetry(dev["ip"])
            device_cards.append({**dev, **telemetry})
        else:
            device_cards.append({
                **dev,
                "status": "Waiting",
                "battery": "N/A",
                "temp": "N/A",
                "power": "N/A"
            })
    return jsonify(device_cards)

@app.route("/stream/start/<device_ip>/<cam_type>", methods=["POST"])
def start_stream(device_ip, cam_type):
    title = f"{cam_type} Cam - {device_ip}"
    if cam_type == "Rear":
        cam_id = "0"
        orientation = "90"
    else:
        cam_id = "1"
        orientation = "270"
        
    subprocess.run(["adb", "connect", f"{device_ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    cmd = [
        "scrcpy",
        "-s", f"{device_ip}:5555",
        "--video-source=camera",
        f"--camera-id={cam_id}",
        f"--window-title={title}",
        "--max-size=1024",
        "--max-fps=30",
        f"--orientation={orientation}"
    ]
    
    process = subprocess.Popen(cmd)
    active_streams[device_ip] = process
    
    return jsonify({"status": "success", "message": f"Started {cam_type} camera stream for {device_ip}"})

@app.route("/stream/start-all-rear", methods=["POST"])
def start_all_rear():
    devices = get_connected_devices()
    launched_count = 0
    for dev in devices:
        if dev["connected"]:
            ip = dev["ip"]
            title = f"Rear Cam - {ip}"
            subprocess.run(["adb", "connect", f"{ip}:5555"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            cmd = [
                "scrcpy",
                "-s", f"{ip}:5555",
                "--video-source=camera",
                "--camera-id=0",
                f"--window-title={title}",
                "--max-size=1024",
                "--max-fps=30",
                "--orientation=90"
            ]
            process = subprocess.Popen(cmd)
            active_streams[ip] = process
            launched_count += 1
            
    return jsonify({"status": "success", "message": f"Launched {launched_count} rear camera streams."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
