"""
simulate.py - TrackIQ Monte Carlo Simulator
True numerical simulation with explicit, tunable factor weights.
Runs 2,000 race simulations per call. No LLM involved in probability calc.
"""

import random
import json
import anthropic
from brisnet_fields import BRIS_RUNNING_STYLE_MAP

MODEL = "claude-sonnet-4-6"

# ── WEIGHT PROFILES ────────────────────────────────────────────────────────
# Weights must sum to 1.0 per profile.
# Tuned from Jun 27 BAQ/CDX results analysis.

# Weights focused on pace figures, class, and style — Prime Power and speed figures removed
WEIGHTS = {
    "fast_dirt": {
        "prime_power":   0.00,
        "speed_avg":     0.00,
        "speed_best":    0.00,
        "pace_e1":       0.40,   # Early pace dominant on fast dirt
        "pace_e2":       0.30,   # Middle pace
        "class":         0.15,
        "style_fit":     0.15,
    },
    "sloppy_dirt": {
        "prime_power":   0.00,
        "speed_avg":     0.00,
        "speed_best":    0.00,
        "pace_e1":       0.25,   # Pace less reliable on wet
        "pace_e2":       0.20,
        "class":         0.30,   # Class dominates on sloppy
        "style_fit":     0.25,   # Closers benefit on wet tracks
    },
    "turf": {
        "prime_power":   0.00,
        "speed_avg":     0.00,
        "speed_best":    0.00,
        "pace_e1":       0.30,
        "pace_e2":       0.25,
        "class":         0.30,   # Class critical on turf
        "style_fit":     0.15,
    },
    "muddy_dirt": {
        "prime_power":   0.00,
        "speed_avg":     0.00,
        "speed_best":    0.00,
        "pace_e1":       0.20,
        "pace_e2":       0.18,
        "class":         0.35,   # Class most important on muddy
        "style_fit":     0.27,
    },
}

# Running style scores for pace scenario fit
# Higher = better fit when style matches the pace scenario
STYLE_SCORES = {
    "E":  {"speed_bias": 1.15, "off_track_penalty": 0.90},  # Early speed
    "EP": {"speed_bias": 1.08, "off_track_penalty": 0.95},  # Early-presser
    "P":  {"speed_bias": 1.00, "off_track_penalty": 1.00},  # Presser
    "PS": {"speed_bias": 0.98, "off_track_penalty": 1.02},
    "S":  {"speed_bias": 0.92, "off_track_penalty": 1.08},  # Stalker/closer
    "SS": {"speed_bias": 0.88, "off_track_penalty": 1.12},  # Deep closer
}

# ── HELPER: detect track condition from race_info ─────────────────────────

def get_weight_profile(race_info: dict) -> tuple[str, dict]:
    surface   = (race_info.get("surface") or "Dirt").lower()
    condition = (race_info.get("track_condition") or "").lower()

    if "turf" in surface or "grass" in surface:
        return "turf", WEIGHTS["turf"]
    if any(w in condition for w in ["sloppy", "muddy", "wet", "good to sloppy"]):
        if "muddy" in condition:
            return "muddy_dirt", WEIGHTS["muddy_dirt"]
        return "sloppy_dirt", WEIGHTS["sloppy_dirt"]
    return "fast_dirt", WEIGHTS["fast_dirt"]


# ── SCORE A SINGLE HORSE ──────────────────────────────────────────────────

