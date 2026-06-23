"""
app.py — BrisAI Handicapping Trial App
Airtable structure: Email, FirstOpened, ExpiresAt, LastAccess, AccessCount, Blocked
"""

import os
import json
import uuid
import tempfile
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify, Response, session

import anthropic
from brisnet_parser import parse_brisnet_file, build_race_label, build_claude_prompt

# ── CONFIG ────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
AIRTABLE_PAT       = os.environ.get("AIRTABLE_PAT", "")
AIRTABLE_BASE_ID   = os.environ.get("AIRTABLE_BASE_ID", "")
AIRTABLE_PROSPECTS = os.environ.get("AIRTABLE_PROSPECTS_TABLE", "Table 1")
AIRTABLE_USAGE     = os.environ.get("AIRTABLE_USAGE_TABLE", "Table 2")

TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "3"))
MODEL      = "claude-sonnet-4-6"
MAX_TOKENS = 2048

race_store: dict = {}


# ── ROUTES ────────────────────────────────────────────────────────────────────

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

    today      = datetime.now(timezone.utc).date()
    today_str  = today.strftime("%Y-%m-%d")

    existing = _airtable_find_prospect(email)

    if existing:
        fields = existing["fields"]

        # Check if manually blocked
        if fields.get("Blocked"):
            return jsonify({
                "trial_expired": True,
                "message": "Your trial access has ended. Contact us to continue.",
            })

        # Check ExpiresAt
        expires_str = fields.get("ExpiresAt", "")
        if expires_str:
            try:
                expires_date = datetime.strptime(expires_str[:10], "%Y-%m-%d").date()
                if today > expires_date:
                    return jsonify({
                        "trial_expired": True,
                        "message": (
                            f"Your {TRIAL_DAYS}-day trial has ended. "
                            "Contact us to continue."
                        ),
                    })
                days_remaining = (expires_date - today).days
            except ValueError:
                days_remaining = TRIAL_DAYS
        else:
            days_remaining = TRIAL_DAYS

        # Update LastAccess and AccessCount
        count = int(fields.get("AccessCount", 0) or 0)
        _airtable_update_prospect(existing["id"], {
            "LastAccess":  today_str,
            "AccessCount": count + 1,
        })

    else:
        # New prospect — create record
        expires_str    = (today + timedelta(days=TRIAL_DAYS)).strftime("%Y-%m-%d")
        days_remaining = TRIAL_DAYS
        _airtable_create_prospect(email, today_str, expires_str)

    session["prospect"] = {"name": name, "email": email, "company": company}
    return jsonify({"ok": True, "days_remaining": days_remaining})


@app.route("/upload", methods=["POST"])
def upload():
    if not session.get("prospect"):
        return jsonify({"error": "Session expired. Please refresh and sign in again."}), 401

    if "file" not in request.files:
        return jsonify({"error": "No file attached."}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "Empty filename."}), 400

    suffix = os.path.splitext(f.filename)[1] or ".DRF"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        f.save(tmp.name)
        tmp_path = tmp.name

    try:
        races = parse_brisnet_file(tmp_path)
    except Exception as exc:
        return jsonify({"error": f"Parse error: {exc}"}), 400
    finally:
        os.unlink(tmp_path)

    if not races:
        return jsonify({
            "error": "No valid race data found. Make sure this is a Brisnet Single-File (.DRF / .bris)."
        }), 400

    upload_id = str(uuid.uuid4())
    race_store[upload_id] = races
    session["upload_id"]  = upload_id
    session["filename"]   = f.filename

    race_list = []
    for key in sorted(races.keys(), key=lambda k: (k[1], _sort_int(k[2]))):
        info = races[key]["race_info"]
        race_list.append({
            "key":        f"{key[0]}|{key[1]}|{key[2]}",
            "label":      build_race_label(key, info),
            "num_horses": len(races[key]["horses"]),
            "surface":    info.get("surface", ""),
            "race_class": info.get("race_class", ""),
            "purse":      info.get("purse", ""),
        })

    return jsonify({"races": race_list, "upload_id": upload_id})


