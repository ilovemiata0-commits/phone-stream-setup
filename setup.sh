#!/bin/bash

echo "==================================================="
echo "   SETTING UP PHONE STREAM SECURITY SYSTEM        "
echo "==================================================="

# 1. Update system package repositories
sudo apt update

# 2. Install core dependencies
sudo apt install -y adb curl python3 python3-pip python3-flask bc openssh-server git

# 3. Check and install scrcpy automatically
if ! command -v scrcpy &> /dev/null; then
    echo "Installing scrcpy..."
    # Try apt installation first
    sudo apt install -y scrcpy 2>/dev/null || {
        echo "Apt package missing, compiling/installing scrcpy dependencies..."
        sudo apt install -y ffmpeg libsdl2-2.0-0 adb wget gcc git pkg-config meson ninja-build \
            libsdl2-dev libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libusb-1.0-0-dev
        
        # Download official scrcpy server prebuilt binary
        sudo wget https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-server-v2.4 -O /usr/local/bin/scrcpy-server
        chmod +x /usr/local/bin/scrcpy-server
    }
fi

# 4. Configure ~/.bashrc shortcuts
cat << 'EOF_BASH' >> ~/.bashrc

alias dashboard='python3 ~/phone-stream-setup/app.py'
alias watchdog='python3 ~/phone-stream-setup/watchdog.py'

# --- SMART USB IP SYNC ---
syncphone() {
    echo "Starting ADB server..."
    adb kill-server
    sudo adb start-server
    
    echo "Checking connected physical USB device..."
    local SERIAL
    SERIAL=$(adb -d get-serialno 2>/dev/null)
    
    if [ -z "$SERIAL" ] || [ "$SERIAL" = "unknown" ]; then
        echo "Error: No phone detected via USB."
        return 1
    fi
    
    echo "Detected Phone Hardware Serial: $SERIAL"
    
    local PHONE_NUM=""
    for i in {1..4}; do
        if [ -f "$HOME/.phone${i}_serial" ] && [ "$(cat "$HOME/.phone${i}_serial")" = "$SERIAL" ]; then
            PHONE_NUM="$i"
            break
        fi
    done
    
    if [ -z "$PHONE_NUM" ]; then
        for i in {1..4}; do
            if [ ! -f "$HOME/.phone${i}_serial" ]; then
                PHONE_NUM="$i"
                echo "$SERIAL" > "$HOME/.phone${i}_serial"
                echo "Registered as Phone $PHONE_NUM!"
                break
            fi
        done
    fi
    
    if [ -z "$PHONE_NUM" ]; then
        echo "Error: All 4 phone slots are occupied."
        return 1
    fi
    
    local IP_FILE="$HOME/.phone${PHONE_NUM}_ip"
    local LABEL="Phone $PHONE_NUM"
    
    PHONE_IP=$(adb -d shell ip -o addr show 2>/dev/null | grep 'inet ' | grep -E '192\.168\.|10\.|172\.' | grep -v '127.0.0.1' | grep -v 'ccmni' | grep -v 'rmnet' | awk '{print $4}' | cut -d/ -f1 | head -n1)
    
    if [ -n "$PHONE_IP" ]; then
        echo "$PHONE_IP:5555" > "$IP_FILE"
        adb -d tcpip 5555
        sleep 2
        adb connect "$PHONE_IP:5555"
        echo "Synced $LABEL to IP ($PHONE_IP:5555)!"
    else
        echo "Error: Could not resolve Wi-Fi IP."
    fi
}

_get_target() {
    local IP_FILE="$1"
    local DEFAULT="$2"
    if [ -f "$IP_FILE" ]; then cat "$IP_FILE"; else echo "$DEFAULT"; fi
}

