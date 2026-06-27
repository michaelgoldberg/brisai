"""
app.py - TrackIQ AI Handicapping Trial App
"""

import os
import json
import uuid
import re
import tempfile
import requests
from datetime import datetime, timezone, timedelta
from flask import Flask, render_template, request, jsonify, Response, session

import anthropic
from brisnet_parser import parse_brisnet_file, build_claude_prompt

# ── CONFIG ────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key-change-in-production")

ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
AIRTABLE_PAT       = os.environ.get("AIRTABLE_PAT", "")
AIRTABLE_BASE_ID   = os.environ.get("AIRTABLE_BASE_ID", "")
AIRTABLE_PROSPECTS = os.environ.get("AIRTABLE_PROSPECTS_TABLE", "Table 1")
AIRTABLE_USAGE     = os.environ.get("AIRTABLE_USAGE_TABLE", "Table 2")
AIRTABLE_RESULTS   = "Results"

TRIAL_DAYS = int(os.environ.get("TRIAL_DAYS", "3"))
MODEL      = "claude-sonnet-4-6"
MAX_TOKENS = 4096

race_store = {}
pick_store = {}

SAMPLE_CARDS = {
    "CDX0627": {"label": "Churchill Downs - Sat Jun 27", "file": "CDX0627.DRF"},
    "BAQ0627": {"label": "Aqueduct - Sat Jun 27",        "file": "BAQ0627.DRF"},
    "CDX0628": {"label": "Churchill Downs - Sun Jun 28", "file": "CDX0628.DRF"},
    "BAQ0628": {"label": "Aqueduct - Sun Jun 28",        "file": "BAQ0628.DRF"},
}
SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "sample_cards")


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _races_from_parsed(parsed):
    str_races = {}
    for key, race in parsed.items():
        str_key = f"{key[0]}|{key[1]}|{key[2]}" if isinstance(key, tuple) else str(key)
        str_races[str_key] = race

    race_list = []
    for str_key, race in str_races.items():
        ri = race.get("race_info", {})
        race_num = ri.get("race_num") or race.get("race_num", "")
        if not race_num and "|" in str_key:
            race_num = str_key.split("|")[2]
        race_list.append({
            "key":        str_key,
            "race_num":   race_num,
            "distance":   ri.get("distance")   or race.get("distance", ""),
            "surface":    ri.get("surface")    or race.get("surface", ""),
            "race_class": ri.get("race_class") or race.get("race_class", ""),
            "num_horses": len(race.get("horses", [])),
        })

    race_list.sort(key=lambda r: int(str(r["race_num"])) if str(r["race_num"]).isdigit() else 0)
    return str_races, race_list


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

    today     = datetime.now(timezone.utc).date()
    today_str = today.strftime("%Y-%m-%d")
    existing  = _airtable_find_prospect(email)

    if existing:
        fields = existing["fields"]
        if fields.get("Blocked"):
            return jsonify({"expired": True, "message": "Your access has been suspended."})
        expires_str = fields.get("ExpiresAt", "")
        if expires_str:
            try:
                expires_date = datetime.strptime(expires_str[:10], "%Y-%m-%d").date()
                if today > expires_date:
                    return jsonify({"expired": True, "message": f"Your {TRIAL_DAYS}-day trial has ended."})
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

    session["name"]    = name
    session["email"]   = email
    session["company"] = company
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
        parsed = parse_brisnet_file(tmp_path)
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    if not parsed:
        return jsonify({"error": "No races found in file."}), 400

    str_races, race_list = _races_from_parsed(parsed)
    upload_id = str(uuid.uuid4())
    race_store[upload_id] = str_races
    return jsonify({"upload_id": upload_id, "races": race_list})


@app.route("/sample_cards")
def list_sample_cards():
    return jsonify({"cards": [{"id": k, "label": v["label"]} for k, v in SAMPLE_CARDS.items()]})


@app.route("/load_sample")
def load_sample():
    card_id = request.args.get("card", "")
    if card_id not in SAMPLE_CARDS:
        return jsonify({"error": "Unknown sample card."}), 400
    path = os.path.join(SAMPLE_DIR, SAMPLE_CARDS[card_id]["file"])
    if not os.path.exists(path):
        return jsonify({"error": f"Sample file not found: {path}"}), 404
    try:
        parsed = parse_brisnet_file(path)
    except Exception as e:
        return jsonify({"error": f"Could not parse file: {e}"}), 400
    if not parsed:
        return jsonify({"error": "No races found in file."}), 400
    str_races, race_list = _races_from_parsed(parsed)
    upload_id = str(uuid.uuid4())
    race_store[upload_id] = str_races
    return jsonify({"upload_id": upload_id, "races": race_list, "label": SAMPLE_CARDS[card_id]["label"]})


