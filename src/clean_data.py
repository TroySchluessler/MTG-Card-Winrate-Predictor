import json
import re
import pandas as pd

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

# ---------------------------------------------------------------------------
# STEP A: Load and flatten the MTGJSON set file
# ---------------------------------------------------------------------------

with open(f"{RAW_DIR}/SOS.json", "r", encoding="utf-8") as f:
    raw = json.load(f)

cards = raw["data"]["cards"]
mtg_df = pd.DataFrame(cards)

# Drop basic lands — they have no meaningful win rate and no useful text
mtg_df = mtg_df[~mtg_df["supertypes"].apply(lambda s: "Basic" in s)]

# Drop duplicate printings (showcase/borderless variants of the same card).
# Text is identical across printings, so keep the first occurrence of each name.
mtg_df = mtg_df.drop_duplicates(subset=["name", "side"], keep="first")

# --- Handle double-faced ("prepare") cards ---
# These have TWO rows: one with side == 'a', one with side == 'b'.
# We combine them into a single row per card.
double_faced = mtg_df[mtg_df["layout"] == "prepare"].copy()
single_faced = mtg_df[mtg_df["layout"] != "prepare"].copy()

combined_rows = []
for full_name, group in double_faced.groupby("name"):
    side_a = group[group["side"] == "a"]
    side_b = group[group["side"] == "b"]
    if side_a.empty or side_b.empty:
        continue  # skip anything malformed rather than crash

    a = side_a.iloc[0]
    b = side_b.iloc[0]

    combined_rows.append({
        "name": full_name,                              # e.g. "Elite Interceptor // Rejoinder"
        "front_name": full_name.split("//")[0].strip(),  # e.g. "Elite Interceptor" — matches 17lands naming
        "text": f"{a['text']}\n{b['text']}",              # both faces' rules text concatenated
        "manaCost": a.get("manaCost", ""),
        "type": a.get("type", ""),
        "rarity": a.get("rarity", ""),
        "keywords": a.get("keywords", []) if isinstance(a.get("keywords"), list) else [],
    })

double_faced_clean = pd.DataFrame(combined_rows)

single_faced_clean = single_faced.copy()
single_faced_clean["front_name"] = single_faced_clean["name"]  # same as name for normal cards
single_faced_clean = single_faced_clean[
    ["name", "front_name", "text", "manaCost", "type", "rarity", "keywords"]
]

mtg_df = pd.concat([single_faced_clean, double_faced_clean], ignore_index=True)

print(f"MTGJSON cards after cleaning: {len(mtg_df)}")

# ---------------------------------------------------------------------------
# STEP B: Load and clean the 17lands card ratings CSV
# ---------------------------------------------------------------------------

lands_df = pd.read_csv(f"{RAW_DIR}/card-ratings-2026-08-30.csv")

lands_df = lands_df[["Name", "Rarity", "# GIH", "GIH WR"]].copy()
lands_df.columns = ["name", "rarity_17lands", "games_in_hand", "gih_wr"]

# GIH WR arrives as a string like "53.8%" — convert to a float like 0.538
lands_df["gih_wr"] = (
    lands_df["gih_wr"]
    .astype(str)
    .str.rstrip("%")
    .replace("nan", pd.NA)
    .astype(float) / 100
).round(4)

# Drop cards with missing win rate (too few games for 17lands to report)
lands_df = lands_df.dropna(subset=["gih_wr"])

# Optional stricter sample-size filter — uncomment and tune if your win rates
# look noisy in EDA (very low game counts produce unreliable win rates)
# lands_df = lands_df[lands_df["games_in_hand"] >= 200]

print(f"17lands cards after cleaning: {len(lands_df)}")

# ---------------------------------------------------------------------------
# STEP C: Merge on card name
# ---------------------------------------------------------------------------

# Try matching on front_name first (handles double-faced cards),
# falling back to full name for everything else.
df = pd.merge(mtg_df, lands_df, left_on="front_name", right_on="name", how="inner", suffixes=("", "_lands"))

print(f"Merged dataset: {len(df)} cards")

unmatched = set(lands_df["name"]) - set(mtg_df["front_name"])
print(f"Unmatched 17lands cards (likely Mystical Archive/bonus sheet reprints, dropped): {len(unmatched)}")
print(sorted(unmatched)[:10], "...")

# ---------------------------------------------------------------------------
# STEP D: Final structure + save
# ---------------------------------------------------------------------------

final_df = df[["name", "text", "manaCost", "type", "rarity", "keywords", "games_in_hand", "gih_wr"]]
final_df = final_df.rename(columns={"gih_wr": "win_rate"})

final_df.to_csv(f"{PROCESSED_DIR}/strixhaven_clean.csv", index=False)
print(f"\nSaved {len(final_df)} rows to {PROCESSED_DIR}/strixhaven_clean.csv")
print(final_df.head())