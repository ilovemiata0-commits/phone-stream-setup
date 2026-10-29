# 📷 Android Security Camera Dashboard

A lightweight, high-performance multi-device Android security camera monitoring system built for ChromeOS and Linux. This platform utilizes `adb` for battery, thermal, and state monitoring paired with `scrcpy` for low-latency hardware-accelerated video streaming, all managed through a responsive Flask web interface.

---

## 🚀 Features

- **Multi-Device Grid Dashboard**: View device connection status, battery levels, operating temperatures, and power states at a glance.
- **Single & Multi-Feed Streaming**: Launch individual device video streams with dedicated window titles or launch all active cameras simultaneously with "Watch All".
- **Persistent ADB Connection**: Reliable device registration over TCP/IP (port 5555) via automated setup scripts.
- **Background Watchdog**: Includes `watchdog.py` monitoring script to maintain device connectivity and system telemetry.

---

## 🛠️ Stack & Dependencies

- **OS Environment**: ChromeOS (Linux container / Debian ARM64 / x86_64)
- **Backend**: Python 3, Flask
- **Device Management**: Android Debug Bridge (`adb`)
- **Video Engine**: `scrcpy` (v3.1)
- **Version Control**: Git & GitHub

---

## 📦 Installation & Setup

### 1. Prerequisites
Ensure `adb` and `python3` are installed on your Linux environment:
```bash
sudo apt update
sudo apt install adb python3 python3-pip -y
