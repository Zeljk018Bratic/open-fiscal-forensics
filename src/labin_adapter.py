from __future__ import annotations
import hashlib, json
from pathlib import Path
import pandas as pd

PLACEHOLDER_OIB = {"", "GDPR"}          # maskirane fizičke osobe / prazno polje
COLMAP = {"Datum": "datum", "Datum računa": "datum_racuna", "Datum dospijeća": "datum_dospijeca",
          "Iznos na poziciji": "iznos", "Primatelj": "primatelj", "OIB": "oib",
          "Broj računa": "broj_racuna", "Opis": "opis", "Pozicija": "pozicija",
          "Ekonomska klasifikacija": "ekon_klasa", "IBAN": "iban"}

def load_labin_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)
    raw = df.copy()
    df = df.rename(columns=COLMAP)
    for c in ("datum", "datum_racuna", "datum_dospijeca"):
        df[c] = pd.to_datetime(df[c], errors="coerce", utc=True).dt.tz_localize(None)
    df["iznos"] = pd.to_numeric(df["iznos"], errors="coerce")
    df["oib_valjan"] = df["oib"].str.fullmatch(r"\d{11}")      # samo prava 11-znamenkasta polja
    # hash retka nad SIROVIM vrijednostima (stabilan identitet retka za snapshot ledger)
    df["row_hash"] = raw.apply(lambda r: hashlib.sha256("\x1f".join(r.astype(str)).encode()).hexdigest(), axis=1)
    return df

def update_ledger(df: pd.DataFrame, ledger_path: Path, now_utc: str) -> pd.DataFrame:
    """Vlastiti 'first_seen_utc' – jedini timestamp kojem vjerujemo. Ledger je append-only."""
    led = pd.read_json(ledger_path, lines=True) if ledger_path.exists() else pd.DataFrame(columns=["row_hash", "first_seen_utc"])
    new = df.loc[~df["row_hash"].isin(led["row_hash"]), ["row_hash"]].assign(first_seen_utc=now_utc)
    if len(new):
        with open(ledger_path, "a", encoding="utf-8") as f:
            for rec in new.to_dict("records"):
                f.write(json.dumps(rec) + "\n")
        led = pd.concat([led, new], ignore_index=True)
    return df.merge(led, on="row_hash", how="left")

def split_procurement_v2(df, threshold=26_540.0, band=0.15, window_days=90, min_invoices=2):
    d = df[df["oib_valjan"] & df["iznos"].notna()].copy()
    # 1) agregiraj POZICIJE istog računa u jedan račun (inače lažno 'cijepanje')
    d["racun_kljuc"] = d["broj_racuna"].where(d["broj_racuna"] != "", d["row_hash"])
    inv = (d.groupby(["oib", "primatelj", "racun_kljuc"], as_index=False)
             .agg(iznos=("iznos", "sum"), datum=("datum", "max"), n_pozicija=("iznos", "size")))
    out = []
    for (oib, prim), g in inv.groupby(["oib", "primatelj"]):
        g = g.sort_values("datum").set_index("datum")
        s = g["iznos"].rolling(f"{window_days}D").sum()
        n = g["iznos"].rolling(f"{window_days}D").count()
        hit = (s > threshold) & (n >= min_invoices) & (g["iznos"] < threshold)
        if hit.any():
            out.append({"oib": oib, "primatelj": prim, "n_racuna": int(n[hit].max()),
                        "kumulativ": round(float(s[hit].max()), 2),
                        "tik_ispod_praga": int(g["iznos"].between(threshold*(1-band), threshold, inclusive="left").sum()),
                        "omjer_praga": round(float(s[hit].max()/threshold), 2)})
    return pd.DataFrame(out).sort_values("omjer_praga", ascending=False) if out else pd.DataFrame()

def date_logic_flags(df, late_days=90):
    f = pd.DataFrame(index=df.index)
    f["racun_nakon_isplate"] = df["datum_racuna"] > df["datum"]
    f["isplata_nakon_dospijeca_dana"] = (df["datum"] - df["datum_dospijeca"]).dt.days
    f["kasni_racun_dana"] = (df["datum"] - df["datum_racuna"]).dt.days
    f["flag_vrlo_kasno"] = f["kasni_racun_dana"] > late_days
    return f
