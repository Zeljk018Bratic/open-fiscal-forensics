"""Klijent za CityX/transparentor API (prema https://labin.transparentor.org/api-dokumentacija).
POST text/plain upit 'SELECT ALL DATA WHERE ...' na <api>/export; Authorization: ApiKey ...; limit 100 upita/dan.
Svaki odgovor se sprema SIROV + SHA-256 + vrijeme preuzimanja (lanac čuvanja dokaza)."""
from __future__ import annotations
import hashlib, json, time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import requests

API_URL = "https://labin-api.transparentor.org/export"
DAILY_LIMIT = 100

class DailyLimitReached(RuntimeError): ...

def build_query(day_from: date, day_to: date, extra: str = "") -> str:
    q = f"SELECT ALL DATA\nWHERE occurrence BETWEEN '{day_from.isoformat()}' AND '{day_to.isoformat()}'"
    if extra: q += f"\nAND {extra}"
    return q + "\nORDER BY occurrence ASC"

def fetch_window(api_key: str, day_from: date, day_to: date, out_dir: Path,
                 session: requests.Session | None = None, url: str = API_URL, timeout: int = 60) -> dict:
    s = session or requests.Session()
    r = s.post(url, data=build_query(day_from, day_to).encode("utf-8"), timeout=timeout,
               headers={"Authorization": f"ApiKey {api_key}", "Content-Type": "text/plain;charset=utf-8",
                        "Accept": "application/json"})
    if r.status_code == 429:
        raise DailyLimitReached("Dnevni limit API upita (100) dosegnut – nastavi sutra, ne ponavljaj upite.")
    r.raise_for_status()
    raw = r.content
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"export_{day_from}_{day_to}_{stamp}.json"
    path.write_bytes(raw)                                   # sirovi bajtovi, bez ikakve obrade
    payload = json.loads(raw)
    rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("results") or payload.get("items") or [])
    rec = {"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "rows": len(rows),
           "from": str(day_from), "to": str(day_to), "retrieved_at_utc": stamp, "url": url,
           "query": build_query(day_from, day_to)}
    with open(out_dir / "download_manifest.jsonl", "a", encoding="utf-8") as f:   # append-only dnevnik preuzimanja
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec

def fetch_range(api_key: str, start: date, end: date, out_dir: Path, window_days: int = 7, **kw) -> list[dict]:
    """Prozori po tjednu: izbjegava moguće gornje ograničenje broja redaka i troši ~52 upita/godinu."""
    recs, cur = [], start
    while cur <= end:
        nxt = min(cur + timedelta(days=window_days - 1), end)
        recs.append(fetch_window(api_key, cur, nxt, out_dir, **kw)); cur = nxt + timedelta(days=1)
        time.sleep(1)
    return recs

def api_rows_to_df(rows: list[dict]):
    import pandas as pd
    df = pd.DataFrame(rows).rename(columns={"vat": "oib", "destination": "primatelj", "occurrence": "datum",
                                            "amount": "iznos", "description": "opis"})
    df["datum"] = pd.to_datetime(df["datum"], errors="coerce", utc=True).dt.tz_localize(None)
    df["iznos"] = pd.to_numeric(df["iznos"], errors="coerce")
    if "update_date" in df: df["update_date"] = pd.to_datetime(df["update_date"], errors="coerce", utc=True).dt.tz_localize(None)
    df["oib_valjan"] = df["oib"].astype(str).str.fullmatch(r"\d{11}")
    return df

def id_gaps(df, id_col: str = "id") -> list[int]:
    ids = sorted(pd_int for pd_int in df[id_col].dropna().astype(int).unique())
    return [i for a, b in zip(ids, ids[1:]) for i in range(a + 1, b)] if ids else []

def update_after_booking(df, tolerance_days: int = 30):
    """API polje update_date: zapisi izmijenjeni dugo nakon datuma knjiženja. Operater kontrolira to polje,
    pa je ovo samo prvi filter; jači je signal usporedbe s našim first_seen_utc (vidi anomaly_detectors)."""
    d = (df["update_date"] - df["datum"]).dt.days
    return df.assign(izmjena_nakon_dana=d)[d > tolerance_days].sort_values("izmjena_nakon_dana", ascending=False)

def first_seen_before_update(df, tolerance_days: int = 1):
    """Zapis koji smo PRVI put vidjeli nakon što tvrdi da je zadnji put izmijenjen => update_date unatrag ili propušten snapshot."""
    seen = __import__("pandas").to_datetime(df["first_seen_utc"], utc=True, errors="coerce").dt.tz_localize(None)
    return df[(seen - df["update_date"]).dt.days > tolerance_days]


def fetch_query(api_key: str, query: str, out_dir: Path, tag: str,
                session: requests.Session | None = None, url: str = API_URL, timeout: int = 120) -> dict:
    """Proizvoljan EXPORT upit; sirov odgovor + SHA-256 + vrijeme + točan tekst upita (append-only dnevnik)."""
    s = session or requests.Session()
    r = s.post(url, data=query.encode("utf-8"), timeout=timeout,
               headers={"Authorization": f"ApiKey {api_key}", "Content-Type": "text/plain;charset=utf-8",
                        "Accept": "application/json"})
    if r.status_code == 429:
        raise DailyLimitReached("Dnevni limit API upita (100) dosegnut – nastavi sutra.")
    r.raise_for_status()
    raw = r.content
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out_dir / f"{tag}_{stamp}.json"
    path.write_bytes(raw)
    payload = json.loads(raw)
    rows = payload if isinstance(payload, list) else (payload.get("data") or payload.get("results") or payload.get("items") or [])
    rec = {"tag": tag, "file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
           "rows": len(rows), "retrieved_at_utc": stamp, "url": url, "query": query}
    with open(out_dir / "download_manifest.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec
