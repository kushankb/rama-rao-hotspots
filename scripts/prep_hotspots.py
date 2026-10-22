"""
Build scripts/data.json for the hotspot explorer from the CRVA pipeline outputs.

Run from the CRVATool folder (after 09, 10 and 11 in data-pipeline/scripts):
  conda run -n ml_trade python /path/to/rama-rao-hotspots/scripts/prep_hotspots.py
"""
import json
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

MI = Path("data-pipeline/model_indicators")
OUT = Path(__file__).parent / "data.json"
WINDOWS = ["2047", "2050", "2100"]
COMPS = ["annual_rain", "june_rain", "july_rain", "rainy_days", "tmax", "tmin", "hot_days", "cold_days", "frost",
         "drought", "dry_spells", "p99_rain", "events_100mm", "rx1_pct", "rx3_pct"]
WEIGHTS = {"annual_rain": 10, "june_rain": 5, "july_rain": 15, "rainy_days": 5, "tmax": 6, "tmin": 6, "hot_days": 5,
           "cold_days": 3, "frost": 2, "drought": 12, "dry_spells": 11, "p99_rain": 5, "events_100mm": 5, "rx1_pct": 5, "rx3_pct": 5}
SIGN = {k: (-1 if k in ("annual_rain", "june_rain", "july_rain", "rainy_days") else 1) for k in COMPS}
THRESH = {"annual_rain": 10, "june_rain": 10, "july_rain": 10, "rainy_days": 10, "tmax": 1.0, "tmin": 1.0, "hot_days": 5,
          "cold_days": 2, "frost": 5, "drought": 5, "dry_spells": 1.0, "p99_rain": 5.0, "events_100mm": 0.5, "rx1_pct": 10, "rx3_pct": 10}
ATLAS_CATS = ["More favourable", "Moderately favourable", "No hazard", "Moderately unfavourable", "More unfavourable"]


def rnd(c):
    if isinstance(c[0], (float, int)):
        return [round(c[0], 3), round(c[1], 3)]
    return [rnd(x) for x in c]


def r(v, n=3):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else round(float(v), n)


def abs_class(share):
    if share is None or np.isnan(share):
        return None
    return "None" if share <= 0 else "High" if share > 40 else "Moderate" if share > 20 else "Low"


g = gpd.read_file("web/public/data/india_districts.geojson")
g["geometry"] = g.geometry.simplify(0.03, preserve_topology=True)
stats = json.load(open("web/public/data/crva_stats.json"))
keep = [row for _, row in g.iterrows() if row.geometry is not None and stats.get(f"district:{row.district_id}", {}).get("climate_hazard", {}).get("multimodel")]
admins = [f"district:{row.district_id}" for row in keep]
pos = {a: i for i, a in enumerate(admins)}
feats = [{"n": row["name"], "st": row["state_name"], "g": {"type": row.geometry.__geo_interface__["type"], "coordinates": rnd(row.geometry.__geo_interface__["coordinates"])}} for row in keep]
N = len(admins)


def blank():
    return [None] * N


changes = pd.read_csv(MI / "model_changes.csv")
changes = changes[changes["admin"].isin(pos)]
changes["window"] = changes["window"].astype(str)
models = sorted(changes["model"].unique())
sources = ["median"] + models + ["ensemble"]

values = {s: {c: {w: blank() for w in WINDOWS} for c in COMPS} for s in sources}
worse = {s: {c: {w: blank() for w in WINDOWS} for c in COMPS} for s in sources}
for row in changes.itertuples():
    i = pos[row.admin]
    values[row.model][row.indicator][row.window][i] = r(row.change)
    worse[row.model][row.indicator][row.window][i] = bool(row.worse) if row.valid else None

rng = {c: {w: blank() for w in WINDOWS} for c in COMPS}
agree = {c: {w: blank() for w in WINDOWS} for c in COMPS}
for a in admins:
    i = pos[a]
    mm = stats[a]["climate_hazard"]["multimodel"]
    for c in COMPS:
        for w in WINDOWS:
            e = mm["indicators"].get(c, {}).get(w)
            if not e:
                continue
            values["median"][c][w][i] = e["med"]
            rng[c][w][i] = [e["min"], e["max"]]
            agree[c][w][i] = [e["n_adverse"], e["n_worse"]]
            worse["median"][c][w][i] = e["n_worse"] >= 4
    # ensemble mean (old pipeline): changes from the Atlas-style index components, threshold flags from 08
    fhi = stats[a]["climate_hazard"].get("future_hazard_index", {}).get("SSP245", {})
    ah = stats[a]["climate_hazard"].get("aggregate_hazard", {}).get("SSP245", {})
    for w in WINDOWS:
        for c in COMPS:
            values["ensemble"][c][w][i] = r(fhi.get(w, {}).get("changes", {}).get(c))
            wv = ah.get(w, {}).get("components", {}).get(c, {}).get("worse")
            worse["ensemble"][c][w][i] = wv

