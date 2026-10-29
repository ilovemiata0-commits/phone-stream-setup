from flask import Flask, render_template, redirect, url_for, jsonify
import os
import re
import subprocess

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))

def clean_ip(raw_ip):
    match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+)', raw_ip)
    if match:
        return match.group(1)
    match_ip = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', raw_ip)
    if match_ip:
        return match_ip.group(1) + ":5555"
    return raw_ip

def get_phone_info():
    phones = {}
    for i in range(1, 5):
        ip_file = os.path.expanduser(f"~/.phone{i}_ip")
        serial_file = os.path.expanduser(f"~/.phone{i}_serial")
        
        ip = "Not Synced"
        if os.path.exists(ip_file):
            with open(ip_file, "r") as f:
                ip = clean_ip(f.read().strip())
        
        connected = (ip != "Not Synced")
        
        battery = "--"
        temp = "--"
        charging = "Offline"
        
        if connected and os.path.exists(serial_file):
            try:
                with open(serial_file, "r") as sf:
                    serial = sf.read().strip()
                
                target = ip if ip != "Not Synced" else serial
                
                raw_battery = subprocess.run(
                    ["adb", "-s", target, "shell", "dumpsys", "battery"], 
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=1, text=True
                ).stdout
                
                if raw_battery:
                    level_match = re.search(r'level:\s*(\d+)', raw_battery)
                    temp_match = re.search(r'temperature:\s*(\d+)', raw_battery)
                    
                    if level_match:
                        battery = level_match.group(1) + "%"
                    if temp_match:
                        t_val = int(temp_match.group(1))
                        temp = f"{t_val // 10}.{t_val % 10}°C"
                        
                    if "Powered: true" in raw_battery or "plugged: 1" in raw_battery or "plugged: 2" in raw_battery or "status: 2" in raw_battery:
                        if "plugged: 1" in raw_battery:
                            charging = "Charging (AC)"
                        elif "plugged: 2" in raw_battery:
                            charging = "Charging (USB)"
                        else:
                            charging = "Charging"
                    elif "status: 5" in raw_battery:
                        charging = "Full"
                    else:
                        charging = "Unplugged"
            except Exception:
                pass
            
        phones[i] = {
            "ip": ip,
            "status": "Online" if connected else "Offline",
            "battery": battery,
            "temp": temp,
            "charging": charging
        }
    return phones

@app.route('/')
def index():
    phones = get_phone_info()
    return render_template('index.html', phones=phones)

@app.route('/api/status')
def api_status():
    return jsonify(get_phone_info())

@app.route('/stream/<int:phone_id>/<cam_type>')
def stream(phone_id, cam_type):
    phones = get_phone_info()
    phone_data = phones.get(phone_id)
    if phone_data and phone_data["status"] == "Online":
        ip = phone_data["ip"]
        env = os.environ.copy()
        env["DISPLAY"] = ":0"
        
        if cam_type == "rear":
            camera_id = "0"
            capture_orientation = "90"
            cam_name = "Rear Camera"
        else:
            camera_id = "1"
            capture_orientation = "270"
            cam_name = "Front Camera"
        
        window_title = f"Phone {phone_id} - {cam_name}"
        
        cmd = [
            "scrcpy", 
            "-s", ip, 
            "--window-title", window_title,
            "--video-source=camera", 
            f"--camera-id={camera_id}",
            "--max-size=720",          
            "--video-bit-rate=2M",     
            "--max-fps=30",            
            f"--capture-orientation={capture_orientation}",
            "--stay-awake"
        ]
        
        subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
    return redirect(url_for('index'))

@app.route('/flashlight/<int:phone_id>')
def flashlight(phone_id):
    phones = get_phone_info()
    phone_data = phones.get(phone_id)
    if phone_data and phone_data["status"] == "Online":
        ip = phone_data["ip"]
        try:
            # 1. Wake up the screen and dismiss keyguard
            subprocess.run(["adb", "-s", ip, "shell", "input", "keyevent", "224"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["adb", "-s", ip, "shell", "wm", "dismiss-keyguard"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 2. Open notification shade to expose quick settings toggles
            subprocess.run(["adb", "-s", ip, "shell", "cmd", "statusbar", "expand-notifications"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # 3. Alternatively, send a broadcast intent that some OEMs support for torch toggle
            subprocess.run(["adb", "-s", ip, "shell", "am", "broadcast", "-a", "android.intent.action.FLASHLIGHT_TOGGLE"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    return redirect(url_for('index'))

@app.route('/stream-all')
def stream_all():
    phones = get_phone_info()
    env = os.environ.copy()
    env["DISPLAY"] = ":0"
    
    for phone_id, data in phones.items():
        if data["status"] == "Online":
            ip = data["ip"]
            window_title = f"Phone {phone_id} - Rear Camera"
            cmd = [
                "scrcpy", 
                "-s", ip, 
                "--window-title", window_title,
                "--video-source=camera", 
                "--camera-id=0",           
                "--max-size=720",          
                "--video-bit-rate=2M",     
                "--max-fps=30",            
                "--capture-orientation=90", 
                "--stay-awake"
            ]
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