@app.route("/analyze")
def analyze():
    if not session.get("prospect"):
        def _unauth():
            yield f'data: {json.dumps({"error": "Session expired. Please refresh."})}\n\n'
        return Response(_unauth(), content_type="text/event-stream")

    # Re-check trial on every analysis
    prospect = session["prospect"]
    existing = _airtable_find_prospect(prospect["email"])
    if existing:
        fields = existing["fields"]
        if fields.get("Blocked"):
            def _blocked():
                yield f'data: {json.dumps({"trial_expired": True, "error": "Your access has been blocked."})}\n\n'
            return Response(_blocked(), content_type="text/event-stream")
        expires_str = fields.get("ExpiresAt", "")
        if expires_str:
            try:
                expires_date = datetime.strptime(expires_str[:10], "%Y-%m-%d").date()
                if datetime.now(timezone.utc).date() > expires_date:
                    def _expired():
                        yield f'data: {json.dumps({"trial_expired": True, "error": "Your trial has ended."})}\n\n'
                    return Response(_expired(), content_type="text/event-stream")
            except ValueError:
                pass

    upload_id    = request.args.get("upload_id") or session.get("upload_id")
    race_key_str = request.args.get("race_key", "")

    def _err(msg):
        return Response(
            f'data: {json.dumps({"error": msg})}\n\n',
            content_type="text/event-stream",
        )

    if not upload_id or upload_id not in race_store:
        return _err("Session expired — please re-upload your file.")

    parts = race_key_str.split("|")
    if len(parts) != 3:
        return _err("Invalid race selection.")

    race_key = tuple(parts)
    races    = race_store[upload_id]

    if race_key not in races:
        return _err("Race not found — please re-select.")

    race_data = races[race_key]
    prompt    = build_claude_prompt(race_data)

    def generate():
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for chunk in stream.text_stream:
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
        except anthropic.AuthenticationError:
            yield f"data: {json.dumps({'error': 'API key error — contact support.'})}\n\n"
            return
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
            return

        yield f"data: {json.dumps({'done': True})}\n\n"

        # Log usage
        info = race_data["race_info"]
        _airtable_log_usage(
            email      = prospect.get("email", ""),
            name       = prospect.get("name", ""),
            company    = prospect.get("company", ""),
            filename   = session.get("filename", ""),
            track      = info.get("track", ""),
            race_num   = info.get("race_num", ""),
            race_date  = info.get("date", ""),
            race_class = info.get("race_class", ""),
            purse      = info.get("purse", ""),
        )

    return Response(
        generate(),
        content_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── AIRTABLE HELPERS ──────────────────────────────────────────────────────────

def _at_headers():
    return {
        "Authorization": f"Bearer {AIRTABLE_PAT}",
        "Content-Type":  "application/json",
    }


def _airtable_find_prospect(email: str):
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        return None
    try:
        resp = requests.get(
            f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}",
            headers=_at_headers(),
            params={"filterByFormula": f'LOWER({{Email}})="{email}"', "maxRecords": 1},
            timeout=6,
        )
        records = resp.json().get("records", [])
        return records[0] if records else None
    except Exception:
        return None


def _airtable_create_prospect(email: str, first_opened: str, expires_at: str):
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        return
    try:
        requests.post(
            f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}",
            headers=_at_headers(),
            json={"fields": {
                "Email":       email,
                "FirstOpened": first_opened,
                "ExpiresAt":   expires_at,
                "LastAccess":  first_opened,
                "AccessCount": 1,
            }},
            timeout=6,
        )
    except Exception:
        pass


def _airtable_update_prospect(record_id: str, fields: dict):
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        return
    try:
        requests.patch(
            f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}/{record_id}",
            headers=_at_headers(),
            json={"fields": fields},
            timeout=6,
        )
    except Exception:
        pass


def _airtable_log_usage(email, name, company, filename,
                         track, race_num, race_date, race_class, purse):
    if not AIRTABLE_PAT or not AIRTABLE_BASE_ID:
        return
    try:
        requests.post(
            f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_USAGE}",
            headers=_at_headers(),
            json={"fields": {
                "Email":       email,
                "Name":        name,
                "Company":     company,
                "File":        filename,
                "Track":       track,
                "Race":        race_num,
                "Race Date":   race_date,
                "Class":       race_class,
                "Purse":       purse,
                "Analyzed At": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }},
            timeout=6,
        )
    except Exception:
        pass


def _sort_int(val):
    try:
        return int(str(val).strip())
    except (ValueError, TypeError):
        return 999


# ── ENTRY POINT ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
