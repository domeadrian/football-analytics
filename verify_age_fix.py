"""Verify the age fix works correctly"""
import json, pandas as pd

with open('data/all_players_2526.json', encoding='utf-8') as f:
    data = json.load(f)

df = pd.DataFrame(data)
df.rename(columns={"_leagueName": "league"}, inplace=True)

# Apply the FIXED logic
df["birth_date"] = pd.to_datetime(df["dateBorn"], dayfirst=True, errors="coerce")
df["age"] = pd.to_numeric(df["age"], errors="coerce")
mask = df["age"].isna() & df["birth_date"].notna()
df.loc[mask, "age"] = ((pd.Timestamp.now() - df.loc[mask, "birth_date"]).dt.days / 365.25).round(1)

# Results
total = len(df)
has_age = df["age"].notna().sum()
has_dob = df["birth_date"].notna().sum()
print(f"Total: {total}")
print(f"Has age: {has_age} ({has_age/total*100:.1f}%)")
print(f"Has birth_date parsed: {has_dob} ({has_dob/total*100:.1f}%)")
print(f"Missing age: {df['age'].isna().sum()}")
print(f"Missing birth_date: {df['birth_date'].isna().sum()}")

# Verify known players
for name in ["Daniel Bîrligea", "Darius Olaru", "Mohamed Salah", "Erling Haaland", "Kylian Mbappé"]:
    row = df[df["strPlayer"].str.contains(name, case=False, na=False)]
    if not row.empty:
        r = row.iloc[0]
        print(f"\n  {r['strPlayer']:30s} age={r['age']:>5}  dob={r['dateBorn']:>12}  parsed={r['birth_date']}")
