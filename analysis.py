"""
RPC #21 — Decoding the 2026 Tamil Nadu Assembly Election
Analysis Notebook (Python Script)
Author: Nandhini
Research Questions Answered: Q2 (Flip), Q3 (Vote Share), Q6 (Margins)
Bonus: Q4 (Reserved Seats)
Data Source: ECI live results portal — tn_2026_results.csv, tn_2021_results.csv
Note: 2026 turnout column intentionally blank in CSV (Form-20 not released at data prep time)
"""

import pandas as pd
import os

BASE = os.path.join(os.path.dirname(__file__), "input_files_for_participants_rpc")
OUT  = os.path.join(os.path.dirname(__file__), "analysis_outputs")
os.makedirs(OUT, exist_ok=True)

# ── LOAD ─────────────────────────────────────────────────────────────
df26 = pd.read_csv(os.path.join(BASE, "data/tn_2026_results.csv"))
df21 = pd.read_csv(os.path.join(BASE, "data/tn_2021_results.csv"))
master = pd.read_csv(os.path.join(BASE, "data/constituency_master.csv"))

for df in [df26, df21]:
    df["votes"] = pd.to_numeric(df["votes"], errors="coerce").fillna(0).astype(int)

print("✅ Data loaded")
print(f"   2026: {len(df26):,} rows | 2021: {len(df21):,} rows | Master: {len(master)} constituencies")

# ── HELPER: COMPUTE WINNERS ──────────────────────────────────────────
def get_winners(df):
    rows = []
    for ac, grp in df.groupby("ac_number"):
        s = grp.sort_values("votes", ascending=False).reset_index(drop=True)
        if len(s) < 2: continue
        total = int(s["votes"].sum())
        rows.append({
            "ac_number": int(ac),
            "constituency": s.iloc[0]["constituency"],
            "winner_party": s.iloc[0]["party"],
            "winner_votes": int(s.iloc[0]["votes"]),
            "runner_up_party": s.iloc[1]["party"],
            "runner_up_votes": int(s.iloc[1]["votes"]),
            "margin": int(s.iloc[0]["votes"]) - int(s.iloc[1]["votes"]),
            "total_valid_votes": total,
            "winner_vote_share": round(s.iloc[0]["votes"] / total * 100, 2),
            "num_candidates": len(s),
            "region": s.iloc[0]["region"],
            "reserved": s.iloc[0]["reserved"],
        })
    return pd.DataFrame(rows).sort_values("ac_number").reset_index(drop=True)

w26 = get_winners(df26)
w21 = get_winners(df21)

# ── PARTY SEATS OVERVIEW ─────────────────────────────────────────────
seats26 = w26["winner_party"].value_counts().reset_index()
seats26.columns = ["party", "seats_2026"]
seats21 = w21["winner_party"].value_counts().reset_index()
seats21.columns = ["party", "seats_2021"]
seat_compare = seats26.merge(seats21, on="party", how="outer").fillna(0)
seat_compare[["seats_2021","seats_2026"]] = seat_compare[["seats_2021","seats_2026"]].astype(int)
seat_compare["change"] = seat_compare["seats_2026"] - seat_compare["seats_2021"]
seat_compare = seat_compare.sort_values("seats_2026", ascending=False)
seat_compare.to_csv(os.path.join(OUT, "01_seat_comparison.csv"), index=False)

print("\n📊 SEAT COMPARISON 2021 → 2026:")
print(seat_compare.head(10).to_string(index=False))

# ── VOTE SHARE OVERALL ────────────────────────────────────────────────
def vote_share_overall(df, year):
    total = df["votes"].sum()
    vs = df.groupby("party")["votes"].sum()
    vs = (vs / total * 100).round(2).sort_values(ascending=False).reset_index()
    vs.columns = ["party", f"vote_share_{year}"]
    return vs

vs26 = vote_share_overall(df26, 2026)
vs21 = vote_share_overall(df21, 2021)
vs_all = vs26.merge(vs21, on="party", how="outer").fillna(0)
vs_all["change"] = (vs_all["vote_share_2026"] - vs_all["vote_share_2021"]).round(2)
vs_all = vs_all.sort_values("vote_share_2026", ascending=False)
vs_all.to_csv(os.path.join(OUT, "02_vote_share_overall.csv"), index=False)

print("\n📊 VOTE SHARE OVERALL:")
print(vs_all.head(8).to_string(index=False))

# ════════════════════════════════════════════════════════════════════
# RESEARCH Q2: THE FLIP STORY
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("RESEARCH Q2: THE FLIP STORY")
print("="*60)

