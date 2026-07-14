"""
brisnet_parser.py  (CORRECTED — columnar past-race structure)
-------------------------------------------------------------
Reads a Brisnet Single File (.bris / .DRF / .csv) and returns
structured horse data grouped by race.

Key change from original: past-race data is COLUMNAR.
Access pattern:  row[ PAST_RACE_COL[attr] + i ]   (i = 0..9, 0=most recent)
NOT:             row[ base + i*81 + offset ]  ← that was wrong
"""

import csv
from brisnet_fields import (
    RACE_FIELDS, HORSE_FIELDS, PAST_RACE_COL, NUM_PAST_RACES,
    SURFACE_MAP, RACE_TYPE_MAP, BRIS_RUNNING_STYLE_MAP,
)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def safe_get(row, index, default=""):
    try:
        val = row[index].strip()
        return val if val else default
    except IndexError:
        return default


def safe_float(row, index, default=None):
    try:
        return float(row[index].strip())
    except (IndexError, ValueError):
        return default


def safe_int(row, index, default=None):
    try:
        return int(row[index].strip())
    except (IndexError, ValueError):
        return default


def yards_to_furlongs(yards_str):
    """Convert distance in yards to a readable furlongs string.
    Brisnet uses negative yards for turf routes in some versions — take abs()."""
    try:
        y = abs(float(yards_str))
        f = y / 220.0
        return f"{int(f)}f" if f == int(f) else f"{f:.1f}f"
    except (ValueError, TypeError):
        return yards_str or "?"


def foal_year_to_age(foal_year_str, race_year_str):
    """Derive horse age from 2-digit foal year and race year."""
    try:
        fy = int(foal_year_str.strip())
        ry = int(race_year_str.strip()[:4])
        # foal_year field stores last 2 digits (23 = 2023)
        full_fy = 2000 + fy if fy < 50 else 1900 + fy
        return ry - full_fy
    except (ValueError, TypeError):
        return None


def pace_pressure_label(horses):
    early_count = sum(1 for h in horses if h["bris_run_style"] in ("E", "E/P"))
    total = len(horses)
    if total == 0:
        return "Unknown"
    ratio = early_count / total
    if ratio >= 0.40:
        return "Hot (contested early)"
    elif ratio >= 0.20:
        return "Honest (moderate early pace)"
    else:
        return "Slow (lone speed / no pressure)"


# ── MAIN PARSER ───────────────────────────────────────────────────────────────