def score_horse(horse: dict, weights: dict, profile_name: str, pace_count: dict) -> float:
    """
    Returns a raw score for a horse. Higher = better.
    All factors normalized to 0-100 scale before weighting.
    """
    pp         = horse.get("prime_power")    or 80.0
    avg_spd    = horse.get("avg_speed")      or 70.0
    best_spd   = horse.get("best_speed")     or 70.0
    style_code = horse.get("bris_run_style") or "P"

    # Past races for pace figures
    past = horse.get("past_races", [])
    e1_figs = [p["e1_pace"]   for p in past[:4] if p.get("e1_pace")]
    e2_figs = [p["e2_pace"]   for p in past[:4] if p.get("e2_pace")]
    e1 = sum(e1_figs) / len(e1_figs) if e1_figs else 80.0
    e2 = sum(e2_figs) / len(e2_figs) if e2_figs else 80.0

    # Class proxy: use purse of most recent race or default
    class_score = 75.0
    if past:
        recent_purse = int(float(str(past[0].get("purse") or 0).replace(",","").replace("$","") or 0))
        if recent_purse > 100000:
            class_score = 95.0
        elif recent_purse > 50000:
            class_score = 85.0
        elif recent_purse > 25000:
            class_score = 78.0
        elif recent_purse > 10000:
            class_score = 70.0
        else:
            class_score = 62.0

    # Running style fit score
    style_info  = STYLE_SCORES.get(style_code, STYLE_SCORES["P"])
    e_count     = pace_count.get("E", 0) + pace_count.get("EP", 0)
    total       = max(pace_count.get("total", 1), 1)
    speed_bias  = pace_count.get("speed_bias", 1.0)

    # On sloppy, closers get a bonus
    off_track_mult = 1.0
    if "sloppy" in profile_name or "muddy" in profile_name:
        off_track_mult = style_info["off_track_penalty"]

    style_fit_score = 75.0 * style_info["speed_bias"] * off_track_mult

    # Days off adjustment
    days_off = past[0].get("days_off", 30) if past else 30
    freshness = 1.0
    if days_off and days_off > 90:
        freshness = 0.92   # Long layoff penalty
    elif days_off and days_off < 10:
        freshness = 0.95   # Too quick back

    # Speed figure TREND over last 3 races
    # Improving = bonus, declining = penalty
    spd_figs = [p.get("bris_speed") for p in past[:3] if p.get("bris_speed")]
    trend_mult = 1.0
    if len(spd_figs) >= 2:
        # Most recent is index 0
        recent  = float(spd_figs[0])
        prev    = float(spd_figs[1])
        diff    = recent - prev

        if len(spd_figs) >= 3:
            # Use average of last 2 vs most recent for smoother signal
            avg_prev = (float(spd_figs[1]) + float(spd_figs[2])) / 2
            diff = recent - avg_prev

        if diff >= 8:
            trend_mult = 1.12    # Strong improver (+12%)
        elif diff >= 4:
            trend_mult = 1.06    # Mild improver (+6%)
        elif diff >= 1:
            trend_mult = 1.02    # Slight improver (+2%)
        elif diff <= -8:
            trend_mult = 0.88    # Sharp decliner (-12%)
        elif diff <= -4:
            trend_mult = 0.94    # Mild decliner (-6%)
        elif diff <= -1:
            trend_mult = 0.98    # Slight decliner (-2%)
        # else: flat — no adjustment

    # Weighted score
    raw = (
        weights["prime_power"] * float(pp)          +
        weights["speed_avg"]   * float(avg_spd)     +
        weights["speed_best"]  * float(best_spd)    +
        weights["pace_e1"]     * float(e1)           +
        weights["pace_e2"]     * float(e2)           +
        weights["class"]       * float(class_score)  +
        weights["style_fit"]   * float(style_fit_score)
    )

    return raw * freshness * trend_mult


# ── MONTE CARLO ──────────────────────────────────────────────────────────