# aggregates per source
atlas_pm = pd.read_csv(MI / "atlas_index_per_model.csv")
atlas_pm["window"] = atlas_pm["window"].astype(str)
atlas_mm = pd.read_csv(MI / "atlas_index.csv")
atlas_mm["window"] = atlas_mm["window"].astype(str)

agg = {s: {w: blank() for w in WINDOWS} for s in sources}
for row in atlas_pm[atlas_pm["admin"].isin(pos)].itertuples():
    agg[row.model][row.window][pos[row.admin]] = {"ai": r(row.index), "ac": ATLAS_CATS[row.code + 2]}
for row in atlas_mm[atlas_mm["admin"].isin(pos)].itertuples():
    agg["median"][row.window][pos[row.admin]] = {"ai": r(row.index_med), "ac": row.category, "nu": int(row.n_unfav), "nf": int(row.n_fav)}

# threshold share per model
ch = changes.copy()
ch["w"] = ch["indicator"].map(WEIGHTS)
ch["ww"] = ch["w"] * (ch["worse"] & ch["valid"])
ch["wv"] = ch["w"] * ch["valid"]
sh = ch.groupby(["model", "admin", "window"])[["ww", "wv"]].sum()
sh = (sh["ww"] / sh["wv"] * 100).reset_index(name="share")
for row in sh.itertuples():
    e = agg[row.model][row.window][pos[row.admin]]
    e["ts"], e["tc"] = r(row.share, 1), abs_class(row.share)

for a in admins:
    i = pos[a]
    ch_ = stats[a]["climate_hazard"]
    for w in WINDOWS:
        mm = ch_["multimodel"]["aggregate"].get(w)
        if mm:
            agg["median"][w][i].update({"ts": mm["absolute"]["share"], "tc": mm["absolute"]["category"], "nm": mm["absolute"]["n_moderate"],
                                         "rs": mm["relative"]["score"], "rq": mm["relative"]["quintile"], "rd": mm["relative"]["sd_class"]})
        fe = ch_.get("future_hazard_index", {}).get("SSP245", {}).get(w)
        ae = ch_.get("aggregate_hazard", {}).get("SSP245", {}).get(w)
        if fe or ae:
            agg["ensemble"][w][i] = {
                "ai": r(fe["value"]) if fe else None, "ac": fe["category"] if fe else None,
                "ts": ae["absolute"]["share"] if ae else None, "tc": ae["absolute"]["category"] if ae else None,
                "rs": ae["relative"]["score"] if ae else None, "rq": ae["relative"]["quintile"] if ae else None, "rd": ae["relative"]["sd_class"] if ae else None}

# relative ranking per individual model (weighted percentile rank within the model)
for m in models:
    for w in WINDOWS:
        sub = changes[(changes["model"] == m) & (changes["window"] == w)]
        wide = sub.pivot_table(index="admin", columns="indicator", values="adverse")
        rk = wide.rank(pct=True) * 100
        score = (rk * pd.Series(WEIGHTS)).sum(axis=1) / sum(WEIGHTS.values())
        cuts = np.percentile(score, [20, 40, 60, 80])
        q = ["Very low", "Low", "Medium", "High", "Very high"]
        mu, sd = score.mean(), score.std(ddof=0)
        for a, v in score.items():
            e = agg[m][w][pos[a]]
            e["rs"] = r(v, 1)
            e["rq"] = q[int(np.searchsorted(cuts, v, "right"))]
            z = (v - mu) / sd
            e["rd"] = "Very high" if z > 1.5 else "High" if z > 0.5 else "Medium" if z > -0.5 else "Low" if z > -1.5 else "Very low"

out = {"districts": feats, "windows": WINDOWS, "models": models, "sources": sources, "components": COMPS,
       "weights": WEIGHTS, "sign": SIGN, "thresholds": THRESH,
       "values": values, "worse": worse, "range": rng, "agree": agree, "agg": agg}
OUT.write_text(json.dumps(out, separators=(",", ":")))
print(N, "districts", len(sources), "sources", round(os.path.getsize(OUT) / 1e6, 2), "MB")
