"""
app.py - TrackIQ AI Handicapping Trial App
v2
"""

import os
import json
import uuid
import tempfile
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify, Response, session

import anthropic
from brisnet_parser import parse_brisnet_file, build_claude_prompt

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
AIRTABLE_PAT       = os.environ.get("AIRTABLE_PAT", "")
AIRTABLE_BASE_ID   = os.environ.get("AIRTABLE_BASE_ID", "")
AIRTABLE_PROSPECTS = "Table 1"
AIRTABLE_USAGE     = "Table 2"

TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "3"))
MODEL      = "claude-sonnet-4-6"
MAX_TOKENS = 2048

race_store = {}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    data    = request.get_json() or {}
    name    = data.get("name", "").strip()
    email   = data.get("email", "").strip().lower()
    company = data.get("company", "").strip()

    if not name or not email:
        return jsonify({"error": "Name and email are required."}), 400

    today     = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")

    existing = _airtable_find_prospect(email)

    if existing:
        fields = existing["fields"]
        if fields.get("Blocked"):
            return jsonify({"expired": True})
        expires_str = fields.get("ExpiresAt", "")
        if expires_str:
            try:
                expires_date = datetime.strptime(expires_str[:10], "%Y-%m-%d").date()
                if today > expires_date:
                    return jsonify({"expired": True})
            except ValueError:
                pass
        _airtable_update_prospect(existing["id"], {
            "LastAccess":  today_str,
            "AccessCount": (fields.get("AccessCount") or 0) + 1,
        })
    else:
        expires_date = today + timedelta(days=TRIAL_DAYS)
        _airtable_create_prospect({
            "Name":        name,
            "Email":       email,
            "Company":     company,
            "FirstOpened": today_str,
            "ExpiresAt":   expires_date.strftime("%Y-%m-%d"),
            "LastAccess":  today_str,
            "AccessCount": 1,
        })

    session["name"]  = name
    session["email"] = email
    return jsonify({"ok": True})


@app.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename."}), 400

    suffix = os.path.splitext(f.filename)[1].lower() or ".drf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        races = parse_brisnet_file(tmp_path)
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not races:
        return jsonify({"error": "No races found in file."}), 400

    upload_id = str(uuid.uuid4())

    str_races = {}
    for key, race in races.items():
        if isinstance(key, tuple):
            str_key = f"{key[0]}|{key[1]}|{key[2]}"
        else:
            str_key = str(key)
        str_races[str_key] = race

    race_store[upload_id] = str_races

    race_list = []
    for str_key, race in str_races.items():
        horses   = race.get("horses", [])
        race_num = race.get("race_num", "")
        if not race_num and "|" in str_key:
            race_num = str_key.split("|")[2]
        race_list.append({
            "key":        str_key,
            "race_num":   race_num,
            "distance":   race.get("distance", ""),
            "surface":    race.get("surface", ""),
            "race_class": race.get("race_class", ""),
            "num_horses": len(horses),
        })

    race_list.sort(key=lambda r: int(str(r["race_num"])) if str(r["race_num"]).isdigit() else 0)
    return jsonify({"upload_id": upload_id, "races": race_list})


@app.route("/analyze")
def analyze():
    upload_id = request.args.get("upload_id", "")
    race_key  = request.args.get("race_key", "")

    if upload_id not in race_store:
        return Response(_err_stream("Session expired. Please re-upload your file."), mimetype="text/event-stream")

    races = race_store[upload_id]
    if race_key not in races:
        return Response(_err_stream("Race not found."), mimetype="text/event-stream")

    race   = races[race_key]
    prompt = build_claude_prompt(race)
    email  = session.get("email", "unknown")

    _airtable_log_usage({
        "Email":   email,
        "Track":   race.get("track", ""),
        "RaceNum": str(race.get("race_num", "")),
        "Date":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })

    def generate():
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(generate(), mimetype="text/event-stream")


def _at_headers():
    return {"Authorization": f"Bearer {AIRTABLE_PAT}", "Content-Type": "application/json"}

def _airtable_find_prospect(email):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}"
    try:
        r = requests.get(url, headers=_at_headers(), params={"filterByFormula": f"LOWER({{Email}})=\'{email}\'"}, timeout=10)
        records = r.json().get("records", [])
        return records[0] if records else None
    except Exception:
        return None

def _airtable_create_prospect(fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}"
    try:
        requests.post(url, headers=_at_headers(), json={"fields": fields}, timeout=10)
    except Exception:
        pass

def _airtable_update_prospect(record_id, fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}/{record_id}"
    try:
        requests.patch(url, headers=_at_headers(), json={"fields": fields}, timeout=10)
    except Exception:
        pass

def _airtable_log_usage(fields):
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_USAGE}"
    try:
        requests.post(url, headers=_at_headers(), json={"fields": fields}, timeout=10)
    except Exception:
        pass

def _err_stream(msg):
    yield f"data: {json.dumps({'error': msg})}\n\n"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