_check_single_phone() {
    local NAME="$1"
    local TARGET="$2"
    local IP="${TARGET%:*}"
    
    echo "----------------------------------------------------"
    echo "[$NAME Diagnostics] Target: $TARGET"
    if ping -c 1 -w 1 "$IP" >/dev/null 2>&1; then
        echo -e "  ├── Wi-Fi / Network: \e[32mONLINE\e[0m"
    else
        echo -e "  ├── Wi-Fi / Network: \e[31mOFFLINE\e[0m"
        echo "----------------------------------------------------"
        return 1
    fi

    local BATTERY_INFO=$(adb -s "$TARGET" shell dumpsys battery 2>/dev/null)
    if [ -n "$BATTERY_INFO" ]; then
        local LEVEL=$(echo "$BATTERY_INFO" | grep "level:" | awk '{print $2}')
        local STATUS_CODE=$(echo "$BATTERY_INFO" | grep "status:" | awk '{print $2}')
        local TEMP_RAW=$(echo "$BATTERY_INFO" | grep "temperature:" | awk '{print $2}')
        local TEMP_C=$(echo "scale=1; $TEMP_RAW / 10" | bc 2>/dev/null || echo "N/A")
        
        local STATUS="Unknown"
        case "$STATUS_CODE" in
            2) STATUS="Charging ⚡" ;; 3) STATUS="Discharging 🔋" ;;
            4) STATUS="Not Charging" ;; 5) STATUS="Full 🟢" ;;
        esac
        echo "  ├── Battery Level:   ${LEVEL}% ($STATUS)"
        echo "  └── Temperature:   ${TEMP_C}°C"
    fi
    echo "----------------------------------------------------"
}

# --- CAMERA COMMANDS ---
phoneback()  { local T=$(_get_target ~/.phone1_ip 192.168.1.150:5555); _check_single_phone "Phone 1" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=back --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --window-title="Phone 1 (Back)"; }
phonefront() { local T=$(_get_target ~/.phone1_ip 192.168.1.150:5555); _check_single_phone "Phone 1" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=front --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --window-title="Phone 1 (Front)"; }
recback()    { local T=$(_get_target ~/.phone1_ip 192.168.1.150:5555); _check_single_phone "Phone 1" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=back --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --record=phone1_back.mp4; }

phone2back()  { local T=$(_get_target ~/.phone2_ip 192.168.1.221:5555); _check_single_phone "Phone 2" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=back --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --window-title="Phone 2 (Back)"; }
phone3back()  { local T=$(_get_target ~/.phone3_ip 192.168.1.222:5555); _check_single_phone "Phone 3" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=back --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --window-title="Phone 3 (Back)"; }
phone4back()  { local T=$(_get_target ~/.phone4_ip 192.168.1.223:5555); _check_single_phone "Phone 4" "$T"; scrcpy -s "$T" --video-source=camera --camera-facing=back --orientation=90 -m1024 -b2M --max-fps=30 --no-audio --window-title="Phone 4 (Back)"; }

# --- MULTI-FEED WATCHALL ---
watchall() {
    echo "==================================================="
    echo "      RUNNING PRE-FLIGHT SYSTEM HEALTH CHECK       "
    echo "==================================================="
    local P1=$(_get_target ~/.phone1_ip 192.168.1.150:5555)
    local P2=$(_get_target ~/.phone2_ip 192.168.1.221:5555)
    local P3=$(_get_target ~/.phone3_ip 192.168.1.222:5555)
    local P4=$(_get_target ~/.phone4_ip 192.168.1.223:5555)
    
    _check_single_phone "Phone 1" "$P1"
    _check_single_phone "Phone 2" "$P2"
    _check_single_phone "Phone 3" "$P3"
    _check_single_phone "Phone 4" "$P4"
    
    scrcpy -s "$P1" --video-source=camera --camera-facing=back --orientation=90 -m512 -b1M --max-fps=30 --no-audio --window-title="Phone 1 (Security)" &
    scrcpy -s "$P2" --video-source=camera --camera-facing=back --orientation=90 -m512 -b1M --max-fps=30 --no-audio --window-title="Phone 2 (Security)" &
    scrcpy -s "$P3" --video-source=camera --camera-facing=back --orientation=90 -m512 -b1M --max-fps=30 --no-audio --window-title="Phone 3 (Security)" &
    scrcpy -s "$P4" --video-source=camera --camera-facing=back --orientation=90 -m512 -b1M --max-fps=30 --no-audio --window-title="Phone 4 (Security)" &
}

EOF_BASH

echo "Setup complete!"