flip = w26.merge(w21[["ac_number","winner_party","margin"]], on="ac_number",
                 suffixes=("_2026","_2021"))
flip["flipped"] = flip["winner_party_2026"] != flip["winner_party_2021"]
flip = flip.merge(master[["ac_number","district"]], on="ac_number", how="left")

print(f"\nTotal seats FLIPPED: {flip['flipped'].sum()} / {len(flip)} ({flip['flipped'].mean()*100:.0f}%)")
print(f"Total seats HELD:    {(~flip['flipped']).sum()} / {len(flip)}")

# Sankey data
sankey = flip.groupby(["winner_party_2021","winner_party_2026"]).size().reset_index(name="seats")
sankey = sankey.sort_values("seats", ascending=False)
sankey.to_csv(os.path.join(OUT, "03_sankey_flip_data.csv"), index=False)

print("\nTop seat flows (2021 → 2026):")
print(sankey.head(12).to_string(index=False))

# TVK gains
tvk_gains = flip[flip["flipped"] & (flip["winner_party_2026"]=="TVK")].groupby("winner_party_2021").size().sort_values(ascending=False)
print(f"\nTVK gained {len(flip[flip['winner_party_2026']=='TVK'])} seats. Taken from:")
print(tvk_gains.to_string())

# Flip by region
flip_by_region = flip[flip["flipped"]].groupby(["region","winner_party_2026"]).size().reset_index(name="count")
flip_by_region.to_csv(os.path.join(OUT, "04_flips_by_region.csv"), index=False)

print("\nFlipped seats by region:")
print(flip.groupby("region")["flipped"].agg(["sum","count"]).rename(columns={"sum":"flipped","count":"total"}).to_string())

# ════════════════════════════════════════════════════════════════════
# RESEARCH Q3: THE VOTE SHARE STORY
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("RESEARCH Q3: THE VOTE SHARE STORY")
print("="*60)

def vs_by_region(df):
    total_by_region = df.groupby("region")["votes"].sum().reset_index().rename(columns={"votes":"total"})
    by_rp = df.groupby(["region","party"])["votes"].sum().reset_index()
    m = by_rp.merge(total_by_region, on="region")
    m["pct"] = (m["votes"] / m["total"] * 100).round(2)
    return m

vsr26 = vs_by_region(df26)
vsr21 = vs_by_region(df21)

main_parties = ["TVK","DMK","AIADMK","INC","NTK"]
vsr_pivot26 = vsr26[vsr26["party"].isin(main_parties)].pivot_table(index="region",columns="party",values="pct",fill_value=0)
vsr_pivot21 = vsr21[vsr21["party"].isin(main_parties)].pivot_table(index="region",columns="party",values="pct",fill_value=0)

print("\nVote share by region (2026):")
print(vsr_pivot26.round(1).to_string())
print("\nVote share by region (2021):")
print(vsr_pivot21.round(1).to_string())

# Where TVK votes came from
tvk_vs = vs_all[vs_all["party"]=="TVK"]["vote_share_2026"].values[0]
dmk_drop = abs(vs_all[vs_all["party"]=="DMK"]["change"].values[0])
aia_drop = abs(vs_all[vs_all["party"]=="AIADMK"]["change"].values[0])
ntk_drop = abs(vs_all[vs_all["party"]=="NTK"]["change"].values[0])
mnm_2021 = vs_all[vs_all["party"]=="MNM"]["vote_share_2021"].values[0] if "MNM" in vs_all["party"].values else 0

print(f"\nTVK vote share gained: {tvk_vs:.1f}%")
print(f"DMK drop: {dmk_drop:.1f}%")
print(f"AIADMK drop: {aia_drop:.1f}%")
print(f"NTK drop: {ntk_drop:.1f}%")
print(f"MNM (dissolved): {mnm_2021:.1f}%")
print(f"Accounted for: {dmk_drop+aia_drop+ntk_drop+mnm_2021:.1f}% of the {tvk_vs:.1f}% TVK gained")

