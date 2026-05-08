"""
Fix all standings data files with real data from Wikipedia (as of April 16, 2026).
Sources:
  - https://en.wikipedia.org/wiki/2025-26_Liga_I
  - https://en.wikipedia.org/wiki/2025-26_Liga_II
  - https://en.wikipedia.org/wiki/2025-26_Danish_Superliga
  - https://en.wikipedia.org/wiki/2025-26_Belgian_Pro_League
"""
import json, os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def make_entry(rank, team, pld, w, d, l, gf, ga, league_id, source="wikipedia"):
    return {
        "intRank": rank,
        "strTeam": team,
        "idLeague": str(league_id),
        "intPlayed": pld,
        "intWin": w,
        "intDraw": d,
        "intLoss": l,
        "intGoalsFor": gf,
        "intGoalsAgainst": ga,
        "intGoalDifference": gf - ga,
        "intPoints": w * 3 + d,
        "source": source,
    }

def make_entry_pts(rank, team, pld, w, d, l, gf, ga, pts, league_id, source="wikipedia"):
    """For cases where points aren't simply 3*W+D (e.g. halved points carried over)."""
    return {
        "intRank": rank,
        "strTeam": team,
        "idLeague": str(league_id),
        "intPlayed": pld,
        "intWin": w,
        "intDraw": d,
        "intLoss": l,
        "intGoalsFor": gf,
        "intGoalsAgainst": ga,
        "intGoalDifference": gf - ga,
        "intPoints": pts,
        "source": source,
    }

