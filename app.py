# app.py
from flask import Flask, render_template, jsonify, request
import json
import os
import gspread
from pathlib import Path

app = Flask(__name__)

# Config (use env vars in production)
SHEET_ID = os.getenv("SHEET_ID", "https://docs.google.com/spreadsheets/d/1KA88moq8f59KCK2mjl_gsuBiOcOa2PcvZf5_Ryrac4E/edit?gid=0#gid=0")
SHEET_NAME_BINS = os.getenv("SHEET_NAME_BINS", "devices")
SHEET_NAME_TASKS = os.getenv("SHEET_NAME_TASKS", "tasks")
GOOGLE_CREDS_FILE = os.getenv("GOOGLE_CREDS_FILE", "data/credentials.json")  # Service account JSON

# Local fallback data files
BINS_FALLBACK = Path("data/bins_data.json")
LIGHTS_FALLBACK = Path("data/lights_data.json")

# Lazy gspread client initializer
_gspread_client = None

def get_gspread_client():
    global _gspread_client
    if _gspread_client:
        return _gspread_client

    creds_path = Path(GOOGLE_CREDS_FILE)
    if not creds_path.exists():
        # Don't crash — keep client None and allow fallback to local JSON
        app.logger.warning(f"Google creds not found at {creds_path}; using local fallback data.")
        return None

    try:
        # Use gspread.service_account (uses google-auth)
        _gspread_client = gspread.service_account(filename=str(creds_path))
        return _gspread_client
    except Exception as exc:
        app.logger.exception("Failed to create gspread client:")
        _gspread_client = None
        return None

def get_sheet_data(sheet_name):
    """Fetch all rows from a Google Sheet as list of dicts. Returns None on failure."""
    client = get_gspread_client()
    if not client:
        return None
    try:
        sh = client.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(sheet_name)
        records = worksheet.get_all_records()
        return records
    except Exception as exc:
        app.logger.exception(f"Error reading sheet '{sheet_name}':")
        return None

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/bins")
def bins_page():
    bins_data = get_sheet_data(SHEET_NAME_BINS)
    if bins_data is None:
        # Fallback to local file if Google Sheets unavailable
        if BINS_FALLBACK.exists():
            with open(BINS_FALLBACK, "r", encoding="utf-8") as f:
                bins_data = json.load(f)
        else:
            bins_data = []
    return render_template("bins.html", bins=bins_data)

@app.route("/api/bins")
def bins_api():
    data = get_sheet_data(SHEET_NAME_BINS)
    if data is None:
        return jsonify({"error": "Could not load Google Sheet (falling back to local file)."}), 503
    return jsonify({"data": data})

@app.route("/lights")
def lights_page():
    # For now lights are local JSON fallback
    if LIGHTS_FALLBACK.exists():
        with open(LIGHTS_FALLBACK, "r", encoding="utf-8") as f:
            lights_data = json.load(f)
    else:
        lights_data = []
    return render_template("lights.html", lights=lights_data)

@app.route("/api/lights")
def lights_api():
    if LIGHTS_FALLBACK.exists():
        with open(LIGHTS_FALLBACK, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []
    return jsonify({"data": data})

@app.route("/api/telemetry", methods=["POST"])
def receive_telemetry():
    """Receive data from virtual sensors (Smart Bin / Smart Light)"""
    try:
        data = request.get_json()
        print("Telemetry received:", data)

        # Example: save to file or print (you can extend this to Google Sheets)
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        with open("data/telemetry_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")

        return jsonify({"status": "success", "message": "Telemetry received"}), 200
    except Exception as e:
        print("Error:", e)
        return jsonify({"status": "error", "message": str(e)}), 400

@app.route("/api/evidence/upload", methods=["POST"])
def upload_evidence():
    """Receive image evidence (illegal dumping etc.)"""
    try:
        device_id = request.form.get("device_id")
        timestamp = request.form.get("timestamp")
        file = request.files.get("file")
        if not file:
            return jsonify({"status": "error", "message": "No file provided"}), 400

        # sanitize filename components
        safe_device = (device_id or "unknown").replace(" ", "_")
        safe_ts = (timestamp or str(int(time.time()))).replace(":", "-")

        filename = f"evidence_{safe_device}_{safe_ts}.jpg"
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)
        file.save(filepath)
        print(f"Evidence received from {device_id} -> {filename}")
        return jsonify({"status": "success", "file_saved": filename}), 200
    except Exception as e:
        print("Error uploading evidence:", e)
        return jsonify({"status": "error", "message": str(e)}), 400

if __name__ == "__main__":
    # For local development only. In production use gunicorn as configured on Render.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
