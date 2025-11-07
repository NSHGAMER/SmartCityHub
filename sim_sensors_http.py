#!/usr/bin/env python3
"""
Virtual Bin Simulator (HTTP)
- Posts periodic telemetry to SIM_ENDPOINT (default: http://127.0.0.1:5000/api/telemetry)
- Occasionally triggers an 'illegal_dump' event and uploads a photo to EVIDENCE_ENDPOINT
Config via environment variables:
  SIM_ENDPOINT (HTTP POST target for telemetry)
  EVIDENCE_ENDPOINT (multipart upload target for evidence)
  NUM_DEVICES (how many virtual bins)
  INTERVAL (seconds between posts per device)
  DUMP_PROB (probability per post to simulate illegal dump, 0-1)
"""
import os, time, random, threading, requests, uuid
from datetime import datetime, timezone

SIM_ENDPOINT = os.getenv("SIM_ENDPOINT", "http://127.0.0.1:5000/api/telemetry")
EVIDENCE_ENDPOINT = os.getenv("EVIDENCE_ENDPOINT", "")  # e.g. https://.../api/evidence/upload
NUM_DEVICES = int(os.getenv("NUM_DEVICES", "4"))
INTERVAL = float(os.getenv("INTERVAL", "8"))
DUMP_PROB = float(os.getenv("DUMP_PROB", "0.06"))  # ~6% chance per post
BASE_LAT = float(os.getenv("BASE_LAT", "12.9716"))
BASE_LON = float(os.getenv("BASE_LON", "77.5946"))

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def make_telemetry(device_id, lat, lon, baseline_fill):
    # slow drift up, occasional drop simulated by random choice
    drift = random.uniform(-0.6, 1.2)
    noise = random.gauss(0, 2.0)
    fill = max(0, min(100, baseline_fill + drift + noise))
    if random.random() < 0.01:  # rare emptying event
        fill = max(0, fill - random.uniform(30, 95))
    battery = max(10.0, 100 - random.uniform(0, 0.3))
    status = "Full" if fill > 80 else "Active"
    return {
        "device_id": device_id,
        "timestamp": now_iso(),
        "lat": round(lat,6),
        "lon": round(lon,6),
        "fill_pct": round(fill,2),
        "battery_pct": round(battery,2),
        "rssi": -60 + random.randint(-8,8),
        "status": status
    }

def upload_evidence(device_id, lat, lon, fill_pct):
    """Download a placeholder image and upload as multipart to EVIDENCE_ENDPOINT"""
    if not EVIDENCE_ENDPOINT:
        print(f"[{device_id}] No EVIDENCE_ENDPOINT configured — skipping evidence upload")
        return None
    try:
        # fetch a random placeholder image (small)
        img_resp = requests.get("https://picsum.photos/400/300", timeout=8)
        img_bytes = img_resp.content
        files = {
            "file": ("evidence.jpg", img_bytes, "image/jpeg")
        }
        data = {
            "device_id": device_id,
            "timestamp": now_iso(),
            "lat": lat,
            "lon": lon,
            "fill_pct": fill_pct,
            "event_type": "illegal_dump"
        }
        r = requests.post(EVIDENCE_ENDPOINT, files=files, data=data, timeout=12)
        print(f"[{device_id}] Evidence upload {r.status_code} -> {r.text[:200]}")
        return r
    except Exception as e:
        print(f"[{device_id}] Evidence upload failed: {e}")
        return None

def device_loop(device_id, lat, lon, baseline_fill):
    while True:
        payload = make_telemetry(device_id, lat, lon, baseline_fill)
        try:
            r = requests.post(SIM_ENDPOINT, json=payload, timeout=8)
            print(f"[{device_id}] Telemetry {r.status_code if r is not None else 'ERR'} {payload['fill_pct']}")
        except Exception as e:
            print(f"[{device_id}] Telemetry POST error: {e}")

        # maybe trigger illegal dump event
        if random.random() < DUMP_PROB:
            print(f"[{device_id}] >>> Simulating illegal dump event!")
            upload_evidence(device_id, lat, lon, payload["fill_pct"])

        time.sleep(INTERVAL + random.uniform(-1.5, 1.5))

def spawn(num=NUM_DEVICES):
    print("SIM START", "endpoint=", SIM_ENDPOINT, "evidence=", bool(EVIDENCE_ENDPOINT))
    for i in range(num):
        dev = f"VIRTUAL-BIN-{i+1:03d}"
        lat = BASE_LAT + random.uniform(-0.006, 0.006)
        lon = BASE_LON + random.uniform(-0.006, 0.006)
        baseline = random.uniform(10, 70)
        t = threading.Thread(target=device_loop, args=(dev, lat, lon, baseline), daemon=True)
        t.start()
        print("Started", dev, "pos", round(lat,5), round(lon,5))
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("Simulator stopped.")

if __name__ == "__main__":
    spawn()
