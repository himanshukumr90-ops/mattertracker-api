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

def str_val(v):
    """Safely extract string from a value that might be a dict, int, or string."""
    if v is None:
        return ""
    if isinstance(v, dict):
        # Try common name keys
        return str(v.get("name") or v.get("status_desc") or v.get("desc") or "").strip()
    return str(v).strip()

def fetch_case(case_type, case_no, case_year):
    try:
        # First call: get basic case info
        url = f"{PHHC_API_BASE}/getCase"
        params = {"case_no": str(case_no), "case_type": case_type, "case_year": str(case_year)}
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        print(f"[API] getCase status: {r.status_code}")
        if r.status_code != 200:
            return None

        data = r.json()
        print(f"[API] Raw data: {data}")

        if isinstance(data, list):
            if len(data) == 0:
                return None
            data = data[0]
        if not data:
            return None

        # Get CNR number to fetch full case details
        cnr = str_val(data.get("cnr_no") or data.get("cnrNo") or "")

        # Try to get party details from a second endpoint using CNR
        party_detail = ""
        petitioner = ""
        respondent = ""
        next_date = ""
        advocate = ""

        if cnr:
            try:
                detail_url = f"{PHHC_API_BASE}/getCaseDetailByCNR"
                dr = requests.get(detail_url, params={"cnr_no": cnr}, headers=HEADERS, timeout=15)
                print(f"[API] getCaseDetailByCNR status: {dr.status_code}")
                if dr.status_code == 200:
                    detail = dr.json()
                    print(f"[API] Detail data: {detail}")
                    if isinstance(detail, list) and len(detail) > 0:
                        detail = detail[0]
                    if isinstance(detail, dict):
                        party_detail = str_val(detail.get("party_detail") or detail.get("partyDetail") or "")
                        advocate = str_val(detail.get("advocate_name") or detail.get("advocateName") or "")
                        next_date = str_val(detail.get("next_date") or detail.get("nextDate") or
                                          detail.get("next_hearing_date") or "")
            except Exception as e:
                print(f"[API] Detail fetch error: {e}")

        # Fall back to main data if detail didn't give party info
        if not party_detail:
            party_detail = str_val(data.get("party_detail") or data.get("partyDetail") or
                                   data.get("case_title") or "")

        if not next_date:
            next_date = str_val(data.get("next_date") or data.get("nextDate") or
                               data.get("next_hearing_date") or "")

        if not advocate:
            advocate = str_val(data.get("advocate_name") or data.get("advocateName") or "")

        # Split party detail into petitioner/respondent
        if " Vs " in party_detail:
            parts = party_detail.split(" Vs ", 1)
            petitioner, respondent = parts[0].strip(), parts[1].strip()
        elif " VS " in party_detail:
            parts = party_detail.split(" VS ", 1)
            petitioner, respondent = parts[0].strip(), parts[1].strip()

        # Handle nested objects
        status_raw = data.get("status") or data.get("case_status") or ""
        if isinstance(status_raw, dict):
            status = status_raw.get("status_desc") or status_raw.get("name") or ""
        else:
            status = str(status_raw).strip()

        district_raw = data.get("district") or ""
        if isinstance(district_raw, dict):
            district = district_raw.get("name") or ""
        else:
            district = str(district_raw).strip()

        category_raw = data.get("category") or ""
        category = str(category_raw) if not isinstance(category_raw, dict) else str_val(category_raw)

        return {
            "found": True,
            "party_detail": party_detail,
            "petitioner_name": petitioner,
            "respondent_name": respondent,
            "next_hearing_date": next_date,
            "cnr_no": cnr,
            "status": status,
            "advocate_name": advocate,
            "category": category,
            "diary_number": str_val(data.get("diary_number") or data.get("diaryNumber") or ""),
            "registration_date": str_val(data.get("registration_date") or data.get("registrationDate") or ""),
            "district": district,
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "MatterTracker Case Lookup API"})

@app.route("/case", methods=["GET"])
def get_case():
    case_type = request.args.get("type", "").strip().upper()
    case_no   = request.args.get("no",   "").strip()
    case_year = request.args.get("year", "").strip()
    if not case_type or not case_no or not case_year:
        return jsonify({"error": "Missing parameters: type, no, year"}), 400
    result = fetch_case(case_type, case_no, case_year)
    if result:
        return jsonify(result)
    return jsonify({"found": False, "message": "Case not found"}), 404
