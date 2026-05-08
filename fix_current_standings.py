"""
Write CURRENT phase standings — playoff/playout tables with actual accumulated points.
Data from Wikipedia & Flashscore as of April 16, 2026.

Liga I: Playoff + Playout phase (4 rounds played of 10/9)
Liga II: Promotion Playoff (4 rounds) + Playout Groups A & B (3 rounds)
"""
import json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def e(rank, team, pld, w, d, l, gf, ga, pts, lid, group=""):
    """Create a standings entry with explicit points (halved carryover + phase results)."""
    return {
        "intRank": rank,
        "strTeam": team,
        "idLeague": str(lid),
        "intPlayed": pld,
        "intWin": w,
        "intDraw": d,
        "intLoss": l,
        "intGoalsFor": gf,
        "intGoalsAgainst": ga,
        "intGoalDifference": gf - ga,
        "intPoints": pts,
        "source": "wikipedia_flashscore_april_2026",
        "group": group,
    }

def save(lid, name, table, phase="regular_season", phase_desc=""):
    path = os.path.join(DATA_DIR, f"full_standings_2526_{lid}.json")
    data = {
        "league_id": lid,
        "league_name": name,
        "season": "2025-2026",
        "source": "wikipedia_flashscore_april_2026",
        "phase": phase,
        "phase_description": phase_desc,
        "no_resort": True if phase != "regular_season" else False,
        "table": table,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  {path} => {len(table)} teams (phase={phase})")


# =========================================================================
# ROMANIAN LIGA I (4691) — PLAYOFF + PLAYOUT PHASE (4 rounds played)
# Source: Wikipedia 2025-26 Liga I — Play-off table & Play-out table
# Points = halved regular season + phase results
# Pld/W/D/L/GF/GA = current phase only
# =========================================================================
print("=== Romanian Liga I (playoff/playout active) ===")
liga1 = [
    # Championship Playoff (Top 6, points halved + 4 playoff rounds played)
    e( 1, "Universitatea Cluj",          4, 4, 0, 0,  9,  2, 39, 4691, "playoff"),
    e( 2, "Universitatea Craiova",       4, 2, 0, 2,  3,  5, 36, 4691, "playoff"),
    e( 3, "Rapid București",             4, 1, 1, 2,  4,  5, 32, 4691, "playoff"),
    e( 4, "CFR Cluj",                    4, 1, 1, 2,  3,  5, 31, 4691, "playoff"),
    e( 5, "Argeș Pitești",              4, 1, 2, 1,  2,  2, 30, 4691, "playoff"),
    e( 6, "Dinamo București",            4, 0, 2, 2,  4,  6, 28, 4691, "playoff"),
    # Relegation Playout (Bottom 10, points halved + 4 playout rounds played)
    e( 7, "UTA Arad",                    4, 3, 0, 1, 11,  5, 31, 4691, "playout"),
    e( 8, "FCSB",                        4, 2, 1, 1,  7,  3, 30, 4691, "playout"),
    e( 9, "Botoșani",                    4, 2, 0, 2,  7, 10, 27, 4691, "playout"),
    e(10, "Oțelul Galați",              4, 1, 0, 3,  5,  9, 24, 4691, "playout"),
    e(11, "Csíkszereda Miercurea Ciuc",  4, 2, 1, 1,  5,  5, 23, 4691, "playout"),
    e(12, "Farul Constanța",            4, 1, 1, 2,  3,  3, 23, 4691, "playout"),
    e(13, "Petrolul Ploiești",          4, 2, 0, 2,  4,  4, 22, 4691, "playout"),
    e(14, "Unirea Slobozia",             4, 2, 0, 2,  6,  6, 19, 4691, "playout"),
    e(15, "Hermannstadt",                4, 2, 0, 2,  6,  5, 18, 4691, "playout"),
    e(16, "Metaloglobus București",      4, 1, 1, 2,  2,  6, 10, 4691, "playout"),
]
save(4691, "Romanian Liga I", liga1,
     phase="playoff_playout_active",
     phase_desc="Playoff (4/10 rounds) + Playout (4/9 rounds) — points halved from regular season")


# =========================================================================
# ROMANIAN LIGA II (4665) — PROMOTION PLAYOFF + PLAYOUT GROUPS
# Source: Wikipedia 2025-26 Liga II — Play-off (4 rounds) + Play-out A/B (3 rounds)
# Points = full RS carryover + phase results
# =========================================================================
print("=== Romanian Liga II (playoff/playout active) ===")
liga2 = [
    # Promotion Playoff (Top 6, all RS points kept + 4 playoff rounds)
    e( 1, "Corvinul Hunedoara",          4, 2, 0, 2,  3,  2, 59, 4665, "playoff"),
    e( 2, "Sepsi OSK Sfântu Gheorghe",   4, 3, 1, 0,  7,  1, 54, 4665, "playoff"),
    e( 3, "Voluntari",                   4, 3, 1, 0,  9,  2, 49, 4665, "playoff"),
    e( 4, "Steaua București",            4, 2, 0, 2,  5,  4, 45, 4665, "playoff"),
    e( 5, "Bihor Oradea",               4, 1, 0, 3,  4,  9, 42, 4665, "playoff"),
    e( 6, "Chindia Târgoviște",          4, 0, 0, 4,  2, 12, 39, 4665, "playoff"),
    # Playout Group A (8 teams, all RS points + 3 playout rounds)
    e( 7, "ASA Târgu Mureș",             3, 2, 0, 1,  8,  5, 43, 4665, "playout_a"),
    e( 8, "Metalul Buzău",               3, 3, 0, 0,  9,  3, 41, 4665, "playout_a"),
    e( 9, "Politehnica Iași",            3, 2, 0, 1,  4,  1, 37, 4665, "playout_a"),
    e(10, "Slatina",                     3, 2, 1, 0,  7,  2, 33, 4665, "playout_a"),
    e(11, "Gloria Bistrița",             3, 1, 0, 2,  4,  4, 29, 4665, "playout_a"),
    e(12, "Ceahlăul Piatra Neamț",      3, 0, 1, 2,  1,  7, 19, 4665, "playout_a"),
    e(13, "CS Dinamo București",          3, 1, 0, 2,  4,  5, 19, 4665, "playout_a"),
    e(14, "Câmpulung Muscel",            3, 0, 0, 3,  1, 11, 10, 4665, "playout_a"),
    # Playout Group B (8 teams, all RS points + 3 playout rounds)
    e(15, "Reșița",                      3, 2, 1, 0,  4,  1, 40, 4665, "playout_b"),
    e(16, "Bacău",                       3, 1, 0, 2,  2,  4, 36, 4665, "playout_b"),
    e(17, "Concordia Chiajna",           3, 2, 1, 0,  4,  1, 34, 4665, "playout_b"),
    e(18, "Afumați",                     3, 1, 1, 1,  5,  2, 34, 4665, "playout_b"),
    e(19, "Dumbrăvița",                  3, 0, 1, 2,  2,  4, 26, 4665, "playout_b"),
    e(20, "1599 Șelimbăr",              3, 1, 1, 1,  1,  2, 24, 4665, "playout_b"),
    e(21, "Olimpia Satu Mare",           3, 2, 0, 1,  6,  5, 20, 4665, "playout_b"),
    e(22, "Tunari",                      3, 0, 1, 2,  1,  6, 17, 4665, "playout_b"),
]
save(4665, "Romanian Liga II", liga2,
     phase="playoff_playout_active",
     phase_desc="Promotion Playoff (4/10 rounds) + Playout Groups A & B (3/7 rounds) — all RS points carried over")


# =========================================================================
# DANISH SUPERLIGA (4340) — CHAMPIONSHIP + RELEGATION ROUND (active)
# Source: Wikipedia 2025-26 Danish Superliga
# Points and goals carried over in full from regular season
# =========================================================================
print("=== Danish Superliga (championship/relegation round active) ===")
danish = [
    # Championship Round (Top 6, RS points + results carried over)
    e( 1, "AGF Aarhus",       26, 16, 8, 2, 50, 26, 56, 4340, "championship"),
    e( 2, "FC Midtjylland",   26, 14, 9, 3, 63, 28, 51, 4340, "championship"),
    e( 3, "FC Nordsjælland",  26, 13, 2,11, 43, 41, 41, 4340, "championship"),
    e( 4, "Viborg",           26, 12, 4,10, 42, 38, 40, 4340, "championship"),
    e( 5, "Sønderjyske",      26, 10, 8, 8, 37, 35, 38, 4340, "championship"),
    e( 6, "Brøndby",          26, 10, 5,11, 33, 27, 35, 4340, "championship"),
    # Relegation Round (Bottom 6, RS points + results carried over)
    e( 7, "FC Copenhagen",    26, 10, 5,11, 46, 39, 35, 4340, "relegation"),
    e( 8, "OB",               26,  9, 7,10, 41, 51, 34, 4340, "relegation"),
    e( 9, "Randers",          26,  8, 6,12, 27, 33, 30, 4340, "relegation"),
    e(10, "Fredericia",       26,  8, 4,14, 34, 56, 28, 4340, "relegation"),
    e(11, "Silkeborg",        26,  7, 5,14, 31, 54, 26, 4340, "relegation"),
    e(12, "Vejle",            26,  3, 9,14, 31, 50, 18, 4340, "relegation"),
]
save(4340, "Danish Superliga", danish,
     phase="championship_relegation_active",
     phase_desc="Championship Round + Relegation Round (4/10 rounds played) — all points carried over")


# =========================================================================
# BELGIAN PRO LEAGUE (4338) — PLAYOFFS ACTIVE
# Source: Wikipedia 2025-26 Belgian Pro League
# Champions' PO (points halved), Europe PO (points halved), Relegation PO (full points)
# =========================================================================
print("=== Belgian Pro League (playoffs active) ===")
belgian = [
    # Champions' Playoff (Top 6, RS points halved + 2 PO rounds)
    e( 1, "Union SG",         2, 2, 0, 0,  2,  0, 39, 4338, "champions_po"),
    e( 2, "Club Brugge",      2, 2, 0, 0,  6,  3, 38, 4338, "champions_po"),
    e( 3, "Sint-Truiden",     2, 0, 0, 2,  1,  3, 29, 4338, "champions_po"),
    e( 4, "Anderlecht",       2, 1, 0, 1,  5,  5, 25, 4338, "champions_po"),
    e( 5, "Gent",             2, 0, 1, 1,  2,  4, 24, 4338, "champions_po"),
    e( 6, "Mechelen",         2, 0, 1, 1,  1,  2, 24, 4338, "champions_po"),
    # Europe Playoff (7th-12th, RS points halved + 2 PO rounds)
    e( 7, "Westerlo",         2, 2, 0, 0,  4,  1, 26, 4338, "europe_po"),
    e( 8, "Genk",             2, 1, 1, 0,  2,  1, 25, 4338, "europe_po"),
    e( 9, "Standard Liège",   2, 1, 0, 1,  4,  3, 23, 4338, "europe_po"),
    e(10, "Charleroi",        2, 1, 0, 1,  2,  3, 20, 4338, "europe_po"),
    e(11, "OH Leuven",        2, 0, 1, 1,  1,  3, 18, 4338, "europe_po"),
    e(12, "Antwerp",          2, 0, 0, 2,  2,  4, 18, 4338, "europe_po"),
    # Relegation Playoff (13th-16th, full RS points + 2 PO rounds)
    e(13, "Zulte Waregem",    2, 1, 1, 0,  4,  3, 36, 4338, "relegation_po"),
    e(14, "Cercle Brugge",    2, 1, 1, 0,  5,  2, 35, 4338, "relegation_po"),
    e(15, "La Louvière",      2, 0, 0, 2,  0,  4, 31, 4338, "relegation_po"),
    e(16, "Dender EH",        2, 1, 0, 1,  2,  2, 22, 4338, "relegation_po"),
]
save(4338, "Belgian Pro League", belgian,
     phase="playoffs_active",
     phase_desc="Champions' PO (2/10), Europe PO (2/10), Relegation PO (2/6) — points halved for top 12, full for bottom 4")


print("\nAll standings updated with CURRENT phase data!")