@app.route("/analyze")
def analyze():
    upload_id = request.args.get("upload_id", "")
    race_key  = request.args.get("race_key", "")

    if upload_id not in race_store:
        return Response(_err_stream("Session expired. Please re-upload your file."),
                        mimetype="text/event-stream")
    races = race_store[upload_id]
    if race_key not in races:
        return Response(_err_stream("Race not found."), mimetype="text/event-stream")

    race     = races[race_key]
    ri       = race.get("race_info", {})
    prompt   = build_claude_prompt(race)
    email    = session.get("email", "unknown")
    race_num = ri.get("race_num") or race.get("race_num", "")
    track    = ri.get("track")    or race.get("track", "")

    _airtable_log_usage({
        "Email":   email,
        "Track":   track,
        "RaceNum": str(race_num),
        "Date":    datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    })

    full_analysis = []

    def generate():
        yield f"data: {json.dumps({'ping': True})}\n\n"
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    full_analysis.append(text)
                    yield f"data: {json.dumps({'text': text})}\n\n"

            analysis_text = "".join(full_analysis)
            win_pick, place_pick, show_pick, exacta, trifecta = _extract_picks(analysis_text)
            if win_pick["pp"]:
                if upload_id not in pick_store:
                    pick_store[upload_id] = {}
                pick_store[upload_id][str(race_num)] = {
                    "win_pp":     win_pick["pp"],
                    "win_name":   win_pick["name"],
                    "win_odds":   win_pick["odds"],
                    "place_pp":   place_pick["pp"] if place_pick["pp"] else None,
                    "place_name": place_pick["name"],
                    "place_odds": place_pick["odds"],
                }
                yield f"data: {json.dumps({'picks': {'win': win_pick, 'place': place_pick, 'show': show_pick, 'exacta': exacta, 'trifecta': trifecta}})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    resp = Response(generate(), mimetype="text/event-stream")
    resp.headers["X-Accel-Buffering"] = "no"
    resp.headers["Cache-Control"]     = "no-cache"
    resp.headers["Connection"]        = "keep-alive"
    return resp


# ── RESULTS ───────────────────────────────────────────────────────────────────

@app.route("/upload_results", methods=["POST"])
def upload_results():
    if "file" not in request.files:
        return jsonify({"error": "No file provided."}), 400
    f         = request.files["file"]
    text      = f.read().decode("utf-8", errors="ignore")
    upload_id = request.form.get("upload_id", "")
    email     = session.get("email", "unknown")
    results   = _parse_results(text)
    if not results:
        return jsonify({"error": "Could not parse results file."}), 400

    picks          = pick_store.get(upload_id, {})
    card_summary   = []
    total_invested = 0.0
    total_returned = 0.0

    for race_num, race_result in sorted(results.items()):
        pick     = picks.get(str(race_num), {})
        win_pp   = pick.get("win_pp")
        place_pp = pick.get("place_pp")
        if not win_pp or not place_pp:
            card_summary.append({
                "race_num": race_num,
                "winner":   f"PP{race_result['winner_pp']} {race_result['winner_name']}",
                "place":    f"PP{race_result['place_pp']} {race_result['place_name']}",
                "picks_available": False,
            })
            continue
        roi = _calculate_roi(race_result, win_pp, place_pp)
        total_invested += roi["invested"]
        total_returned += roi["returned"]
        _airtable_save_result({
            "Track": race_result.get("track",""), "RaceDate": race_result.get("date",""),
            "RaceNum": race_num, "WinPick": pick.get("win_name",""),
            "WinPickPP": win_pp, "WinPickOdds": pick.get("win_odds",""),
            "PlacePick": pick.get("place_name",""), "PlacePickPP": place_pp,
            "PlacePickOdds": pick.get("place_odds",""),
            "ActualWinner": race_result.get("winner_name",""),
            "ActualPlace": race_result.get("place_name",""),
            "WinBetResult": "HIT" if roi["win_hit"] else "MISS",
            "PlaceBetResult": "HIT" if roi["place_hit"] else "MISS",
            "ExactaHit": roi["exacta_hit"], "WinPayout": roi["win_return"],
            "PlacePayout": roi["place_return"], "ExactaPayout": roi["exacta_return"],
            "RaceROI": roi["roi"], "Email": email,
        })
        card_summary.append({
            "race_num": race_num,
            "win_pick": f"PP{win_pp} {pick.get('win_name','')}",
            "place_pick": f"PP{place_pp} {pick.get('place_name','')}",
            "winner": f"PP{race_result['winner_pp']} {race_result['winner_name']}",
            "place":  f"PP{race_result['place_pp']} {race_result['place_name']}",
            "win_hit": roi["win_hit"], "place_hit": roi["place_hit"],
            "exacta_hit": roi["exacta_hit"], "win_return": roi["win_return"],
            "place_return": roi["place_return"], "exacta_return": roi["exacta_return"],
            "invested": roi["invested"], "returned": roi["returned"],
            "roi": roi["roi"], "picks_available": True,
        })

    card_roi = round(((total_returned-total_invested)/total_invested*100),1) if total_invested > 0 else 0
    return jsonify({"ok": True, "races": card_summary, "card_total": {
        "invested": round(total_invested,2), "returned": round(total_returned,2),
        "roi": card_roi, "races_with_picks": sum(1 for r in card_summary if r.get("picks_available")),
    }})


