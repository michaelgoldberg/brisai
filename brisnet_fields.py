"""
brisnet_fields.py  (CORRECTED — verified against CDX0502.DRF)
--------------------------------------------------------------
All indices are 0-based. Verified empirically by parsing a real
Brisnet Single File (.DRF) with 169 horse rows / 1435 fields per row.

KEY DISCOVERY: Past-race data is COLUMNAR, not block-based.
Each attribute (date, speed, pace, …) occupies a contiguous
10-slot array.  Past race i (0=most recent) is at:
    row[ PAST_RACE_COL[attr] + i ]
"""

# ── RACE-LEVEL FIELDS ─────────────────────────────────────────────────────────
# Same for every horse row in a race.
RACE_FIELDS = {
    "track":       0,    # Track code (e.g. CD, KEE, AQU)
    "date":        1,    # Race date YYYYMMDD
    "race_num":    2,    # Race number
    "post_pos":    3,    # Post position (also per-horse, but race context)
    "distance":    5,    # Distance in yards  ← was 6, now FIXED
    "surface":     6,    # D=Dirt T=Turf A=All-Weather  ← was 7, FIXED
    "race_type":   8,    # S/A/C/M/MC/AO/CO/N/G1/G2/G3
    "race_class":  10,   # Short class label e.g. "Md Sp Wt"  ← new
    "purse":       11,   # Purse in dollars
    "conditions":  15,   # Full conditions text (long string)
    "horse_list":  16,   # Semicolon-delimited entry list (informational)
}

# ── PER-HORSE FIELDS ──────────────────────────────────────────────────────────
HORSE_FIELDS = {
    "post_pos":    3,    # Post position
    "trainer":     27,   # Trainer name  ← was 21, FIXED
    "program_num": 42,   # Program number  ← was 28, FIXED
    "morning_line":43,   # Morning line odds (e.g. 15.00 = 15-1)  ← was 15, FIXED
    "horse_name":  44,   # Horse name  ← was 27, FIXED
    "foal_year":   45,   # Foal year (e.g. 23 = 2023 = 3yo in 2026)  ← was "age"@24
    "sex":         48,   # C/G/F/M/R  ← was 25, FIXED
    "color":       49,   # Color code (DKBBR, GR, etc.)
    "weight":      50,   # Assigned weight (lbs)  ← was 18, FIXED
    "sire":        51,   # Sire name
    "dam":         52,   # Dam name (maternal)
    "dam_sire":    53,   # Dam's sire
    "jockey":      32,   # Jockey name  ← was 22, FIXED
    "owner":       38,   # Owner name
    "state_bred":  56,   # State bred (KY, FL, CA, etc.)
    "bris_run_style": 209, # Brisnet running style: E / E/P / P / S / NA  ← NEW
    "prime_power": 250,  # BRIS Prime Power Rating  ← index was right!
    "bris_speed_current": 235, # BRIS speed figure for today (if available)
}

# ── PAST PERFORMANCE — COLUMNAR STRUCTURE ─────────────────────────────────────
# Brisnet stores 10 past races per horse.
# Each attribute has its own 10-element array starting at the base below.
# Access: row[ PAST_RACE_COL[attr] + i ]   (i=0 = most recent race)

NUM_PAST_RACES = 10   # max slots; many will be empty

PAST_RACE_COL = {
    # ── Identity ──────────────────────────────────────────────────────────
    "date":        255,  # YYYYMMDD
    "days_off":    265,  # Days since prior race
    "track":       275,  # Track code
    "post_pos":    295,  # Post position in that race
    "track_cond":  305,  # Track condition (FT=Fast, FM=Firm, GD, MY, SY, SF)
    "distance":    315,  # Distance in yards (negative = turf route?)
    "surface":     325,  # T=Turf, D=Dirt, A=All-Weather
    "num_horses":  345,  # Field size
    "finish_pos":  355,  # Official finish position
    "equipment":   365,  # Equipment (b=blinkers, f=front bandages, etc.)
    "medication":  385,  # Medication (1=on medication, 0=none)
    "comment":     395,  # Brisnet chart comment
    # ── Result context ────────────────────────────────────────────────────
    "winner":      405,  # Winner's name
    "second":      415,  # 2nd place finisher
    "third":       425,  # 3rd place finisher
    "odds":        515,  # Odds at finish (e.g. 14.42 = 14-1)
    "race_type":   535,  # Race type class label
    "claim_price": 545,  # Claiming price (if applicable)
    "purse":       555,  # Purse amount
    # ── Running positions at each call ────────────────────────────────────
    "pos_pp":      565,  # Position at pre-pace call
    "pos_1st":     575,  # Position at 1st call
    "pos_2nd":     585,  # Position at 2nd call
    "pos_str":     595,  # Position at stretch
    "pos_fin":     605,  # Position at finish (unofficial)
    "pos_off_fin": 615,  # Official final position (same as finish_pos)
    # ── Lengths behind leader ─────────────────────────────────────────────
    "len_str":     635,  # Lengths behind at stretch
    "len_fin":     645,  # Lengths behind at finish
    # ── BRIS pace/speed figures ───────────────────────────────────────────
    "bris_speed":  765,  # BRIS Speed Figure  ← was offset 18 in wrong block
    "e1_pace":     775,  # E1 Pace Figure (early pace, first call)
    "e2_pace":     785,  # E2 Pace Figure (second call)
    "late_pace":   855,  # Late Pace Figure
    # ── Fractional / final times (raw seconds) ───────────────────────────
    "frac_1":      875,  # First fraction (e.g. 23.06 sec)
    "frac_2":      895,  # Second fraction
    "frac_3":      915,  # Third fraction
    "final_time":  935,  # Final time in seconds
    # ── Trainer / jockey in that past race ───────────────────────────────
    "past_trainer": 1055,
    "past_jockey":  1065,
}

# ── LOOKUP TABLES ─────────────────────────────────────────────────────────────

SURFACE_MAP = {
    "D": "Dirt",
    "T": "Turf",
    "A": "All-Weather",
    "": "Unknown",
}

RACE_TYPE_MAP = {
    "G1": "Grade 1 Stakes",
    "G2": "Grade 2 Stakes",
    "G3": "Grade 3 Stakes",
    "N":  "Non-Graded Stakes",
    "A":  "Allowance",
    "AO": "Allowance Optional Claiming",
    "C":  "Claiming",
    "CO": "Optional Claiming",
    "M":  "Maiden Special Weight",
    "MC": "Maiden Claiming",
    "S":  "Starter Allowance",
    "T":  "Trials",
}

# Brisnet-provided running style codes (field 209)
BRIS_RUNNING_STYLE_MAP = {
    "E":   "Front Runner",
    "E/P": "Early Presser",
    "P":   "Presser",
    "S":   "Closer",
    "NA":  "Unknown",
    "":    "Unknown",
}
