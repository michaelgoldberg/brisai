"""
simulate.py - TrackIQ Monte Carlo Simulator
Factors (per spec):
  1. Best speed figure in last 4 races
  2. Horses inactive 6+ months are excluded
  3. Pace line (E1/E2/LP) in last 4 races
  4. Class (purse level)
  5. Race distance match
  6. Surface match
  7. Track condition match
  8. Training progression (speed fig trend last 4)
  9. Finish position in last 4 races
 10. Lengths behind at first call and stretch
"""

import random
import math

MODEL = "claude-sonnet-4-6"

# ── WEIGHTS ───────────────────────────────────────────────────────────────────
# All weights sum to 1.0

WEIGHTS = {
    "dirt": {
        "best_speed":      0.20,
        "pace_e1":         0.18,
        "pace_e2":         0.12,
        "pace_lp":         0.08,
        "class":           0.12,
        "distance_fit":    0.06,
        "surface_fit":     0.06,
        "condition_fit":   0.04,
        "trend":           0.06,
        "finish_pos":      0.05,
        "lengths_c1":      0.02,
        "lengths_str":     0.01,
    },
    "turf": {
        "best_speed":      0.18,
        "pace_e1":         0.12,
        "pace_e2":         0.12,
        "pace_lp":         0.10,
        "class":           0.18,
        "distance_fit":    0.06,
        "surface_fit":     0.08,
        "condition_fit":   0.04,
        "trend":           0.05,
        "finish_pos":      0.05,
        "lengths_c1":      0.01,
        "lengths_str":     0.01,
    },
    "synthetic": {
        "best_speed":      0.20,
        "pace_e1":         0.15,
        "pace_e2":         0.12,
        "pace_lp":         0.10,
        "class":           0.14,
        "distance_fit":    0.06,
        "surface_fit":     0.07,
        "condition_fit":   0.03,
        "trend":           0.06,
        "finish_pos":      0.05,
        "lengths_c1":      0.01,
        "lengths_str":     0.01,
    },
}

