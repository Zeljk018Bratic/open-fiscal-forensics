"""Plan preuzimanja: svi mediji + De Conte, 2020-01-01 .. danas. Radi po godinama (nepoznato ograničenje broja redaka).
Pokretanje:  python query_plan.py --dry-run          (samo ispis upita)
             OFFF_API_KEY=... python query_plan.py   (stvarno preuzimanje u ./offf_output/api_raw)
Ako neki odgovor ima >= SPLIT_AT redaka, skripta ga automatski ponavlja po kvartalima."""
from __future__ import annotations
import os, sys
from datetime import date
from pathlib import Path

MEDIA_OIBS = ["44110106406", "76567298947", "67336385733", "64546066176", "68419124305",
              "63397242948", "58894956548", "55172671114", "36243340926", "90625517782"]   # polazna lista iz CSV isječaka – nepotpuna, PROVJERI
DE_CONTE_OIB = "57160528400"
SPLIT_AT = 900                      # sumnjivo blizu opaženog ograničenja izvoza (~1000-1130 redaka)
KEYWORDS = ["oglaš", "medij", "javnog informiranja", "promid", "reklam"]

def year_windows(first=2020, today: date | None = None):
    today = today or date.today()
    for y in range(first, today.year + 1):
        yield f"{y}-01-01", (f"{y}-12-31" if y < today.year else today.isoformat())

def quarters(a: str, b: str):
    y = int(a[:4]); qs = [(f"{y}-01-01", f"{y}-03-31"), (f"{y}-04-01", f"{y}-06-30"), (f"{y}-07-01", f"{y}-09-30"), (f"{y}-10-01", f"{y}-12-31")]
    return [(x, min(z, b)) for x, z in qs if x <= b]

def q(cond: str, a: str, b: str) -> str:
    return f"SELECT ALL DATA\nWHERE ({cond}) AND occurrence BETWEEN '{a}' AND '{b}'\nORDER BY occurrence ASC"

def build_plan(today: date | None = None):
    oibs = "[" + ", ".join(f"'{o}'" for o in MEDIA_OIBS) + "]"
    kw = " OR ".join(f"description ICONTAINS '{k}'" for k in KEYWORDS)
    sets = {
        "media_klasa3233": "economical STARTSWITH '3233'",
        "media_subvencije352": "economical STARTSWITH '352'",
        "media_opis": kw,
        "media_oib": f"vat IN {oibs}",
        "deconte_oib": f"vat = '{DE_CONTE_OIB}'",
        "deconte_naziv": "destination ICONTAINS 'conte'",
    }
    for tag, cond in sets.items():
        for a, b in year_windows(today=today):
            yield f"{tag}_{a[:4]}", q(cond, a, b), cond, a, b

def run(api_key: str, out_dir: Path, today: date | None = None, session=None):
    import transparentor_client as tc
    n = 0
    for tag, query, cond, a, b in build_plan(today):
        rec = tc.fetch_query(api_key, query, out_dir, tag, session=session); n += 1
        print(f"{tag}: {rec['rows']} redaka  sha256={rec['sha256'][:12]}")
        if rec["rows"] >= SPLIT_AT:
            for qa, qb in quarters(a, b):
                r2 = tc.fetch_query(api_key, q(cond, qa, qb), out_dir, f"{tag}_{qa[5:7]}", session=session); n += 1
                print(f"   {tag} {qa}..{qb}: {r2['rows']} redaka")
    print(f"Ukupno upita: {n} (dnevni limit 100)")

if __name__ == "__main__":
    if "--dry-run" in sys.argv:
        n = 0
        for tag, query, *_ in build_plan():
            n += 1; print(f"--- {tag}\n{query}")
        print(f"\nUkupno upita (bez dijeljenja po kvartalima): {n}")
    else:
        key = os.environ.get("OFFF_API_KEY")
        if not key: sys.exit("Postavi OFFF_API_KEY (ključ vezan uz tvoju IPv4 adresu).")
        run(key, Path(__file__).resolve().parent.parent / "offf_output" / "api_raw")
