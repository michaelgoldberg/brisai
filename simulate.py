"""
simulate.py - TrackIQ Monte Carlo Simulator
Factor priority (per spec):
  PACE (heaviest):
    - E1 pace (base figure at first call)
    - E2 pace (base figure at second call)  
    - LP late pace
    - Position at first call (lengths from front)
    - Position at stretch (lengths from front)
  SPEED (secondary):
    - Best speed figure last 4 races
    - Speed figure trend (training progression)
  JOCKEY (tiebreaker):
    - Jockey win% at this track/meet
  SUPPORTING:
    - Class, distance fit, surface fit, condition fit, finish position
  EXCLUSION: horses inactive 6+ months
"""

import random

# ── WEIGHTS ───────────────────────────────────────────────────────────────────

WEIGHTS = {
    "dirt": {
        # PACE — 52% total (E1 + LP only, no E2)
        "pace_e1":         0.26,   # Early pace - first call
        "pace_e2":         0.00,   # Removed
        "pace_lp":         0.16,   # Final/late pace
        "pos_c1":          0.06,   # Position at first call
        "pos_str":         0.04,   # Position at stretch (within 3 lengths filter applied separately)
        # SPEED — 22% total
        "best_speed":      0.14,
        "trend":           0.08,
        # JOCKEY — 8%
        "jockey_win_pct":  0.08,
        # SUPPORTING — 18%
        "class":           0.08,
        "distance_fit":    0.04,
        "surface_fit":     0.03,
        "condition_fit":   0.02,
        "finish_pos":      0.01,
    },
    "turf": {
        # PACE — 46% (E1 + LP only)
        "pace_e1":         0.20,
        "pace_e2":         0.00,
        "pace_lp":         0.18,
        "pos_c1":          0.04,
        "pos_str":         0.04,
        # SPEED — 22%
        "best_speed":      0.14,
        "trend":           0.08,
        # JOCKEY — 8%
        "jockey_win_pct":  0.08,
        # SUPPORTING — 24%
        "class":           0.12,
        "distance_fit":    0.05,
        "surface_fit":     0.04,
        "condition_fit":   0.02,
        "finish_pos":      0.01,
    },
    "synthetic": {
        # PACE — 48% (E1 + LP only)
        "pace_e1":         0.22,
        "pace_e2":         0.00,
        "pace_lp":         0.16,
        "pos_c1":          0.05,
        "pos_str":         0.05,
        # SPEED — 22%
        "best_speed":      0.14,
        "trend":           0.08,
        # JOCKEY — 8%
        "jockey_win_pct":  0.08,
        # SUPPORTING — 22%
        "class":           0.10,
        "distance_fit":    0.05,
        "surface_fit":     0.04,
        "condition_fit":   0.02,
        "finish_pos":      0.01,
    },
}