def parse_brisnet_file(filepath):
    """
    Parse a Brisnet single-file PP download.
    Returns a dict keyed by (track, date, race_num) → {race_info, horses}.
    """
    races = {}

    with open(filepath, "r", encoding="latin-1") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) < 50:
                continue

            # ── Race-level fields ──────────────────────────────────────────
            track    = safe_get(row, RACE_FIELDS["track"])
            date_raw = safe_get(row, RACE_FIELDS["date"])
            race_num = safe_get(row, RACE_FIELDS["race_num"]).lstrip()
            race_key = (track, date_raw, race_num)

            race_type_code = safe_get(row, RACE_FIELDS["race_type"])
            race_info = {
                "track":      track,
                "date":       _format_date(date_raw),
                "race_num":   race_num,
                "distance":   yards_to_furlongs(safe_get(row, RACE_FIELDS["distance"])),
                "surface":    SURFACE_MAP.get(safe_get(row, RACE_FIELDS["surface"]), "?"),
                "race_type":  RACE_TYPE_MAP.get(race_type_code, race_type_code),
                "race_class": safe_get(row, RACE_FIELDS["race_class"]),
                "purse":      _format_purse(safe_get(row, RACE_FIELDS["purse"])),
                "conditions": safe_get(row, RACE_FIELDS["conditions"]),
            }

            # ── Per-horse fields ───────────────────────────────────────────
            foal_year   = safe_get(row, HORSE_FIELDS["foal_year"])
            age         = foal_year_to_age(foal_year, date_raw)

            horse = {
                "horse_name":    safe_get(row, HORSE_FIELDS["horse_name"], "Unknown"),
                "program_num":   safe_get(row, HORSE_FIELDS["program_num"]).strip(),
                "post_pos":      safe_get(row, HORSE_FIELDS["post_pos"]),
                "morning_line":  safe_get(row, HORSE_FIELDS["morning_line"]),
                "trainer":       safe_get(row, HORSE_FIELDS["trainer"]),
                "jockey":        safe_get(row, HORSE_FIELDS["jockey"]),
                "age":           age,
                "sex":           safe_get(row, HORSE_FIELDS["sex"]),
                "weight":        safe_get(row, HORSE_FIELDS["weight"]),
                "owner":         safe_get(row, HORSE_FIELDS["owner"]),
                "state_bred":    safe_get(row, HORSE_FIELDS["state_bred"]),
                "sire":          safe_get(row, HORSE_FIELDS["sire"]),
                "bris_run_style":safe_get(row, HORSE_FIELDS["bris_run_style"]),
                "prime_power":   safe_float(row, HORSE_FIELDS["prime_power"]),
                "past_races":    [],
                "race_info":     race_info,
            }

            # ── Past performance data (COLUMNAR) ───────────────────────────
            past_races = []
            for i in range(NUM_PAST_RACES):
                date = safe_get(row, PAST_RACE_COL["date"] + i)
                if not date or date == "0":
                    break

                # Distance can be negative for turf in some versions
                dist_raw = safe_get(row, PAST_RACE_COL["distance"] + i)

                past_races.append({
                    "date":        _format_date(date),
                    "track":       safe_get(row, PAST_RACE_COL["track"] + i),
                    "race_type":   safe_get(row, PAST_RACE_COL["race_type"] + i),
                    "distance":    yards_to_furlongs(dist_raw),
                    "surface":     SURFACE_MAP.get(
                                       safe_get(row, PAST_RACE_COL["surface"] + i), "?"
                                   ),
                    "track_cond":  safe_get(row, PAST_RACE_COL["track_cond"] + i),
                    "finish_pos":  safe_int(row, PAST_RACE_COL["finish_pos"] + i),
                    "num_horses":  safe_int(row, PAST_RACE_COL["num_horses"] + i),
                    "odds":        safe_float(row, PAST_RACE_COL["odds"] + i),
                    "post_pos":    safe_int(row, PAST_RACE_COL["post_pos"] + i),
                    "days_off":    safe_int(row, PAST_RACE_COL["days_off"] + i),
                    "purse":       safe_get(row, PAST_RACE_COL["purse"] + i),
                    "comment":     safe_get(row, PAST_RACE_COL["comment"] + i),
                    "bris_speed":  safe_float(row, PAST_RACE_COL["bris_speed"] + i),
                    "e1_pace":     safe_float(row, PAST_RACE_COL["e1_pace"] + i),
                    "e2_pace":     safe_float(row, PAST_RACE_COL["e2_pace"] + i),
                    "late_pace":   safe_float(row, PAST_RACE_COL["late_pace"] + i),
                    "frac_1":      safe_float(row, PAST_RACE_COL["frac_1"] + i),
                    "frac_2":      safe_float(row, PAST_RACE_COL["frac_2"] + i),
                    "final_time":  safe_float(row, PAST_RACE_COL["final_time"] + i),
                    "winner":      safe_get(row, PAST_RACE_COL["winner"] + i),
                    "len_fin":     safe_float(row, PAST_RACE_COL["len_fin"] + i),
                    "pos_pp":      safe_int(row, PAST_RACE_COL["pos_pp"] + i),
                    "pos_1st":     safe_int(row, PAST_RACE_COL["pos_1st"] + i),
                    "pos_2nd":     safe_int(row, PAST_RACE_COL["pos_2nd"] + i),
                    "pos_str":     safe_int(row, PAST_RACE_COL["pos_str"] + i),
                    "pos_fin":     safe_int(row, PAST_RACE_COL["pos_fin"] + i),
                    "len_str":     safe_float(row, PAST_RACE_COL["len_str"] + i),
                    "past_trainer":safe_get(row, PAST_RACE_COL["past_trainer"] + i),
                    "past_jockey": safe_get(row, PAST_RACE_COL["past_jockey"] + i),
                })

            horse["past_races"] = past_races

            # Speed figure summaries
            speed_figs = [r["bris_speed"] for r in past_races if r["bris_speed"] is not None]
            horse["avg_speed"]  = round(sum(speed_figs[:3]) / len(speed_figs[:3]), 1) if speed_figs else None
            horse["best_speed"] = max(speed_figs) if speed_figs else None

            # Group by race
            if race_key not in races:
                races[race_key] = {"race_info": race_info, "horses": []}
            races[race_key]["horses"].append(horse)

    # Post-process each race
    for race_data in races.values():
        horses = race_data["horses"]
        race_data["pace_pressure"] = pace_pressure_label(horses)
        race_data["horses"].sort(key=lambda h: _prog_sort(h["program_num"]))

    return races


def build_race_label(race_key, race_info):
    track, date, race_num = race_key
    return (f"Race {race_num} — {track} — {race_info['date']} — "
            f"{race_info['distance']} {race_info['surface']} {race_info['race_class']}")


