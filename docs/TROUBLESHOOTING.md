# Troubleshooting Guide

## Camera Connection Issues

**Symptom:** "Failed to open RTSP stream" in logs.

**Checks:**
1. Verify RTSP URL format: `rtsp://user:pass@ip:port/path`
2. Test with VLC: `vlc rtsp://…`
3. Check firewall on camera device
4. Try `cv2.CAP_FFMPEG` (default) vs `cv2.CAP_GSTREAMER`
5. Increase `camera.reconnect_delay` in `config.yaml`

---

## Model Loading Errors

**Symptom:** "Failed to load custom model" in logs.

**Checks:**
1. Ensure model file exists: `ls models/`
2. Verify ultralytics installed: `pip show ultralytics`
3. Check `model.path` in `config/config.yaml`
4. For ONNX: ensure `onnxruntime` is installed

---

## Performance Problems

**Symptom:** FPS < 3, high latency.

**Fixes:**
1. Reduce `performance.target_fps` to 5
2. Lower `camera.width`/`height` to 640×480
3. Use `model.path` with `.onnx` model (faster CPU inference)
4. Enable swap: `sudo dphys-swapfile setup && sudo dphys-swapfile swapon`

---

## API Connectivity (Flutter)

**Symptom:** "Cannot reach API" on dashboard.

**Checks:**
1. Confirm Pi IP address: `hostname -I`
2. Check API is running: `curl http://192.168.1.100:5000/health`
3. Ensure both devices are on the same network
4. Verify auth token matches in app settings and `config.yaml`

---

## Database Errors

**Symptom:** SQLite errors in logs.

**Fix:** Reinitialise database:
```bash
python database/init_db.py --reset
```

---

## Logs

```bash
# Application log
tail -f logs/surveillance.log

# Systemd service
journalctl -u atm-surveillance -f
```
