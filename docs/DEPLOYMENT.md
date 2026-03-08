# Raspberry Pi Deployment Guide

## Hardware Requirements

- Raspberry Pi 4 Model B (4 GB RAM recommended)
- MicroSD card ≥ 32 GB (Class 10 / A2)
- IP CCTV camera with RTSP stream
- Network connection (Ethernet recommended)
- 5V / 3A USB-C power supply

## 1. OS Installation

1. Download **Raspberry Pi OS 64-bit Lite** from <https://www.raspberrypi.com/software/>.
2. Flash to SD card with Raspberry Pi Imager.
3. Enable SSH and configure Wi-Fi in the Imager settings.

## 2. Network Configuration (Static IP)

Edit `/etc/dhcpcd.conf`:

```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8
```

## 3. Clone and Install

```bash
cd /opt
sudo git clone https://github.com/LBJayasundara/atm-area-surveillance-edge-ai.git
sudo chown -R pi:pi atm-area-surveillance-edge-ai
cd atm-area-surveillance-edge-ai
bash scripts/install.sh
```

## 4. Camera Setup

Edit `config/config.yaml`:

```yaml
camera:
  rtsp_url: "rtsp://admin:password@192.168.1.50:554/stream"
```

Test the stream:
```bash
ffprobe rtsp://admin:password@192.168.1.50:554/stream
```

## 5. Service Management

```bash
# Start
sudo systemctl start atm-surveillance

# Check status
sudo systemctl status atm-surveillance

# View logs
journalctl -u atm-surveillance -f

# Stop
sudo systemctl stop atm-surveillance
```

## 6. Performance Tuning

- Set `performance.target_fps: 5` for lighter load
- Use `model.device: cpu` (GPU not available on Pi 4)
- Ensure swap is enabled (`sudo dphys-swapfile setup`)

## 7. Security

- Change `api.auth_token` in `config/config.yaml`
- Restrict API port with `ufw`:
  ```bash
  sudo ufw allow from 192.168.1.0/24 to any port 5000
  ```
- Use nginx reverse proxy (see `deployment/nginx.conf`)