def run_simulation(race_data: dict, api_key: str, n_sims: int = 2000) -> dict:
    """
    Run n_sims Monte Carlo race simulations.
    Returns win counts, probabilities, fair odds, and EV vs ML.
    """
    race_info = race_data.get("race_info", {})
    horses    = race_data.get("horses", [])

    if not horses:
        return {"error": "No horses in race data."}

    profile_name, weights = get_weight_profile(race_info)

    # Count running styles for pace scenario
    style_counts = {}
    for h in horses:
        s = h.get("bris_run_style", "P")
        style_counts[s] = style_counts.get(s, 0) + 1
    style_counts["total"] = len(horses)

    # Determine pace bias (crowded speed = closers benefit)
    speed_horses = style_counts.get("E", 0) + style_counts.get("EP", 0)
    if speed_horses >= 3:
        style_counts["speed_bias"] = 0.95   # Contested pace favors closers
        pace_scenario = "Contested — multiple speed horses, pace should collapse, closers favored"
    elif speed_horses == 0:
        style_counts["speed_bias"] = 1.05   # Lone speed
        pace_scenario = "Lone speed — front-runner likely to control and wire the field"
    else:
        style_counts["speed_bias"] = 1.0
        pace_scenario = "Moderate pace — no clear pace advantage"

    # Score each horse
    scores = []
    for h in horses:
        s = score_horse(h, weights, profile_name, style_counts)
        scores.append((h, max(s, 0.01)))   # floor at 0.01

    # Normalize scores to probabilities
    total_score = sum(s for _, s in scores)
    base_probs  = [(h, s / total_score) for h, s in scores]

    # Monte Carlo: 2,000 simulations
    win_counts = {h["program_num"]: 0 for h, _ in base_probs}
    probs_only = [p for _, p in base_probs]
    horse_list = [h for h, _ in base_probs]

    for _ in range(n_sims):
        # Add noise to simulate real-world variance
        noisy = [max(p + random.gauss(0, p * 0.15), 0.001) for p in probs_only]
        total = sum(noisy)
        noisy = [p / total for p in noisy]

        # Pick winner by weighted random draw
        r = random.random()
        cumulative = 0.0
        winner_idx = len(horse_list) - 1
        for i, p in enumerate(noisy):
            cumulative += p
            if r <= cumulative:
                winner_idx = i
                break

        win_counts[horse_list[winner_idx]["program_num"]] += 1

    # Build results
    rows = []
    for h, base_prob in base_probs:
        prog     = str(h["program_num"])
        wins     = win_counts[prog]
        win_pct  = wins / n_sims
        fair_odds = prob_to_fair_odds(win_pct)
        ml_dec   = ml_to_decimal(h.get("morning_line", ""))
        ev       = ev_signal(win_pct, ml_dec)
        ml_disp  = fmt_ml(ml_dec)

        rows.append({
            "program_num":  prog,
            "horse_name":   h["horse_name"],
            "win_prob_pct": f"{win_pct*100:.0f}%",
            "fair_odds":    fair_odds,
            "morning_line": ml_disp,
            "ev_label":     ev["label"],
            "ev_color":     ev["color"],
            "win_prob_raw": win_pct,
            "sim_wins":     wins,
        })

    rows.sort(key=lambda r: r["win_prob_raw"], reverse=True)

    return {
        "rows":           rows,
        "pace_advantage": pace_scenario,
        "key_factor":     f"Profile: {profile_name.replace('_',' ').title()} — Top factor: {max(weights, key=weights.get).replace('_',' ').title()}",
        "profile":        profile_name,
        "n_sims":         n_sims,
    }


# ── FORMATTING HELPERS ────────────────────────────────────────────────────

def ml_to_decimal(ml_str) -> float | None:
    try:
        return float(str(ml_str).strip())
    except (ValueError, TypeError):
        return None

def fmt_ml(ml_dec) -> str:
    if ml_dec is None:
        return "N/A"
    if ml_dec < 1.0:
        return f"1-{round(1/ml_dec)}"
    return f"{ml_dec:.1f}-1"

def prob_to_fair_odds(prob: float) -> str:
    if prob <= 0:
        return "N/A"
    fair = (1.0 / prob) - 1.0
    if fair < 1.0:
        denom = round(1.0 / fair)
        return f"1-{denom}"
    return f"{fair:.1f}-1"

def ev_signal(win_prob: float, ml_decimal) -> dict:
    if ml_decimal is None or win_prob <= 0:
        return {"ev": None, "label": "—", "color": "neutral"}
    ev = (win_prob * (ml_decimal + 1)) - 1
    if ev >= 0.08:
        return {"ev": round(ev,2), "label": f"+{round(ev*100):.0f}% EV ✅", "color": "positive"}
    elif ev <= -0.08:
        return {"ev": round(ev,2), "label": f"{round(ev*100):.0f}% EV ❌", "color": "negative"}
    else:
        return {"ev": round(ev,2), "label": "Fair ➖", "color": "neutral"}
