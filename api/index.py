import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PHHC_API_BASE = "https://livedb9010.digitalls.in/cis_filing/public"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://new.phhc.gov.in",
    "Referer": "https://new.phhc.gov.in/",
}

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "MatterTracker Case Lookup API"})

@app.route("/debug", methods=["GET"])
def debug():
    """Returns raw PHHC response so we can see exact field names."""
    case_type = request.args.get("type", "CRM-M")
    case_no   = request.args.get("no", "22")
    case_year = request.args.get("year", "2026")

    results = {}

    # Call 1: getCase
    try:
        r = requests.get(f"{PHHC_API_BASE}/getCase",
                        params={"case_no": case_no, "case_type": case_type, "case_year": case_year},
                        headers=HEADERS, timeout=15)
        results["getCase_status"] = r.status_code
        results["getCase_raw"] = r.json()
    except Exception as e:
        results["getCase_error"] = str(e)

    # Call 2: search endpoint
    try:
        r2 = requests.get(f"{PHHC_API_BASE}/search",
                         params={"case_no": case_no, "case_type": case_type, "case_year": case_year},
                         headers=HEADERS, timeout=15)
        results["search_status"] = r2.status_code
        results["search_raw"] = r2.json()
    except Exception as e:
        results["search_error"] = str(e)

    # Call 3: getCaseStatus
    try:
        r3 = requests.get(f"{PHHC_API_BASE}/getCaseStatus",
                         params={"case_no": case_no, "case_type": case_type, "case_year": case_year},
                         headers=HEADERS, timeout=15)
        results["getCaseStatus_status"] = r3.status_code
        try:
            results["getCaseStatus_raw"] = r3.json()
        except:
            results["getCaseStatus_text"] = r3.text[:500]
    except Exception as e:
        results["getCaseStatus_error"] = str(e)

    return jsonify(results)

@app.route("/case", methods=["GET"])
def get_case():
    case_type = request.args.get("type", "").strip().upper()
    case_no   = request.args.get("no",   "").strip()
    case_year = request.args.get("year", "").strip()

    if not case_type or not case_no or not case_year:
        return jsonify({"error": "Missing parameters: type, no, year"}), 400

    try:
        r = requests.get(f"{PHHC_API_BASE}/getCase",
                        params={"case_no": case_no, "case_type": case_type, "case_year": case_year},
                        headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return jsonify({"found": False}), 404

        data = r.json()
        if isinstance(data, list):
            if len(data) == 0:
                return jsonify({"found": False}), 404
            data = data[0]
        if not data:
            return jsonify({"found": False}), 404

        # Return everything so we can see all fields
        data["found"] = True
        return jsonify(data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