# Track-specific overrides
TRACK_OVERRIDES = {
    "PEN": {
        "dirt": {
            "pace_e1":        0.30,
            "pace_e2":        0.00,
            "pace_lp":        0.18,
            "pos_c1":         0.06,
            "pos_str":        0.04,
            "best_speed":     0.12,
            "trend":          0.06,
            "jockey_win_pct": 0.08,
            "class":          0.08,
            "distance_fit":   0.04,
            "surface_fit":    0.02,
            "condition_fit":  0.01,
            "finish_pos":     0.01,
        }
    },
    # Del Mar: turf-heavy, closers benefit on both surfaces, longer stretch
    "DMR": {
        "dirt": {
            "pace_e1":        0.18,
            "pace_e2":        0.00,
            "pace_lp":        0.32,   # Closers do well at Del Mar
            "pos_c1":         0.04,
            "pos_str":        0.07,
            "best_speed":     0.14,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.05,
            "distance_fit":   0.02,
            "surface_fit":    0.01,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
        "turf": {
            "pace_e1":        0.14,
            "pace_e2":        0.00,
            "pace_lp":        0.38,   # Strong closer bias on DMR turf
            "pos_c1":         0.03,
            "pos_str":        0.08,
            "best_speed":     0.12,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.06,
            "distance_fit":   0.02,
            "surface_fit":    0.01,
            "condition_fit":  0.00,
            "finish_pos":     0.00,
        },
    },
    # Monmouth: speed-friendly on dirt, balanced on turf
    "MTH": {
        "dirt": {
            "pace_e1":        0.28,
            "pace_e2":        0.00,
            "pace_lp":        0.18,
            "pos_c1":         0.06,
            "pos_str":        0.05,
            "best_speed":     0.14,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.07,
            "distance_fit":   0.03,
            "surface_fit":    0.02,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
        "turf": {
            "pace_e1":        0.18,
            "pace_e2":        0.00,
            "pace_lp":        0.28,
            "pos_c1":         0.04,
            "pos_str":        0.07,
            "best_speed":     0.12,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.10,
            "distance_fit":   0.02,
            "surface_fit":    0.02,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
    },
    # Gulfstream: speed-biased dirt, class dominant
    "GP": {
        "dirt": {
            "pace_e1":        0.26,
            "pace_e2":        0.00,
            "pace_lp":        0.18,
            "pos_c1":         0.06,
            "pos_str":        0.05,
            "best_speed":     0.14,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.10,
            "distance_fit":   0.03,
            "surface_fit":    0.01,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
        "turf": {
            "pace_e1":        0.16,
            "pace_e2":        0.00,
            "pace_lp":        0.28,
            "pos_c1":         0.04,
            "pos_str":        0.06,
            "best_speed":     0.12,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.12,
            "distance_fit":   0.03,
            "surface_fit":    0.02,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
    },
    "SAR": {
        "dirt": {
            "pace_e1":        0.16,
            "pace_e2":        0.00,
            "pace_lp":        0.40,   # LP dominant at SAR dirt
            "pos_c1":         0.03,
            "pos_str":        0.07,
            "best_speed":     0.12,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.03,
            "distance_fit":   0.02,
            "surface_fit":    0.01,
            "condition_fit":  0.00,
            "finish_pos":     0.00,
        },
        "turf": {
            "pace_e1":        0.14,
            "pace_e2":        0.00,
            "pace_lp":        0.40,   # LP dominant at SAR turf
            "pos_c1":         0.02,
            "pos_str":        0.08,
            "best_speed":     0.12,
            "trend":          0.08,
            "jockey_win_pct": 0.08,
            "class":          0.04,
            "distance_fit":   0.02,
            "surface_fit":    0.01,
            "condition_fit":  0.01,
            "finish_pos":     0.00,
        },
    },
    "MNR": {
        "dirt": {
            "pace_e1":        0.26,
            "pace_e2":        0.00,
            "pace_lp":        0.18,
            "pos_c1":         0.06,
            "pos_str":        0.04,
            "best_speed":     0.14,
            "trend":          0.06,
            "jockey_win_pct": 0.08,
            "class":          0.10,
            "distance_fit":   0.04,
            "surface_fit":    0.02,
            "condition_fit":  0.01,
            "finish_pos":     0.01,
        },
        "muddy": {
            "pace_e1":        0.30,
            "pace_e2":        0.00,
            "pace_lp":        0.16,
            "pos_c1":         0.06,
            "pos_str":        0.04,
            "best_speed":     0.12,
            "trend":          0.04,
            "jockey_win_pct": 0.08,
            "class":          0.10,
            "distance_fit":   0.04,
            "surface_fit":    0.02,
            "condition_fit":  0.02,
            "finish_pos":     0.00,
        }
    },
}


def get_weights(race_info):
    track   = (race_info.get("track") or "").upper()
    surface = (race_info.get("surface") or "Dirt").lower()
    cond    = (race_info.get("track_condition") or "").lower()

    if "turf" in surface or "grass" in surface:
        surf_key = "turf"
    elif any(w in surface for w in ["synthetic","tapeta","polytrack"]):
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
    if prob <= 0: return "N/A"
    fair = (1.0 / prob) - 1.0
    return f"1-{round(1/fair)}" if fair < 1.0 else f"{fair:.1f}-1"


def fmt_ml(ml_dec):
    if ml_dec is None: return "N/A"
    return f"{ml_dec:.1f}-1"


def score_horse(horse, race_info, weights):
    past = horse.get("past_races", [])[:4]

    # EXCLUSION: inactive 6+ months
    if past:
        days_off = past[0].get("days_off") or 0
        if days_off > 180:
            return 0.0

    # ── PACE FACTORS ──────────────────────────────────────────────────────────
    # Recency-weighted pace: most recent race counts 2x, second 1.5x, rest 1x
    RECENCY = [2.0, 1.5, 1.0, 1.0]
    def weighted_avg(vals_from_past, field):
        vals = [(p[field], RECENCY[i]) for i,p in enumerate(vals_from_past) if p.get(field)]
        if not vals: return None
        return sum(v*w for v,w in vals) / sum(w for _,w in vals)

    avg_e1 = weighted_avg(past, "e1_pace")   or 70.0
    avg_lp = weighted_avg(past, "late_pace") or 70.0

    e1_norm = min(max((avg_e1 - 50) / 60 * 100, 0), 100)
    e2_norm = 0.0  # Removed per spec
    lp_norm = min(max((avg_lp - 50) / 60 * 100, 0), 100)

    # WITHIN 3 LENGTHS AT STRETCH filter
    # Horses that have been within 3 lengths of lead at stretch get a bonus
    # Horses that were more than 3 lengths back at stretch in ALL recent races get a penalty
    stretch_within_3 = 0
    stretch_total = 0
    for p in past:
        str_pos = p.get("pos_str")
        len_str = p.get("len_str")  # lengths behind at stretch
        if str_pos is not None:
            stretch_total += 1
            # If position is 1-3 or lengths behind <= 3, considered "within 3"
            if str_pos <= 3 or (len_str is not None and len_str <= 3.0):
                stretch_within_3 += 1

    if stretch_total > 0:
        stretch_pct = stretch_within_3 / stretch_total
        if stretch_pct >= 0.75:
            stretch_mult = 1.08   # Usually within 3 at stretch
        elif stretch_pct >= 0.50:
            stretch_mult = 1.03   # Sometimes within 3
        elif stretch_pct == 0:
            stretch_mult = 0.88   # Never within 3 at stretch - big penalty
        else:
            stretch_mult = 0.96   # Rarely within 3
    else:
        stretch_mult = 1.0  # No data

    # Position at C1 and stretch (lower position = closer to front = better)
    c1_pos  = [p["pos_1st"] for p in past if p.get("pos_1st")]
    str_pos = [p["pos_str"] for p in past if p.get("pos_str")]
    avg_c1  = sum(c1_pos)/len(c1_pos)   if c1_pos  else 5.0
    avg_str = sum(str_pos)/len(str_pos) if str_pos else 5.0
    # Normalize: position 1 = 100, position 10+ = 0
    c1_norm  = max(0, (10 - avg_c1)  / 9 * 100)
    str_norm = max(0, (10 - avg_str) / 9 * 100)

    # ── SPEED FACTORS ─────────────────────────────────────────────────────────
    speed_figs = [p["bris_speed"] for p in past if p.get("bris_speed")]
    best_speed = max(speed_figs) if speed_figs else 60.0
    # Blend best speed with recency-weighted recent speed for better signal
    recent_spd = weighted_avg(past, "bris_speed") or best_speed
    blended_speed = (best_speed * 0.6 + recent_spd * 0.4)
    best_speed_norm = min(max((blended_speed - 50) / 70 * 100, 0), 100)

    # Trend (training progression) — recency weighted
    trend_mult = 1.0
    if len(speed_figs) >= 2:
        recent   = float(speed_figs[0])
        avg_prev = sum(float(f) for f in speed_figs[1:]) / len(speed_figs[1:])
        diff = recent - avg_prev
        if diff >= 8:    trend_mult = 1.14
        elif diff >= 4:  trend_mult = 1.07
        elif diff >= 1:  trend_mult = 1.03
        elif diff <= -8: trend_mult = 0.86
        elif diff <= -4: trend_mult = 0.93
        elif diff <= -1: trend_mult = 0.97

    # Form cycle bonus: reward horses that finished well in most recent race
    if past:
        last = past[0]
        last_fin  = last.get("finish_pos") or 99
        last_num  = last.get("num_horses") or 8
        # Won last race
        if last_fin == 1:
            trend_mult *= 1.10
        # Finished in top 25% of field
        elif last_fin <= max(2, last_num * 0.25):
            trend_mult *= 1.05
        # Finished last or near last
        elif last_fin >= last_num - 1 and last_num >= 5:
            trend_mult *= 0.92

    trend_norm = 75.0

    # ── JOCKEY WIN % ──────────────────────────────────────────────────────────
    j_starts = horse.get("jockey_starts") or 0
    j_wins   = horse.get("jockey_wins")   or 0
    if j_starts and j_starts > 0:
        j_win_pct = j_wins / j_starts
        # Normalize: 30%+ win rate = 100, 0% = 0
        jockey_norm = min(j_win_pct / 0.30 * 100, 100)
    else:
        jockey_norm = 15.0  # unknown jockey gets a below-average score

    # ── SUPPORTING FACTORS ────────────────────────────────────────────────────
    # Class
    purses = []
    for p in past:
        try:
            purses.append(float(str(p.get("purse") or 0).replace(",","").replace("$","")))
        except:
            pass
    avg_purse  = sum(purses)/len(purses) if purses else 10000
    class_norm = min(avg_purse / 100000 * 100, 100)

    # Distance fit
    today_dist = race_info.get("distance") or ""
    dist_matches = sum(1 for p in past if p.get("distance") == today_dist)
    distance_fit = (dist_matches / len(past) * 100) if past else 50.0

    # Surface fit
    today_surf = (race_info.get("surface") or "").lower()
    surf_matches = sum(1 for p in past if (p.get("surface") or "").lower() == today_surf)
    surface_fit = (surf_matches / len(past) * 100) if past else 50.0

    # Condition fit
    today_cond = (race_info.get("track_condition") or "").lower()
    today_off  = any(w in today_cond for w in ["muddy","sloppy","wet","soft","yielding"])
    cond_matches = 0
    for p in past:
        p_cond = (p.get("track_cond") or "").lower()
        p_off  = any(w in p_cond for w in ["my","sl","gd","hy","sf","yl","wet"])
        if today_off == p_off:
            cond_matches += 1
    condition_fit = (cond_matches / len(past) * 100) if past else 50.0

    # Finish position
    fin_pos = [p["finish_pos"] for p in past if p.get("finish_pos")]
    if fin_pos:
        avg_fin = sum(fin_pos) / len(fin_pos)
        num_h   = sum(p.get("num_horses") or 8 for p in past if p.get("finish_pos")) / len(fin_pos)
        finish_norm = max(0, (num_h - avg_fin) / max(num_h - 1, 1) * 100)
    else:
        finish_norm = 50.0

    # ── WEIGHTED SCORE ────────────────────────────────────────────────────────
    raw = (
        weights["pace_e1"]        * e1_norm        +
        weights.get("pace_e2", 0.0)   * e2_norm        +
        weights["pace_lp"]        * lp_norm        +
        weights["pos_c1"]         * c1_norm        +
        weights["pos_str"]        * str_norm       +
        weights["best_speed"]     * best_speed_norm+
        weights["trend"]          * trend_norm     +
        weights["jockey_win_pct"] * jockey_norm    +
        weights["class"]          * class_norm     +
        weights["distance_fit"]   * distance_fit   +
        weights["surface_fit"]    * surface_fit    +
        weights["condition_fit"]  * condition_fit  +
        weights["finish_pos"]     * finish_norm
    )

    return max(raw * trend_mult * stretch_mult, 0.1)


def run_simulation(race_data, api_key, n_sims=2000, user_weights=None):
    race_info = race_data.get("race_info", {})
    horses    = race_data.get("horses", [])

    if not horses:
        return {"error": "No horses in race data."}

    weights  = user_weights if user_weights else get_weights(race_info)
    scored   = []
    excluded = []

    for h in horses:
        s = score_horse(h, race_info, weights)
        if s == 0.0:
            excluded.append(h.get("horse_name",""))
        else:
            scored.append((h, max(s, 0.01)))

    if not scored:
        return {"error": "All horses excluded (inactive 6+ months)."}

    total      = sum(s for _, s in scored)
    base_probs = [(h, s/total) for h, s in scored]

    # Pace scenario
    style_counts = {}
    for h, _ in base_probs:
        st = h.get("bris_run_style","P")
        style_counts[st] = style_counts.get(st,0) + 1
    speed = style_counts.get("E",0) + style_counts.get("EP",0) + style_counts.get("E/P",0)

    if speed >= 3:   pace_scenario = "Contested — multiple speed horses, pace may collapse"
    elif speed == 2: pace_scenario = "Pressured — two speed horses will duel"
    elif speed == 1: pace_scenario = "Lone speed — front-runner likely to control"
    else:            pace_scenario = "Slow pace — no confirmed early speed"

    # Monte Carlo 2,000 sims
    horse_list = [h for h,_ in base_probs]
    probs_only = [p for _,p in base_probs]
    win_counts = {str(h["program_num"]): 0 for h in horse_list}

    for _ in range(n_sims):
        # Tighter noise for smaller fields to sharpen differentiation
        if len(horse_list) <= 6:
            noise = 0.08
        elif len(horse_list) <= 9:
            noise = 0.11
        else:
            noise = 0.13 + max(len(horse_list)-10, 0) * 0.01
        noisy = [max(p + random.gauss(0, p*noise), 0.001) for p in probs_only]
        tot   = sum(noisy); noisy = [p/tot for p in noisy]
        r = random.random(); cum = 0.0; wi = len(horse_list)-1
        for i,p in enumerate(noisy):
            cum += p
            if r <= cum: wi = i; break
        win_counts[str(horse_list[wi]["program_num"])] += 1

    rows = []
    for h, base_prob in base_probs:
        prog    = str(h["program_num"])
        wins    = win_counts[prog]
        win_pct = wins / n_sims
        j_starts = h.get("jockey_starts") or 0
        j_wins   = h.get("jockey_wins")   or 0
        j_pct    = f"{j_wins/j_starts*100:.0f}%" if j_starts else "N/A"

        rows.append({
            "program_num":   prog,
            "horse_name":    h["horse_name"],
            "win_prob_pct":  f"{win_pct*100:.1f}%",
            "fair_odds":     fmt_odds(win_pct),
            "morning_line":  fmt_ml(ml_to_decimal(h.get("morning_line",""))),
            "jockey":        h.get("jockey",""),
            "jockey_win_pct": j_pct,
            "ev_label":      "",
            "ev_color":      "neutral",
            "win_prob_raw":  win_pct,
            "sim_wins":      wins,
        })

    rows.sort(key=lambda r: r["win_prob_raw"], reverse=True)

    key_factor = f"Pace-dominant weighting (52% pace factors) · Jockey win% included"
    if excluded:
        key_factor += f" · Excluded (6mo+): {', '.join(excluded)}"

    return {
        "rows":           rows,
        "pace_advantage": pace_scenario,
        "key_factor":     key_factor,
        "profile":        "pace-dominant",
        "n_sims":         n_sims,
        "excluded":       excluded,
    }


# ── HARVILLE FORMULA — EXACT EXOTIC COMBINATION PROBABILITIES ─────────────
# Given win probabilities from the simulation, calculate exact probabilities
# for exacta / trifecta / superfecta finishing orders using conditional
# elimination (Harville 1973), with an optional bias correction.

def harville_combo_prob(win_probs, order):
    """
    win_probs: dict {horse_id: win_probability}
    order: list of horse_ids in finish order, e.g. ['3','7','5'] = 3 wins, 7 second, 5 third
    Returns the Harville-formula probability of that exact finishing order.
    """
    remaining = dict(win_probs)
    prob = 1.0
    for horse_id in order:
        p = remaining.get(horse_id, 0.0)
        total = sum(remaining.values())
        if total <= 0:
            return 0.0
        prob *= (p / total)
        del remaining[horse_id]
    return prob


def harville_bias_correction(prob, position):
    """
    Harville's formula tends to overvalue longshots in 2nd/3rd/4th and
    undervalue favorites in those spots. Apply a mild empirical correction
    (Stern-style dampening) based on position depth.
    position: 1=win, 2=place, 3=show, 4=fourth
    """
    if position <= 1:
        return prob
    # Dampen probability slightly more for deeper positions
    dampen = {2: 0.97, 3: 0.93, 4: 0.88}.get(position, 0.85)
    return prob * dampen


def top_n_permutations(rows, n_positions, top_k=10, field_limit=8):
    """
    rows: list of dicts from run_simulation()['rows'], each with
          'program_num' and 'win_prob_raw'
    n_positions: 2 for exacta, 3 for trifecta, 4 for superfecta
    Returns top_k finishing-order combinations ranked by Harville probability,
    each with pretty-printed odds.
    """
    import itertools

    # Limit to the most likely contenders to keep permutation count sane
    pool = sorted(rows, key=lambda r: r['win_prob_raw'], reverse=True)[:field_limit]
    win_probs = {r['program_num']: r['win_prob_raw'] for r in pool}
    name_map  = {r['program_num']: r['horse_name'] for r in pool}

    combos = []
    for order in itertools.permutations(win_probs.keys(), n_positions):
        raw_prob = harville_combo_prob(win_probs, list(order))
        # Apply position-based dampening to the whole combo (approx: apply once at depth)
        corrected = raw_prob * harville_bias_correction(1.0, n_positions)
        combos.append({
            "order":      list(order),
            "horses":     [name_map[o] for o in order],
            "prob_raw":   raw_prob,
            "prob":       corrected,
        })

    combos.sort(key=lambda c: c["prob"], reverse=True)
    top = combos[:top_k]

    for c in top:
        pct = c["prob"] * 100
        c["prob_pct"] = f"{pct:.2f}%" if pct >= 0.1 else f"{pct:.3f}%"
        fair = (1.0 / c["prob"]) if c["prob"] > 0 else 0
        c["fair_payout"] = f"${fair:.2f}" if fair > 0 else "N/A"
        c["combo_str"] = "-".join(c["order"])

    return top


def build_exotic_report(sim_result, field_limit=8):
    """
    Takes the output of run_simulation() and returns ranked Exacta,
    Trifecta, and Superfecta combinations using the Harville formula.
    """
    rows = sim_result.get("rows", [])
    if not rows:
        return {"error": "No simulation rows available."}

    n_horses = len(rows)

    report = {
        "exacta":     top_n_permutations(rows, 2, top_k=10, field_limit=field_limit),
        "trifecta":   top_n_permutations(rows, 3, top_k=10, field_limit=min(field_limit, n_horses)) if n_horses >= 3 else [],
        "superfecta": top_n_permutations(rows, 4, top_k=10, field_limit=min(field_limit, n_horses)) if n_horses >= 4 else [],
        "field_size": n_horses,
        "field_limit_used": min(field_limit, n_horses),
    }
    return report
