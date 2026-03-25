import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PHHC_API_BASE = "https://livedb9010.phhc.gov.in/cis_filing/public"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://new.phhc.gov.in",
    "Referer": "https://new.phhc.gov.in/",
}

def clean(v):
    if v is None:
        return ""
    if isinstance(v, dict):
        return str(v.get("name") or v.get("status_desc") or "").strip()
    return str(v).strip()

def clean_date(v):
    """Extract just the date part from a datetime string."""
    s = clean(v)
    if "T" in s:
        s = s.split("T")[0]
    return s

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

    try:
        r = requests.get(
            f"{PHHC_API_BASE}/getCase",
            params={"case_no": case_no, "case_type": case_type, "case_year": case_year},
            headers=HEADERS, timeout=15
        )
        if r.status_code != 200:
            return jsonify({"found": False, "message": "Case not found"}), 404

        data = r.json()
        if isinstance(data, list):
            if len(data) == 0:
                return jsonify({"found": False, "message": "Case not found"}), 404
            data = data[0]
        if not data:
            return jsonify({"found": False, "message": "Case not found"}), 404

        # ‚îÄ‚îÄ Party names ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        pet_name = clean(data.get("pet_name") or "")
        res_name = clean(data.get("res_name") or "")
        party_detail = f"{pet_name} Vs {res_name}" if pet_name and res_name else pet_name or res_name

        # ‚îÄ‚îÄ All petitioners (for full detail) ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        petitioners = []
        for p in (data.get("petitionerDetails") or []):
            name = clean(p.get("partyname") or "")
            if name:
                petitioners.append(name)

        # ‚îÄ‚îÄ All respondents ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        respondents = []
        for r_ in (data.get("respondentDetails") or []):
            name = clean(r_.get("partyname") or "")
            if name:
                respondents.append(name)

        # ‚îÄ‚îÄ Advocates ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        pet_adv_name   = clean(data.get("pet_adv_name") or "")
        pet_adv_enroll = clean(data.get("pet_adv_enrollment_year") or "")
        pet_advocate = f"{pet_adv_name} ({pet_adv_enroll})" if pet_adv_name and pet_adv_enroll else pet_adv_name

        res_adv_name   = clean(data.get("res_adv_name") or "")
        res_adv_enroll = clean(data.get("res_adv_enrollment_year") or "")
        res_advocate = f"{res_adv_name} ({res_adv_enroll})" if res_adv_name and res_adv_enroll else res_adv_name

        # ‚îÄ‚îÄ Status ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        status_raw = data.get("status") or {}
        if isinstance(status_raw, dict):
            status = clean(status_raw.get("status_desc") or "")
        else:
            status = clean(status_raw)

        # Determine if case is disposed or pending
        is_disposed = bool(data.get("disposal_date") or
                          (isinstance(status_raw, dict) and status_raw.get("status_type") == "M"))

        # ‚îÄ‚îÄ Dates ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        # Next hearing date ‚Äî for pending cases
        next_date = clean_date(
            data.get("next_date") or data.get("cause_list_date") or
            data.get("proposed_cause_list_date") or ""
        )

        # Listing date (last listed)
        listing_date = clean_date(data.get("listing_or_proposal_date") or "")

        # Registration date
        reg_date = clean_date(data.get("reg_date") or data.get("filling_date") or "")

        # Disposal date (if disposed)
        disposal_date = clean_date(data.get("disposal_date") or "")

        # Final order upload date
        final_order_date = clean_date(data.get("final_order_date_uploaded_on") or "")

        # ‚îÄ‚îÄ Other fields ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ‚îÄ
        district_raw = data.get("district") or {}
        district = clean(district_raw.get("name") if isinstance(district_raw, dict) else district_raw)

        cat_desc  = clean(data.get("cat_desc") or "")
        bench     = clean(data.get("bench_name") or "")
        cnr       = clean(data.get("cnr_no") or "")
        diary_no  = str(data.get("case_diary_no") or "")
        list_type = clean(data.get("list_type") or "")

        # Final order link
        order_link = clean(data.get("order") or "")

        return jsonify({
            "found": True,

            # Core party info
            "party_detail": party_detail,
            "petitioner_name": pet_name,
            "respondent_name": res_name,
            "petitioners": petitioners,
            "respondents": respondents,

            # Advocates
            "petitioner_advocate": pet_advocate,
            "respondent_advocate": res_advocate,

            # Case identifiers
            "cnr_no": cnr,
            "diary_number": diary_no,
            "case_type": case_type,
            "case_no": case_no,
            "case_year": case_year,

            # Category & nature
            "category": cat_desc,

            # Court details
            "bench": bench,
            "district": district,
            "list_type": list_type,

            # Status
            "status": status,
            "is_disposed": is_disposed,

            # Dates
            "registration_date": reg_date,
            "next_hearing_date": next_date,
            "listing_date": listing_date,
            "disposal_date": disposal_date,
            "final_order_date": final_order_date,

            # Order
            "order_link": order_link,
        })

    except Exception as e:
        print(f"[API] Error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/orders", methods=["GET"])
def get_orders():
    """Fetch all orders/judgments for a case from PHHC."""
    case_type = request.args.get("type", "").strip().upper()
    case_no   = request.args.get("no",   "").strip()
    case_year = request.args.get("year", "").strip()
    if not case_type or not case_no or not case_year:
        return jsonify({"error": "Missing parameters: type, no, year"}), 400
    try:
        url = f"{PHHC_API_BASE}/judgmentDetails/{case_no}/{case_year}/{case_type}?skip=0&limit=1000"
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return jsonify({"orders": [], "count": 0})
        raw = r.json()
        if not isinstance(raw, list):
            return jsonify({"orders": [], "count": 0})
        orders = []
        for item in raw:
            order_type_code = item.get("order_type", "")
            order_type = "FINAL" if order_type_code == "F" else "INTERIM" if order_type_code == "I" else order_type_code
            order_date_raw = item.get("orderdate", "")
            order_date = str(order_date_raw).split("T")[0] if order_date_raw else ""
            orders.append({
                "order_date": order_date,
                "order_type": order_type,
                "order_url": item.get("order") or "",
                "bench": item.get("bench_name") or "",
                "citation": item.get("citation_no") or "",
                "uploaded": item.get("upload") == "Y",
            })
        orders.sort(key=lambda x: x["order_date"], reverse=True)
        return jsonify({"orders": orders, "count": len(orders)})
    except Exception as e:
        print(f"[API] Orders error: {e}")
        return jsonify({"orders": [], "count": 0, "error": str(e)})
