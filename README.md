# Rama Rao hazard hotspots

District maps, distributions and hotspots for the 15 future-hazard indicators of
Rama Rao et al. (2020), *Atlas on Risk and Vulnerability of Indian Agriculture to
Climate Change* (ICAR-CRIDA), computed from the INDRA-CMIP6 14-model ensemble
and compared with the Atlas's own results.

Live: https://kushankbajaj.com/rama-rao-hotspots/

- Six INDRA-CMIP6 models (BCC-CSM2-MR, GFDL-ESM4, INM-CM5-0, MIROC6, MPI-ESM1-2-LR, NorESM2-MM), SSP2-4.5 ~2047, ~2050, ~2100 (windows 2033–2062, 2036–2065,
  2071–2100) against a 1985–2014 baseline.
- Hotspots: the 10% of districts with the most adverse change in each scenario,
  counted only where the change is adverse.
- Unusually hot and cold days use ±2 SD of the baseline daily anomaly instead of the
  Atlas's ±4 °C, and drought proneness is proxied by SPI-3 drought frequency,
  because the ensemble-mean daily data has little day-to-day variability.

## Rebuild

District changes come from the CRVA tool pipeline
(`CRVATool/data-pipeline/scripts`, `07_future_hazard_index.py` writes them to
`crva_stats.json`). Run the first command from the CRVATool folder and the
second from this repo:

```bash
conda run -n ml_trade python /path/to/rama-rao-hotspots/scripts/prep_hotspots.py   # writes scripts/data.json
python3 -c "t=open('scripts/template.html').read(); open('index.html','w').write(t.replace('__DATA__', open('scripts/data.json').read()))"
```

Part of FAO TCP/IND/4005 (NITI Aayog).