def save(league_id, league_name, table):
    path = os.path.join(DATA_DIR, f"full_standings_2526_{league_id}.json")
    data = {
        "league_id": league_id,
        "league_name": league_name,
        "season": "2025-2026",
        "source": "wikipedia_april_2026",
        "table": table,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Wrote {path} ({len(table)} teams)")

# =========================================================================
# ROMANIAN LIGA I (id=4691) — Regular season final table (30 rounds)
# Source: https://en.wikipedia.org/wiki/2025-26_Liga_I#League_table
# =========================================================================
print("=== Romanian Liga I ===")
liga1 = [
    make_entry( 1, "Universitatea Craiova",      30, 17, 9, 4, 53, 27, 4691),
    make_entry( 2, "Rapid București",             30, 16, 8, 6, 47, 30, 4691),
    make_entry( 3, "Universitatea Cluj",          30, 16, 6, 8, 48, 27, 4691),
    make_entry( 4, "CFR Cluj",                    30, 15, 8, 7, 49, 40, 4691),
    make_entry( 5, "Dinamo București",            30, 14,10, 6, 42, 28, 4691),
    make_entry( 6, "Argeș Pitești",               30, 15, 5,10, 37, 28, 4691),
    make_entry( 7, "FCSB",                        30, 13, 7,10, 48, 40, 4691),
    make_entry( 8, "UTA Arad",                    30, 11,10, 9, 39, 44, 4691),
    make_entry( 9, "Botoșani",                    30, 11, 9,10, 37, 29, 4691),
    make_entry(10, "Oțelul Galați",               30, 11, 8,11, 39, 32, 4691),
    make_entry(11, "Farul Constanța",             30, 10, 7,13, 39, 37, 4691),
    make_entry(12, "Petrolul Ploiești",           30,  7,11,12, 24, 31, 4691),
    make_entry(13, "Csíkszereda Miercurea Ciuc",  30,  8, 8,14, 30, 58, 4691),
    make_entry(14, "Unirea Slobozia",             30,  7, 4,19, 27, 46, 4691),
    make_entry(15, "Hermannstadt",                30,  5, 8,17, 29, 50, 4691),
    make_entry(16, "Metaloglobus București",      30,  2, 6,22, 25, 66, 4691),
]
save(4691, "Romanian Liga I", liga1)

# =========================================================================
# ROMANIAN LIGA II (id=4665) — Regular season final table (21 rounds, 22 teams)
# Source: https://en.wikipedia.org/wiki/2025-26_Liga_II#League_table
# =========================================================================
print("=== Romanian Liga II ===")
liga2 = [
    make_entry( 1, "Corvinul Hunedoara",          21, 16, 5, 0, 37, 13, 4665),
    make_entry( 2, "Sepsi OSK Sfântu Gheorghe",   21, 13, 5, 3, 34, 18, 4665),
    make_entry( 3, "Chindia Târgoviște",           21, 12, 3, 6, 38, 20, 4665),
    make_entry( 4, "Bihor Oradea",                21, 12, 3, 6, 40, 24, 4665),
    make_entry( 5, "Voluntari",                   21, 11, 6, 4, 30, 16, 4665),
    make_entry( 6, "Steaua București",            21, 12, 3, 6, 36, 27, 4665),
    make_entry( 7, "ASA Târgu Mureș",             21, 11, 4, 6, 37, 22, 4665),
    make_entry( 8, "Reșița",                      21, 10, 3, 8, 35, 29, 4665),
    make_entry( 9, "Bacău",                       21,  9, 6, 6, 28, 26, 4665),
    make_entry(10, "Metalul Buzău",               21, 10, 2, 9, 33, 26, 4665),
    make_entry(11, "Politehnica Iași",             21,  9, 4, 8, 25, 22, 4665),
    make_entry(12, "Afumați",                     21,  9, 3, 9, 30, 26, 4665),
    make_entry(13, "Concordia Chiajna",           21,  8, 3,10, 29, 24, 4665),
    make_entry(14, "Gloria Bistrița",             21,  7, 5, 9, 29, 29, 4665),
    make_entry(15, "Slatina",                     21,  7, 5, 9, 27, 28, 4665),
    make_entry(16, "Dumbrăvița",                  21,  7, 4,10, 25, 33, 4665),
    make_entry(17, "1599 Șelimbăr",               21,  5, 5,11, 27, 32, 4665),
    make_entry_pts(18, "Ceahlăul Piatra Neamț",   21,  5, 3,13, 20, 43, 18, 4665),  # 2pts deducted then restored
    make_entry(19, "CS Dinamo București",          21,  3, 7,11, 19, 35, 4665),
    make_entry(20, "Tunari",                      21,  3, 7,11, 19, 36, 4665),
    make_entry(21, "Olimpia Satu Mare",           21,  4, 2,15, 19, 45, 4665),
    make_entry(22, "Câmpulung Muscel",            21,  2, 4,15, 10, 53, 4665),
]
save(4665, "Romanian Liga II", liga2)

# =========================================================================
# DANISH SUPERLIGA (id=4340) — Regular season final table (22 rounds, 12 teams)
# Source: https://en.wikipedia.org/wiki/2025-26_Danish_Superliga#League_table
# =========================================================================
print("=== Danish Superliga ===")
danish = [
    make_entry( 1, "AGF Aarhus",      22, 15, 5, 2, 46, 23, 4340),
    make_entry( 2, "FC Midtjylland",   22, 13, 7, 2, 58, 23, 4340),
    make_entry( 3, "Sønderjyske",      22, 10, 6, 6, 34, 28, 4340),
    make_entry( 4, "Brøndby",          22, 10, 4, 8, 31, 22, 4340),
    make_entry( 5, "Viborg",           22, 10, 3, 9, 37, 35, 4340),
    make_entry( 6, "FC Nordsjælland",  22, 10, 1,11, 37, 39, 4340),
    make_entry( 7, "FC Copenhagen",    22,  8, 5, 9, 35, 34, 4340),
    make_entry( 8, "OB",               22,  7, 6, 9, 36, 46, 4340),
    make_entry( 9, "Randers",          22,  7, 5,10, 22, 27, 4340),
    make_entry(10, "Fredericia",       22,  7, 3,12, 30, 49, 4340),
    make_entry(11, "Silkeborg",        22,  5, 4,13, 24, 45, 4340),
    make_entry(12, "Vejle",            22,  3, 5,14, 26, 45, 4340),
]
save(4340, "Danish Superliga", danish)

# =========================================================================
# BELGIAN PRO LEAGUE (id=4338) — Regular season final table (30 rounds, 16 teams)
# Source: https://en.wikipedia.org/wiki/2025-26_Belgian_Pro_League#League_table
# =========================================================================
print("=== Belgian Pro League ===")
belgian = [
    make_entry( 1, "Union SG",        30, 19, 9, 2, 50, 17, 4338),
    make_entry( 2, "Club Brugge",     30, 20, 3, 7, 59, 36, 4338),
    make_entry( 3, "Sint-Truiden",    30, 18, 3, 9, 47, 35, 4338),
    make_entry( 4, "Gent",            30, 13, 6,11, 49, 43, 4338),
    make_entry( 5, "Mechelen",        30, 12, 9, 9, 39, 37, 4338),
    make_entry( 6, "Anderlecht",      30, 12, 8,10, 43, 39, 4338),
    make_entry( 7, "Genk",            30, 11, 9,10, 46, 47, 4338),
    make_entry( 8, "Standard Liège",  30, 11, 7,12, 27, 35, 4338),
    make_entry( 9, "Westerlo",        30, 10, 9,11, 36, 40, 4338),
    make_entry(10, "Antwerp",         30,  9, 8,13, 31, 32, 4338),
    make_entry(11, "Charleroi",       30,  9, 7,14, 38, 42, 4338),
    make_entry(12, "OH Leuven",       30,  9, 7,14, 32, 43, 4338),
    make_entry(13, "Zulte Waregem",   30,  8, 8,14, 38, 47, 4338),
    make_entry(14, "Cercle Brugge",   30,  7,10,13, 39, 47, 4338),
    make_entry(15, "La Louvière",     30,  6,13,11, 30, 37, 4338),
    make_entry(16, "Dender EH",       30,  3,10,17, 24, 51, 4338),
]
save(4338, "Belgian Pro League", belgian)

print("\nDone! All standings files updated with real Wikipedia data.")
