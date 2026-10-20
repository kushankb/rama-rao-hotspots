import json, geopandas as gpd, numpy as np, os
from pathlib import Path
# Run from the CRVATool folder.
g=gpd.read_file("web/public/data/india_districts.geojson")
g["geometry"]=g.geometry.simplify(0.03, preserve_topology=True)
s=json.load(open("web/public/data/crva_stats.json"))
meta=json.load(open("web/src/data/future_hazard_meta.json"))
combos=[("SSP245","2050"),("SSP585","2050"),("SSP585","2100")]
def rnd(c):
    if isinstance(c[0],(float,int)): return [round(c[0],3),round(c[1],3)]
    return [rnd(x) for x in c]
feats=[]; vals={c["id"]:{f"{a}_{b}":[] for a,b in combos} for c in meta["components"]}
for _,r in g.iterrows():
    k=f"district:{r.district_id}"
    fhi=s.get(k,{}).get("climate_hazard",{}).get("future_hazard_index")
    if not fhi or r.geometry is None: continue
    gi=r.geometry.__geo_interface__
    feats.append({"n":r["name"],"st":r["state_name"],"g":{"type":gi["type"],"coordinates":rnd(gi["coordinates"])}})
    for c in meta["components"]:
        for a,b in combos:
            v=fhi.get(a,{}).get(b,{}).get("changes",{}).get(c["id"])
            vals[c["id"]][f"{a}_{b}"].append(None if v is None or v!=v else round(v,3))
out={"districts":feats,"values":vals,"components":meta["components"],"combos":[f"{a}_{b}" for a,b in combos]}
p=Path(__file__).parent / "data.json"
open(p,"w").write(json.dumps(out,separators=(",",":")))
print(len(feats),"districts", round(os.path.getsize(p)/1e6,2),"MB")
for c in meta["components"]:
    for cb in out["combos"]:
        v=np.array([x for x in vals[c["id"]][cb] if x is not None])
        print(f'{c["id"]:13} {cb:11} p10 {np.percentile(v,10):8.2f} med {np.median(v):8.2f} p90 {np.percentile(v,90):8.2f}  adverse {(v*c["sign"]>0).mean()*100:5.1f}%  zero {(v==0).mean()*100:5.1f}%')