# Regional vote share comparison
regional_vs = pd.DataFrame({
    "TVK_2026": vsr_pivot26.get("TVK",pd.Series(dtype=float)),
    "DMK_2026": vsr_pivot26.get("DMK",pd.Series(dtype=float)),
    "DMK_2021": vsr_pivot21.get("DMK",pd.Series(dtype=float)),
    "AIADMK_2026": vsr_pivot26.get("AIADMK",pd.Series(dtype=float)),
    "AIADMK_2021": vsr_pivot21.get("AIADMK",pd.Series(dtype=float)),
})
regional_vs["DMK_drop"] = (regional_vs["DMK_2021"] - regional_vs["DMK_2026"]).round(1)
regional_vs["AIADMK_drop"] = (regional_vs["AIADMK_2021"] - regional_vs["AIADMK_2026"]).round(1)
regional_vs.to_csv(os.path.join(OUT, "05_regional_vote_share.csv"))
print("\nRegional vote share shifts:")
print(regional_vs[["TVK_2026","DMK_drop","AIADMK_drop"]].round(1).to_string())

# ════════════════════════════════════════════════════════════════════
# RESEARCH Q6: THE MARGIN OF VICTORY STORY
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("RESEARCH Q6: THE MARGIN OF VICTORY STORY")
print("="*60)

for year, w in [(2021, w21), (2026, w26)]:
    over50 = (w["winner_vote_share"] >= 50).sum()
    under35 = (w["winner_vote_share"] < 35).sum()
    print(f"\n{year}:")
    print(f"  Average margin:           {w['margin'].mean():>8,.0f} votes")
    print(f"  Median margin:            {w['margin'].median():>8,.0f} votes")
    print(f"  Seats won with >50% share:{over50:>4}")
    print(f"  Seats won with <35% share:{under35:>4}")
    print(f"  Smallest margin:          {w['margin'].min():>8,} ({w.loc[w['margin'].idxmin(),'constituency']})")
    print(f"  Largest margin:           {w['margin'].max():>8,} ({w.loc[w['margin'].idxmax(),'constituency']})")

# Margin comparison
mc = w26[["ac_number","constituency","winner_party","margin","winner_vote_share","region","reserved"]].merge(
     w21[["ac_number","margin","winner_vote_share"]].rename(columns={"margin":"margin_2021","winner_vote_share":"vs_2021"}),
     on="ac_number", how="left")
mc.to_csv(os.path.join(OUT, "06_margin_comparison.csv"), index=False)

# ════════════════════════════════════════════════════════════════════
# BONUS Q4: RESERVED SEAT STORY
# ════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("BONUS Q4: RESERVED SEAT STORY")
print("="*60)

print("\n2021 Seat counts by reservation category:")
print(w21.groupby(["reserved","winner_party"]).size().unstack(fill_value=0).to_string())
print("\n2026 Seat counts by reservation category:")
print(w26.groupby(["reserved","winner_party"]).size().unstack(fill_value=0).to_string())

sc26 = w26[w26["reserved"]=="SC"]["winner_party"].value_counts()
sc21 = w21[w21["reserved"]=="SC"]["winner_party"].value_counts()
sc_comp = pd.DataFrame({"seats_2021":sc21,"seats_2026":sc26}).fillna(0).astype(int)
sc_comp["change"] = sc_comp["seats_2026"] - sc_comp["seats_2021"]
sc_comp.to_csv(os.path.join(OUT, "07_reserved_seat_analysis.csv"))

tvk_sc_rate = len(w26[(w26["winner_party"]=="TVK")&(w26["reserved"]=="SC")]) / 44 * 100
tvk_gen_rate = len(w26[(w26["winner_party"]=="TVK")&(w26["reserved"]=="GEN")]) / 188 * 100
print(f"\nTVK win rate — SC seats: {tvk_sc_rate:.1f}%  |  GEN seats: {tvk_gen_rate:.1f}%")
print(f"DMK SC seats 2021→2026: {sc21.get('DMK',0)} → {sc26.get('DMK',0)}")
print(f"AIADMK SC seats 2021→2026: {sc21.get('AIADMK',0)} → {sc26.get('AIADMK',0)}")

# ── DATA LIMITATION NOTE ─────────────────────────────────────────────
print("\n" + "="*60)
print("⚠ DATA LIMITATIONS")
print("="*60)
print("1. 2026 turnout column is blank in CSV (ECI Form-20 not released at time of data prep)")
print("   For turnout analysis, source from: results.eci.gov.in/ResultAcGenMay2026")
print(f"   State average turnout per ECI: 85.14% (highest ever for TN assembly election)")
print("2. CSV is live portal data — minor discrepancies vs final audited results possible")
print("3. Causal claims are not possible from this data alone (e.g., why votes shifted)")
print("4. Census demographic data not used (only for boundaries, not voter demographics)")

print("\n✅ Analysis complete. All outputs saved to analysis_outputs/")
print("\nFiles generated:")
for f in sorted(os.listdir(OUT)):
    if f.endswith(".csv"):
        print(f"  • {f}")