# Track-specific overrides (from empirical calibration)
TRACK_OVERRIDES = {
    "PEN": {
        "dirt": {
            "best_speed":   0.18,
            "pace_e1":      0.28,
            "pace_e2":      0.16,
            "pace_lp":      0.06,
            "class":        0.10,
            "distance_fit": 0.05,
            "surface_fit":  0.05,
            "condition_fit":0.03,
            "trend":        0.04,
            "finish_pos":   0.03,
            "lengths_c1":   0.01,
            "lengths_str":  0.01,
        }
    },
    "MNR": {
        "dirt": {
            "best_speed":   0.18,
            "pace_e1":      0.22,
            "pace_e2":      0.16,
            "pace_lp":      0.06,
            "class":        0.16,
            "distance_fit": 0.06,
            "surface_fit":  0.05,
            "condition_fit":0.04,
            "trend":        0.04,
            "finish_pos":   0.02,
            "lengths_c1":   0.01,
            "lengths_str":  0.00,
        },
        "muddy": {
            "best_speed":   0.15,
            "pace_e1":      0.28,
            "pace_e2":      0.18,
            "pace_lp":      0.05,
            "class":        0.16,
            "distance_fit": 0.05,
            "surface_fit":  0.04,
            "condition_fit":0.05,
            "trend":        0.02,
            "finish_pos":   0.01,
            "lengths_c1":   0.01,
            "lengths_str":  0.00,
        }
    },
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def get_weights(race_info):
    track   = (race_info.get("track") or "").upper()
    surface = (race_info.get("surface") or "Dirt").lower()
    cond    = (race_info.get("track_condition") or "").lower()

    # Determine surface bucket
    if "turf" in surface or "grass" in surface:
        surf_key = "turf"
    elif any(w in surface for w in ["synthetic","tapeta","polytrack","all weather"]):
        surf_key = "synthetic"
    elif any(w in cond for w in ["muddy","sloppy","wet"]):
        surf_key = "muddy"
    else:
        surf_key = "dirt"

    if track in TRACK_OVERRIDES and surf_key in TRACK_OVERRIDES[track]:
        return TRACK_OVERRIDES[track][surf_key]
    return WEIGHTS.get(surf_key, WEIGHTS["dirt"])


def ml_to_decimal(ml):
    try:
        return float(str(ml).strip())
    except:
        return None


def fmt_odds(prob):
    if prob <= 0:
        return "N/A"
    fair = (1.0 / prob) - 1.0
    if fair < 1.0:
        return f"1-{round(1/fair)}"
    return f"{fair:.1f}-1"


def fmt_ml(ml_dec):
    if ml_dec is None:
        return "N/A"
    return f"{ml_dec:.1f}-1"


# ── SCORE HORSE ───────────────────────────────────────────────────────────────

def score_horse(horse, race_info, weights):
    """Score a single horse. Returns float score (higher = better)."""

    past = horse.get("past_races", [])[:4]  # only last 4 races

    # ── 1. EXCLUSION: inactive 6+ months ──────────────────────────────────────
    if past:
        days_off = past[0].get("days_off") or 0
        if days_off > 180:
            return 0.0  # excluded

    # ── 2. BEST SPEED FIGURE (last 4) ─────────────────────────────────────────
    speed_figs = [p["bris_speed"] for p in past if p.get("bris_speed")]
    best_speed = max(speed_figs) if speed_figs else 60.0
    # Normalize to 0-100 (typical range 50-120)
    best_speed_norm = min(max((best_speed - 50) / 70 * 100, 0), 100)

    # ── 3. PACE (E1, E2, LP) average last 4 ──────────────────────────────────
    e1s = [p["e1_pace"] for p in past if p.get("e1_pace")]
    e2s = [p["e2_pace"] for p in past if p.get("e2_pace")]
    lps = [p["late_pace"] for p in past if p.get("late_pace")]
    avg_e1 = sum(e1s)/len(e1s) if e1s else 70.0
    avg_e2 = sum(e2s)/len(e2s) if e2s else 70.0
    avg_lp = sum(lps)/len(lps) if lps else 70.0
    # Normalize
    e1_norm  = min(max((avg_e1 - 50) / 60 * 100, 0), 100)
    e2_norm  = min(max((avg_e2 - 50) / 60 * 100, 0), 100)
    lp_norm  = min(max((avg_lp - 50) / 60 * 100, 0), 100)

    # ── 4. CLASS (avg purse last 4) ───────────────────────────────────────────
    purses = []
    for p in past:
        purse_raw = p.get("purse") or 0
        try:
            purses.append(float(str(purse_raw).replace(",","").replace("$","")))
        except:
            pass
    avg_purse = sum(purses)/len(purses) if purses else 10000
    class_norm = min(avg_purse / 100000 * 100, 100)

    # ── 5. DISTANCE FIT ───────────────────────────────────────────────────────
    today_dist = race_info.get("distance") or ""
    dist_matches = [p for p in past if p.get("distance") == today_dist]
    distance_fit = (len(dist_matches) / len(past) * 100) if past else 50.0

    # ── 6. SURFACE FIT ────────────────────────────────────────────────────────
    today_surf = (race_info.get("surface") or "").lower()
    surf_matches = [p for p in past if (p.get("surface") or "").lower() == today_surf]
    surface_fit = (len(surf_matches) / len(past) * 100) if past else 50.0

    # ── 7. TRACK CONDITION FIT ────────────────────────────────────────────────
    today_cond = (race_info.get("track_condition") or "").lower()
    # Fast/Good = 1 category, Off tracks = another
    today_off = any(w in today_cond for w in ["muddy","sloppy","wet","soft","yielding"])
    cond_matches = 0
    for p in past:
        p_cond = (p.get("track_cond") or "").lower()
        p_off  = any(w in p_cond for w in ["my","sl","gd","hy","sf","yl","wet"])  # off track codes
        if today_off == p_off:
            cond_matches += 1
    condition_fit = (cond_matches / len(past) * 100) if past else 50.0

    # ── 8. TRAINING PROGRESSION (speed fig trend last 4) ─────────────────────
    trend_mult = 1.0
    if len(speed_figs) >= 2:
        recent  = float(speed_figs[0])
        avg_prev = sum(float(f) for f in speed_figs[1:]) / len(speed_figs[1:])
        diff = recent - avg_prev
        if diff >= 8:    trend_mult = 1.12
        elif diff >= 4:  trend_mult = 1.06
        elif diff >= 1:  trend_mult = 1.02
        elif diff <= -8: trend_mult = 0.88
        elif diff <= -4: trend_mult = 0.94
        elif diff <= -1: trend_mult = 0.98

    # ── 9. FINISH POSITION (avg last 4, lower = better) ──────────────────────
    fin_pos = [p["finish_pos"] for p in past if p.get("finish_pos")]
    if fin_pos:
        avg_fin = sum(fin_pos) / len(fin_pos)
        num_horses_avg = sum(p.get("num_horses") or 8 for p in past if p.get("finish_pos")) / len(fin_pos)
        # Normalize: 1st = 100, last = 0
        finish_norm = max(0, (num_horses_avg - avg_fin) / (num_horses_avg - 1) * 100) if num_horses_avg > 1 else 50.0
    else:
        finish_norm = 50.0

    # ── 10. LENGTHS BEHIND at C1 and Stretch ─────────────────────────────────
    # pos_1st = position at first call, pos_str = position at stretch
    # pos 1 = leading, higher = further back
    c1_positions = [p["pos_1st"] for p in past if p.get("pos_1st")]
    str_positions = [p["pos_str"] for p in past if p.get("pos_str")]
    avg_c1_pos  = sum(c1_positions) / len(c1_positions) if c1_positions else 5.0
    avg_str_pos = sum(str_positions) / len(str_positions) if str_positions else 5.0
    # Lower position number = better (leading)
    c1_norm  = max(0, (10 - avg_c1_pos)  / 9 * 100)
    str_norm = max(0, (10 - avg_str_pos) / 9 * 100)

    # ── WEIGHTED SCORE ────────────────────────────────────────────────────────
    raw = (
        weights["best_speed"]      * best_speed_norm  +
        weights["pace_e1"]         * e1_norm          +
        weights["pace_e2"]         * e2_norm          +
        weights["pace_lp"]         * lp_norm          +
        weights["class"]           * class_norm       +
        weights["distance_fit"]    * distance_fit     +
        weights["surface_fit"]     * surface_fit      +
        weights["condition_fit"]   * condition_fit    +
        weights["trend"]           * 75.0             +  # placeholder, trend applied as multiplier
        weights["finish_pos"]      * finish_norm      +
        weights["lengths_c1"]      * c1_norm          +
        weights["lengths_str"]     * str_norm
    )

    return max(raw * trend_mult, 0.1)


# ── MONTE CARLO ───────────────────────────────────────────────────────────────

def run_simulation(race_data, api_key, n_sims=2000):
    race_info = race_data.get("race_info", {})
    horses    = race_data.get("horses", [])

    if not horses:
        return {"error": "No horses in race data."}

    weights = get_weights(race_info)

    # Score each horse — inactive horses return 0.0 and are flagged
    scored = []
    excluded = []
    for h in horses:
        score = score_horse(h, race_info, weights)
        if score == 0.0:
            excluded.append(h.get("horse_name",""))
        else:
            scored.append((h, max(score, 0.01)))

    if not scored:
        return {"error": "All horses excluded (inactive 6+ months)."}

    # Normalize to probabilities
    total = sum(s for _, s in scored)
    base_probs = [(h, s/total) for h, s in scored]

    # Count early speed for pace scenario
    style_counts = {}
    for h, _ in base_probs:
        s = h.get("bris_run_style","P")
        style_counts[s] = style_counts.get(s,0) + 1
    speed_horses = style_counts.get("E",0) + style_counts.get("EP",0) + style_counts.get("E/P",0)

    if speed_horses >= 3:
        pace_scenario = "Contested — multiple speed horses, pace may collapse"
    elif speed_horses == 2:
        pace_scenario = "Pressured — two speed horses will duel"
    elif speed_horses == 1:
        pace_scenario = "Lone speed — front-runner likely to control"
    else:
        pace_scenario = "Slow pace — no confirmed early speed"

    # Monte Carlo
    horse_list = [h for h, _ in base_probs]
    probs_only = [p for _, p in base_probs]
    win_counts = {str(h["program_num"]): 0 for h in horse_list}

    for _ in range(n_sims):
        # Variance scales with field size
        noise = 0.15 + max(len(horse_list) - 8, 0) * 0.015
        noisy = [max(p + random.gauss(0, p*noise), 0.001) for p in probs_only]
        total_n = sum(noisy)
        noisy = [p/total_n for p in noisy]

        r = random.random()
        cum = 0.0
        winner_idx = len(horse_list) - 1
        for i, p in enumerate(noisy):
            cum += p
            if r <= cum:
                winner_idx = i
                break
        win_counts[str(horse_list[winner_idx]["program_num"])] += 1

    # Build results
    rows = []
    for h, base_prob in base_probs:
        prog     = str(h["program_num"])
        wins     = win_counts[prog]
        win_pct  = wins / n_sims
        fair     = fmt_odds(win_pct)
        ml_dec   = ml_to_decimal(h.get("morning_line",""))
        ml_disp  = fmt_ml(ml_dec)

        rows.append({
            "program_num":  prog,
            "horse_name":   h["horse_name"],
            "win_prob_pct": f"{win_pct*100:.0f}%",
            "fair_odds":    fair,
            "morning_line": ml_disp,
            "ev_label":     "",
            "ev_color":     "neutral",
            "win_prob_raw": win_pct,
            "sim_wins":     wins,
        })

    rows.sort(key=lambda r: r["win_prob_raw"], reverse=True)

    key_factor = f"Surface: {race_info.get('surface','?')} · Condition: {race_info.get('track_condition','?')} · Best Speed + Pace weighted"
    if excluded:
        key_factor += f" · Excluded (6mo+): {', '.join(excluded)}"

    return {
        "rows":           rows,
        "pace_advantage": pace_scenario,
        "key_factor":     key_factor,
        "profile":        "custom",
        "n_sims":         n_sims,
        "excluded":       excluded,
    }
