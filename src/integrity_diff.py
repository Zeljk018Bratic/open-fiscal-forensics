"""Hash-verifikacija + row-level diff (za verify_integrity.py). Samo relativne putanje."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep=";", encoding="utf-8-sig", dtype=str, keep_default_na=False)

# Stabilan ključ retka u pravi_budzet.csv: nema jedinstvenog ID-a, pa kombinacija polja
DEFAULT_KEY = ["Datum", "OIB", "Primatelj", "Pozicija", "Broj računa", "Poziv na broj"]

def diff_dumps(baseline: Path, current: Path, key_cols: list[str] | None = None):
    a, b = _load(baseline), _load(current)
    key = [c for c in (key_cols or DEFAULT_KEY) if c in a.columns and c in b.columns]
    for df in (a, b):                      # duplikati ključa -> redni broj, da ništa ne nestane iz diffa
        df["_n"] = df.groupby(key).cumcount()
    k = key + ["_n"]
    m = a.merge(b, on=k, how="outer", suffixes=("_stari", "_novi"), indicator=True)
    deleted = m[m["_merge"] == "left_only"][k]
    added = m[m["_merge"] == "right_only"][k]
    both = m[m["_merge"] == "both"]
    val_cols = [c for c in a.columns if c not in key + ["_n"]]
    rows = []
    for _, r in both.iterrows():
        for c in val_cols:
            if r[f"{c}_stari"] != r[f"{c}_novi"]:
                rows.append({**{x: r[x] for x in key}, "polje": c,
                             "staro": r[f"{c}_stari"], "novo": r[f"{c}_novi"]})
    return added.reset_index(drop=True), deleted.reset_index(drop=True), pd.DataFrame(rows)

@dataclass
class IntegrityReport:
    file: str; expected: str; actual: str; match: bool
    baseline_trusted: bool | None = None
    added: pd.DataFrame = field(default_factory=pd.DataFrame)
    deleted: pd.DataFrame = field(default_factory=pd.DataFrame)
    modified: pd.DataFrame = field(default_factory=pd.DataFrame)

def verify_dump(current: Path, expected_hash: str, baseline: Path | None = None) -> IntegrityReport:
    expected = expected_hash.strip().lower()
    actual = sha256_file(Path(current))
    rep = IntegrityReport(Path(current).name, expected, actual, actual == expected)
    if not rep.match and baseline is not None:
        rep.baseline_trusted = sha256_file(Path(baseline)) == expected   # arhiva mora sama odgovarati sidru
        rep.added, rep.deleted, rep.modified = diff_dumps(Path(baseline), Path(current))
    return rep
