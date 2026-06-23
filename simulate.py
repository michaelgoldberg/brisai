"""
simulate.py — Win probability + EV calculation for TrackIQ AI
Calls Claude for a JSON-only simulation, then computes Fair Odds and EV
against morning line.
"""

import json
import anthropic
from brisnet_fields import BRIS_RUNNING_STYLE_MAP

MODEL = "claude-sonnet-4-6"


def build_sim_prompt(race_data: dict) -> str:
    info   = race_data["race_info"]
    horses = race_data["horses"]

    lines = [
        "You are a thoroughbred handicapping probability engine.",
        "Assign win probabilities to each horse based on the structured data below.",
        "Factor in: BRIS Prime Power, average speed figures, best speed figure,",
        "running style fit for the pace scenario, class level, and days off.",
        "",
        f"Race: {info['track']} Race {info['race_num']} | {info['distance']} {info['surface']}",
        f"Class: {info['race_class']} | Purse: {info['purse']}",
        "",
        "HORSES:",
    ]

    for h in horses:
        style = BRIS_RUNNING_STYLE_MAP.get(h.get("bris_run_style", ""), "Unknown")
        lines.append(
            f"#{h['program_num']} {h['horse_name']} | "
            f"PP:{h.get('prime_power') or 'N/A'} | "
            f"AvgSpd:{h.get('avg_speed') or 'N/A'} | "
            f"BestSpd:{h.get('best_speed') or 'N/A'} | "
            f"Style:{style} | "
            f"DaysOff:{h['past_races'][0]['days_off'] if h.get('past_races') else 'N/A'}"
        )

    lines += [
        "",
        "Return ONLY valid JSON. No explanation, no markdown, no code fences.",
        "Format:",
        '{',
        '  "horses": [',
        '    {"program_num": "1", "horse_name": "NAME", "win_prob": 0.00}',
        '  ],',
        '  "pace_advantage": "one sentence on which running style benefits most",',
        '  "key_factor": "the single most important handicapping angle in this race"',
        '}',
        "Probabilities must sum to exactly 1.0. Include every horse listed above.",
    ]
    return "\n".join(lines)


def ml_to_decimal(ml_str: str) -> float | None:
    """Convert morning line string (e.g. '5.20', '15.00') to decimal odds-to-1."""
    try:
        return float(str(ml_str).strip())
    except (ValueError, TypeError):
        return None


def prob_to_fair_odds(prob: float) -> str:
    """Convert win probability to a human-readable fair odds string."""
    if prob <= 0:
        return "N/A"
    fair = (1.0 / prob) - 1.0
    if fair < 1.0:
        # Express as fraction below 1 (e.g. 1-2, 2-5)
        denom = round(1.0 / fair)
        return f"1-{denom}"
    return f"{fair:.1f}-1"


def ev_signal(win_prob: float, ml_decimal: float | None) -> dict:
    """
    Returns EV value and signal label.
    EV = (win_prob × (ml_decimal + 1)) - 1
    Positive = value bet vs morning line.
    """
    if ml_decimal is None or win_prob <= 0:
        return {"ev": None, "label": "—", "color": "neutral"}
    ev = (win_prob * (ml_decimal + 1)) - 1
    if ev >= 0.08:
        return {"ev": round(ev, 2), "label": f"+{round(ev*100):.0f}% EV ✅", "color": "positive"}
    elif ev <= -0.08:
        return {"ev": round(ev, 2), "label": f"{round(ev*100):.0f}% EV ❌", "color": "negative"}
    else:
        return {"ev": round(ev, 2), "label": "Fair ➖", "color": "neutral"}


def run_simulation(race_data: dict, api_key: str) -> dict:
    """
    Run the probability simulation and return enriched results.
    Returns dict with 'rows', 'pace_advantage', 'key_factor', or 'error'.
    """
    prompt = build_sim_prompt(race_data)
    client = anthropic.Anthropic(api_key=api_key)

    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = raw.replace("```json", "").replace("```", "").strip()
        sim = json.loads(raw)
    except json.JSONDecodeError as e:
        return {"error": f"Simulation parse error: {e}"}
    except Exception as e:
        return {"error": str(e)}

    # Build ML lookup from race_data
    ml_lookup = {
        h["program_num"]: ml_to_decimal(h.get("morning_line", ""))
        for h in race_data["horses"]
    }

    rows = []
    for h in sim.get("horses", []):
        prog    = str(h.get("program_num", ""))
        name    = h.get("horse_name", "")
        prob    = float(h.get("win_prob", 0))
        ml_dec  = ml_lookup.get(prog)
        ev_data = ev_signal(prob, ml_dec)

        # Format ML for display
        ml_display = f"{ml_dec:.1f}-1" if ml_dec is not None else "N/A"
        if ml_dec is not None and ml_dec < 1.0:
            ml_display = f"1-{round(1/ml_dec)}"

        rows.append({
            "program_num":  prog,
            "horse_name":   name,
            "win_prob_pct": f"{prob*100:.0f}%",
            "fair_odds":    prob_to_fair_odds(prob),
            "morning_line": ml_display,
            "ev_label":     ev_data["label"],
            "ev_color":     ev_data["color"],
            "win_prob_raw": prob,
        })

    # Sort by win probability descending
    rows.sort(key=lambda r: r["win_prob_raw"], reverse=True)

    return {
        "rows":           rows,
        "pace_advantage": sim.get("pace_advantage", ""),
        "key_factor":     sim.get("key_factor", ""),
    }