def _parse_results(text):
    races = {}
    ordinal_map = {'FIRST':1,'SECOND':2,'THIRD':3,'FOURTH':4,'FIFTH':5,'SIXTH':6,
                   'SEVENTH':7,'EIGHTH':8,'NINTH':9,'TENTH':10,'ELEVENTH':11,'TWELFTH':12}
    sections = re.split(r'(?=(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+RACE)',text,flags=re.IGNORECASE)
    for section in sections:
        if not section.strip(): continue
        m = re.match(r'(FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+RACE',section.strip(),re.IGNORECASE)
        if not m: continue
        race_num = ordinal_map[m.group(1).upper()]
        track_m = re.search(r'(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+RACE\s+(.+?)\s+(\w+\s+\d+\w*,?\s+\d{4})',section,re.IGNORECASE)
        track = track_m.group(1).strip() if track_m else ""
        date  = track_m.group(2).strip() if track_m else ""
        mutuel = re.findall(r'(\d+)-([A-Z][A-Z\s\']+?)\s+([\d.]+)(?:\s+([\d.]+))?(?:\s+([\d.]+))?\s*\.',section)
        finish_order = []; horse_payoffs = {}
        for i,match in enumerate(mutuel[:3]):
            pp_num=int(match[0]); name=match[1].strip(); finish_order.append(pp_num)
            if i==0: horse_payoffs[pp_num]={'win':float(match[2] or 0),'place':float(match[3] or 0),'name':name}
            elif i==1: horse_payoffs[pp_num]={'win':0,'place':float(match[2] or 0),'name':name}
            else: horse_payoffs[pp_num]={'win':0,'place':0,'name':name}
        ex = re.search(r'EXACTOR\s*\((\d+)-(\d+)\)\s*PAID\s*\$([\d.]+)',section,re.IGNORECASE)
        races[race_num]={'race_num':race_num,'track':track,'date':date,'finish_order':finish_order,'horse_payoffs':horse_payoffs,
            'winner_pp':finish_order[0] if finish_order else None,'place_pp':finish_order[1] if len(finish_order)>1 else None,
            'winner_name':horse_payoffs.get(finish_order[0],{}).get('name','') if finish_order else '',
            'place_name':horse_payoffs.get(finish_order[1],{}).get('name','') if len(finish_order)>1 else '',
            'win_payout':horse_payoffs.get(finish_order[0],{}).get('win',0) if finish_order else 0,
            'place_payout':horse_payoffs.get(finish_order[0],{}).get('place',0) if finish_order else 0,
            'exacta_pp1':int(ex.group(1)) if ex else None,'exacta_pp2':int(ex.group(2)) if ex else None,
            'exacta_payout':float(ex.group(3)) if ex else 0.0}
    return races


