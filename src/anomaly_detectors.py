"""Detektori anomalija za transparency_reconciler.py / live_budget_audit.py.
Ulaz: DataFrame iz labin_adapter.load_labin_csv() (+ first_seen_utc iz update_ledger)."""
from __future__ import annotations
import numpy as np, pandas as pd
from labin_adapter import split_procurement_v2, date_logic_flags   # noqa: F401 (re-export)

def timestamp_tampering(df: pd.DataFrame, tolerance_days: int = 7,
                        baseline_seen_utc: str | None = None) -> pd.DataFrame:
    """Redak koji se PRVI PUT pojavio u našem snapshotu >tolerance dana nakon datuma koji tvrdi.
    baseline_seen_utc = first_seen vrijednost PRVOG snapshota: njegovi retci su početno stanje,
    ne mogu se ocjenjivati (inače bi sve starije od tolerancije izgledalo kao backdating)."""
    d = df.copy()
    if baseline_seen_utc:
        d = d[d["first_seen_utc"] != baseline_seen_utc]
    d["_seen"] = pd.to_datetime(d["first_seen_utc"], utc=True, errors="coerce").dt.tz_localize(None)
    d["kasnjenje_dana"] = (d["_seen"] - d["datum"]).dt.days
    return d[d["kasnjenje_dana"] > tolerance_days].drop(columns="_seen").sort_values("kasnjenje_dana", ascending=False)

def time_gaps(ts: pd.Series, factor: float = 3.0) -> pd.DataFrame:
    t = pd.to_datetime(ts, errors="coerce").dropna().sort_values().reset_index(drop=True)
    dt = t.diff().dropna()
    if dt.empty: return pd.DataFrame()
    cad = dt.median(); gaps = dt[dt > cad * factor]
    return pd.DataFrame({"od": t.shift(1)[gaps.index].values, "do": t[gaps.index].values,
                         "propusteno_mjerenja": (gaps / cad).round().astype(int).values})

def flatline_series(values: pd.Series, min_run: int = 12, cv_floor: float = 0.002, win: int = 48) -> dict:
    v = pd.to_numeric(values, errors="coerce").dropna().reset_index(drop=True)
    runs = v.groupby((v != v.shift()).cumsum()).agg(["size", "first"])
    long_runs = runs[runs["size"] >= min_run].rename(columns={"size": "duljina", "first": "vrijednost"})
    cv = v.rolling(win).std() / v.rolling(win).mean().abs().replace(0, np.nan)
    share = float((cv < cv_floor).mean()) if len(v) >= win else 0.0
    return {"dugi_nizovi": long_runs, "udio_prozora_cv_nula": share,
            "za_provjeru": bool(len(long_runs) or share > 0.2)}   # kvar senzora / granica detekcije = alternativa

def link_emissions_to_payments(exceed: pd.DataFrame, pay: pd.DataFrame, oibs: set[str],
                               lag_before: int = 7, lag_after: int = 60, n_perm: int = 2000, seed: int = 42) -> dict:
    """exceed[datum,parametar,vrijednost]; pay[datum,oib,iznos]. Permutacijski test protiv slučajnih poklapanja."""
    e = exceed.assign(datum=pd.to_datetime(exceed["datum"])).sort_values("datum")
    p = pay.assign(datum=pd.to_datetime(pay["datum"]))
    p = p[p["oib"].isin(oibs)]
    if e.empty or p.empty: return {"matches": pd.DataFrame(), "p_value": None}
    lo_d, hi_d = pd.Timedelta(days=lag_before), pd.Timedelta(days=lag_after)
    ed = e["datum"].values.astype("datetime64[D]")
    def hits(dates):
        d = np.sort(np.asarray(dates, dtype="datetime64[D]"))
        a = np.searchsorted(d, ed - np.timedelta64(lag_before, "D"), "left")
        b = np.searchsorted(d, ed + np.timedelta64(lag_after, "D"), "right")
        return int((b > a).sum())
    obs = hits(p["datum"].values)
    rng = np.random.default_rng(seed); t0, t1 = p["datum"].min(), p["datum"].max(); span = max((t1 - t0).days, 1)
    perm = np.array([hits((t0 + pd.to_timedelta(rng.integers(0, span, len(p)), unit="D")).values) for _ in range(n_perm)])
    rows = [{"ekscedencija": r.datum, "parametar": getattr(r, "parametar", None), "isplata": x.datum,
             "oib": x.oib, "iznos": x.iznos, "pomak_dana": (x.datum - r.datum).days}
            for r in e.itertuples() for x in p.itertuples() if r.datum - lo_d <= x.datum <= r.datum + hi_d]
    return {"matches": pd.DataFrame(rows), "pogodaka": obs, "ekscedencija": len(e),
            "p_value": float((perm >= obs).sum() + 1) / (n_perm + 1)}
