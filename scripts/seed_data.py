# scripts/seed_data.py
import gspread
from datetime import datetime
import json
from pathlib import Path

# config - adjust if needed
CRED_FILE = "data/credentials.json"
SHEET_ID = "1KA88moq8f59KCK2mjl_gsuBioC0aPzvZf5_RyraC4E"
DEVICES_SHEET = "devices"
TELEMETRY_SHEET = "bin_telemetry"

# sample device & telemetry
device = {
    "id": "11111111-1111-1111-1111-111111111111",
    "device_name": "Bin-A1",
    "device_type": "bin",
    "model": "ESP32-LoRa",
    "lat": 12.9715987,
    "lon": 77.594566,
    "installed_on": datetime.utcnow().isoformat() + "Z",
    "firmware_version": "1.0",
    "status": "active",
    "notes": "Seeded device"
}

telemetry = {
    "device_id": device["id"],
    "timestamp": datetime.utcnow().isoformat() + "Z",
    "fill_pct": 45.2,
    "battery_pct": 95.0,
    "raw_payload": {"rssi": -65}
}

def main():
    # ensure creds exist
    cred_path = Path(CRED_FILE)
    if not cred_path.exists():
        print("Credentials file not found:", CRED_FILE)
        return

    client = gspread.service_account(filename=CRED_FILE)
    sh = client.open_by_key(SHEET_ID)

    # Append device (if not already present)
    try:
        ws = sh.worksheet(DEVICES_SHEET)
    except Exception as e:
        print("Devices sheet not found:", e)
        return

    records = ws.get_all_records()
    if not any(str(r.get("id")) == device["id"] for r in records):
        # create header order same as earlier: id,device_name,device_type,model,lat,lon,installed_on,firmware_version,status,notes
        row = [
            device["id"],
            device["device_name"],
            device["device_type"],
            device["model"],
            device["lat"],
            device["lon"],
            device["installed_on"],
            device["firmware_version"],
            device["status"],
            device["notes"]
        ]
        ws.append_row(row)
        print("Device appended.")
    else:
        print("Device already exists in sheet.")

    # Append telemetry (create telemetry sheet row)
    try:
        t_ws = sh.worksheet(TELEMETRY_SHEET)
    except Exception:
        # Attempt to create sheet if missing
        t_ws = sh.add_worksheet(title=TELEMETRY_SHEET, rows="1000", cols="20")
        # Add header row consistent with earlier: id,device_id,timestamp,fill_pct,battery_pct,raw_payload
        t_ws.append_row(["id","device_id","timestamp","fill_pct","battery_pct","raw_payload"])

    next_id = t_ws.row_count  # simple; we don't need exact IDs
    t_row = [
        next_id,
        telemetry["device_id"],
        telemetry["timestamp"],
        telemetry["fill_pct"],
        telemetry["battery_pct"],
        json.dumps(telemetry["raw_payload"])
    ]
    t_ws.append_row(t_row)
    print("Telemetry appended.")

if __name__ == "__main__":
    main()
