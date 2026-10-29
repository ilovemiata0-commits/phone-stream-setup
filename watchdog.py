import subprocess, time, re, os, urllib.request, json

TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Optional
TELEGRAM_CHAT_ID = "YOUR_CHAT_ID_HERE"      # Optional

MAX_TEMP_C = 40.0        # Overheat safety limit
RESUME_TEMP_C = 35.0     # Cool-down resume point
TARGET_MAX_BATTERY = 85  # Cycle cap to prevent bloat
TARGET_MIN_BATTERY = 40  # Cycle lower bound

def send_telegram_alert(message):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print(f"[ALERT] {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Telegram alert failed: {e}")

def get_target(phone_num):
    ip_file = os.path.expanduser(f"~/.phone{phone_num}_ip")
    if os.path.exists(ip_file):
        with open(ip_file, 'r') as f: return f.read().strip()
    defaults = {1: "192.168.1.150:5555", 2: "192.168.1.221:5555", 3: "192.168.1.222:5555", 4: "192.168.1.223:5555"}
    return defaults.get(phone_num, "192.168.1.150:5555")

def manage_battery_and_thermal(phone_num, target):
    try:
        output = subprocess.check_output(['adb', '-s', target, 'shell', 'dumpsys', 'battery'], timeout=2).decode('utf-8')
        level_match = re.search(r'level:\s*(\d+)', output)
        temp_match = re.search(r'temperature:\s*(\d+)', output)
        if not level_match or not temp_match: return

        level = int(level_match.group(1))
        temp_c = float(temp_match.group(1)) / 10.0

        # Thermal Overheat Guard
        if temp_c >= MAX_TEMP_C:
            subprocess.run(['adb', '-s', target, 'shell', 'dumpsys', 'battery', 'unplug'], stdout=subprocess.DEVNULL)
            send_telegram_alert(f"⚠️ Security Alert: Phone {phone_num} is overheating ({temp_c}°C). Charging paused.")
            return

        if temp_c <= RESUME_TEMP_C:
            subprocess.run(['adb', '-s', target, 'shell', 'dumpsys', 'battery', 'reset'], stdout=subprocess.DEVNULL)

        # Smart preservation charging cycle (40% - 85%)
        if level >= TARGET_MAX_BATTERY:
            subprocess.run(['adb', '-s', target, 'shell', 'dumpsys', 'battery', 'unplug'], stdout=subprocess.DEVNULL)
        elif level <= TARGET_MIN_BATTERY:
            subprocess.run(['adb', '-s', target, 'shell', 'dumpsys', 'battery', 'reset'], stdout=subprocess.DEVNULL)

    except Exception as e:
        pass

def main_loop():
    print("Starting Thermal Guard & Battery Preservation Watchdog...")
    while True:
        for phone_num in range(1, 5):
            manage_battery_and_thermal(phone_num, get_target(phone_num))
        time.sleep(60)

if __name__ == "__main__":
    main_loop()
