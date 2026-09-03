import json
import re
import pandas as pd

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"

def clean_one_set(json_path, csv_path, set_code):
    with open(json_path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    cards = raw["data"]["cards"]
    mtg_df = pd.DataFrame(cards)

    # Not every set has double-faced cards, so "side" may not exist as a column at all
    if "side" not in mtg_df.columns:
        mtg_df["side"] = pd.NA

    mtg_df = mtg_df[~mtg_df["supertypes"].apply(lambda s: isinstance(s, list) and "Basic" in s)]
    mtg_df = mtg_df.drop_duplicates(subset=["name", "side"], keep="first")

    double_faced = mtg_df[mtg_df["side"].notna()].copy()
    single_faced = mtg_df[mtg_df["side"].isna()].copy()

    combined_rows = []
    if not double_faced.empty:
        for full_name, group in double_faced.groupby("name"):
            side_a = group[group["side"] == "a"]
            side_b = group[group["side"] == "b"]
            if side_a.empty or side_b.empty:
                continue
            a, b = side_a.iloc[0], side_b.iloc[0]
            combined_rows.append({
                "name": full_name,
                "front_name": full_name.split("//")[0].strip(),
                "text": f"{a['text']}\n{b['text']}",
                "manaCost": a.get("manaCost", ""),
                "type": a.get("type", ""),
                "rarity": a.get("rarity", ""),
            })
    double_faced_clean = pd.DataFrame(combined_rows)

    single_faced_clean = single_faced.copy()
    single_faced_clean["front_name"] = single_faced_clean["name"]
    single_faced_clean = single_faced_clean[["name", "front_name", "text", "manaCost", "type", "rarity"]]

    mtg_df_final = pd.concat([single_faced_clean, double_faced_clean], ignore_index=True)

    lands_df = pd.read_csv(csv_path)
    lands_df = lands_df[["Name", "Rarity", "# GIH", "GIH WR"]].copy()
    lands_df.columns = ["name", "rarity_17lands", "games_in_hand", "gih_wr"]
    lands_df["gih_wr"] = (
        lands_df["gih_wr"].astype(str).str.rstrip("%").replace("nan", pd.NA).astype(float) / 100
    ).round(4)
    lands_df = lands_df.dropna(subset=["gih_wr"])

    merged = pd.merge(mtg_df_final, lands_df, left_on="front_name", right_on="name",
                       how="inner", suffixes=("", "_lands"))
    result = merged[["name", "text", "manaCost", "type", "rarity", "games_in_hand", "gih_wr"]]
    result = result.rename(columns={"gih_wr": "win_rate"})
    result["set_code"] = set_code   # track which set each card came from
    return result

if __name__ == "__main__":
    set_1 = clean_one_set(f"{RAW_DIR}/SOS.json", f"{RAW_DIR}/card-ratings-2026-08-30.csv", "SOS")
    set_2 = clean_one_set(f"{RAW_DIR}/EOE.json", f"{RAW_DIR}/card-ratings-2026-09-03.csv", "EOE")
    set_3 = clean_one_set(f"{RAW_DIR}/ECL.json", f"{RAW_DIR}/card-ratings-2026-09-03 (1).csv", "ECL")
    set_4 = clean_one_set(f"{RAW_DIR}/FDN.json", f"{RAW_DIR}/card-ratings-2026-09-03 (2).csv", "FDN")

    combined_df = pd.concat([set_1, set_2, set_3, set_4], ignore_index=True)
    combined_df.to_csv(f"{PROCESSED_DIR}/multi_set_clean.csv", index=False)
    print(f"Combined dataset: {len(combined_df)} cards across {combined_df['set_code'].nunique()} sets")