def build_claude_prompt(race_data, sim_data=None):
    info     = race_data["race_info"]
    horses   = race_data["horses"]
    pressure = race_data.get("pace_pressure", "Unknown")

    lines = [
        "You are an expert thoroughbred horse racing handicapper.",
        "Analyze the following race based ONLY on the structured data provided.",
        "Do not invent or assume any information not present in the data.\n",
        "== RACE INFORMATION ==",
        f"Track: {info['track']}",
        f"Date: {info['date']}",
        f"Race: {info['race_num']}",
        f"Distance: {info['distance']}",
        f"Surface: {info['surface']}",
        f"Class: {info['race_class']} ({info['race_type']})",
        f"Purse: {info['purse']}",
        f"Pace Pressure: {pressure}",
        "",
        "== HORSES ==",
    ]

    for h in horses:
        style_label = BRIS_RUNNING_STYLE_MAP.get(h["bris_run_style"], h["bris_run_style"])
        lines.append(f"\n-- #{h['program_num']} {h['horse_name']} (Post {h['post_pos']}) --")
        lines.append(f"  Age: {h['age'] or '?'}yo {h['sex']}  |  Wt: {h['weight']}  |  ML: {h['morning_line']}")
        lines.append(f"  Trainer: {h['trainer']}  |  Jockey: {h['jockey']}")
        lines.append(f"  Sire: {h['sire']}  |  State Bred: {h['state_bred']}")
        lines.append(f"  BRIS Prime Power: {h['prime_power'] or 'N/A'}")
        lines.append(f"  Avg Speed (last 3): {h['avg_speed'] or 'N/A'}  |  Best Speed: {h['best_speed'] or 'N/A'}")
        lines.append(f"  BRIS Running Style: {style_label} ({h['bris_run_style']})")

        if h["past_races"]:
            lines.append("  Recent Starts (newest first):")
            for pr in h["past_races"]:
                pos  = pr["finish_pos"] or "?"
                spd  = pr["bris_speed"] or "-"
                e1   = pr["e1_pace"]    or "-"
                lp   = pr["late_pace"]  or "-"
                cond = pr["track_cond"] or ""
                nhr  = f"/{pr['num_horses']}" if pr["num_horses"] else ""
                com  = f"  [{pr['comment']}]" if pr["comment"] else ""
                lines.append(
                    f"    {pr['date']} {pr['track']} {pr['distance']} {pr['surface']} "
                    f"Fin:{pos}{nhr} Spd:{spd} E1:{e1} LP:{lp} Cond:{cond}{com}"
                )
        else:
            lines.append("  Recent Starts: None / First-timer")

    # Add sim results if available
    if sim_data and not sim_data.get("error") and sim_data.get("rows"):
        lines.append("\n== SIMULATION RESULTS (2,000 runs) ==")
        lines.append("| # | Horse | Win% | Fair Odds | ML | EV |")
        lines.append("|---|-------|------|-----------|-----|-----|")
        for r in sim_data["rows"]:
            lines.append(
                f"| {r['program_num']} | {r['horse_name']} | {r['win_prob_pct']} | "
                f"{r['fair_odds']} | {r['morning_line']} | {r['ev_label']} |"
            )
        if sim_data.get("pace_advantage"):
            lines.append(f"\nPace Advantage: {sim_data['pace_advantage']}")
        if sim_data.get("key_factor"):
            lines.append(f"Key Factor: {sim_data['key_factor']}")

    lines += [
        "\n== ANALYSIS REQUEST ==",
        "Be BRIEF and DIRECT. 1-2 sentences max per section.",
        "Reference the simulation results above when making your picks.",
        "\n1. PACE: Who controls pace and who benefits.",
        "2. SPEED: Top 3 horses by figures.",
        "3. CLASS: Any notable drops or rises.",
        "4. BEST BET: Your top selection and why in 2 sentences.",
        "\nThen output EXACTLY this block with no deviations:",
        "\n=== PICKS ===",
        "WIN PICK: PP[#] [Horse Name] (ML [odds])",
        "PLACE PICK: PP[#] [Horse Name] (ML [odds])",
        "SHOW PICK: PP[#] [Horse Name] (ML [odds])",
        "EXACTA: PP[#]-PP[#]",
        "TRIFECTA: PP[#]-PP[#]-PP[#]",
    ]

    return "\n".join(lines)


# ── PRIVATE HELPERS ───────────────────────────────────────────────────────────

def _format_date(raw):
    raw = raw.strip()
    if len(raw) == 8:
        try:
            y, m, d = raw[:4], raw[4:6], raw[6:]
            if 1 <= int(m) <= 12:
                return f"{m}/{d}/{y}"
        except ValueError:
            pass
    return raw


def _format_purse(raw):
    try:
        return f"${int(raw):,}"
    except (ValueError, TypeError):
        return raw or "N/A"


def _prog_sort(prog):
    try:
        return int(prog)
    except (ValueError, TypeError):
        return 999