def _calculate_roi(race_result, win_pick_pp, place_pick_pp):
    invested=6.0; returned=0.0
    winner_pp=race_result.get('winner_pp'); place_pp=race_result.get('place_pp')
    win_hit=( win_pick_pp==winner_pp)
    win_return=race_result.get('win_payout',0) if win_hit else 0.0; returned+=win_return
    place_hit=place_pick_pp in [winner_pp,place_pp]
    if place_hit:
        place_return=race_result.get('place_payout',0) if place_pick_pp==winner_pp else race_result.get('horse_payoffs',{}).get(place_pick_pp,{}).get('place',0)
    else: place_return=0.0
    returned+=place_return
    exacta_hit=(race_result.get('exacta_pp1')==win_pick_pp and race_result.get('exacta_pp2')==place_pick_pp)
    exacta_return=race_result.get('exacta_payout',0)*2 if exacta_hit else 0.0; returned+=exacta_return
    return {'invested':invested,'returned':returned,'roi':round(((returned-invested)/invested)*100,1),
            'win_hit':win_hit,'win_return':win_return,'place_hit':place_hit,'place_return':place_return,
            'exacta_hit':exacta_hit,'exacta_return':exacta_return}


def _extract_picks(analysis_text):
    win_pick   = {'pp': None, 'name': '', 'odds': ''}
    place_pick = {'pp': None, 'name': '', 'odds': ''}
    show_pick  = {'pp': None, 'name': '', 'odds': ''}
    exacta     = ''
    trifecta   = ''

    pat_horse = r'PP(\d+)\s+([A-Za-z][A-Za-z0-9 ]+?)\s*\(ML\s*([\d/-]+)\)'
    win_m = re.search(r'WIN PICK:\s*' + pat_horse, analysis_text, re.IGNORECASE)
    if win_m:
        win_pick = {'pp': int(win_m.group(1)), 'name': win_m.group(2).strip(), 'odds': win_m.group(3).strip()}

    place_m = re.search(r'PLACE PICK:\s*' + pat_horse, analysis_text, re.IGNORECASE)
    if place_m:
        place_pick = {'pp': int(place_m.group(1)), 'name': place_m.group(2).strip(), 'odds': place_m.group(3).strip()}

    show_m = re.search(r'SHOW PICK:\s*' + pat_horse, analysis_text, re.IGNORECASE)
    if show_m:
        show_pick = {'pp': int(show_m.group(1)), 'name': show_m.group(2).strip(), 'odds': show_m.group(3).strip()}

    ex_m = re.search(r'EXACTA:\s*PP(\d+)-PP(\d+)', analysis_text, re.IGNORECASE)
    if ex_m:
        exacta = ex_m.group(1) + '-' + ex_m.group(2)

    tri_m = re.search(r'TRIFECTA:\s*PP(\d+)-PP(\d+)-PP(\d+)', analysis_text, re.IGNORECASE)
    if tri_m:
        trifecta = tri_m.group(1) + '-' + tri_m.group(2) + '-' + tri_m.group(3)

    return win_pick, place_pick, show_pick, exacta, trifecta


# ── AIRTABLE ──────────────────────────────────────────────────────────────────

def _at_headers():
    return {"Authorization": f"Bearer {AIRTABLE_PAT}", "Content-Type": "application/json"}

def _airtable_find_prospect(email):
    url=f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}"
    try:
        r=requests.get(url,headers=_at_headers(),params={"filterByFormula":f"LOWER({{Email}})='{email}'"},timeout=10)
        records=r.json().get("records",[]); return records[0] if records else None
    except Exception: return None

def _airtable_create_prospect(fields):
    url=f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}"
    try: requests.post(url,headers=_at_headers(),json={"fields":fields},timeout=10)
    except Exception: pass

def _airtable_update_prospect(record_id,fields):
    url=f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_PROSPECTS}/{record_id}"
    try: requests.patch(url,headers=_at_headers(),json={"fields":fields},timeout=10)
    except Exception: pass

def _airtable_log_usage(fields):
    url=f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_USAGE}"
    try: requests.post(url,headers=_at_headers(),json={"fields":fields},timeout=10)
    except Exception: pass

def _airtable_save_result(fields):
    url=f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_RESULTS}"
    try: requests.post(url,headers=_at_headers(),json={"fields":fields},timeout=10)
    except Exception: pass

def _err_stream(msg):
    yield f"data: {json.dumps({'error': msg})}\n\n"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
