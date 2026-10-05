from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd

def _t(df: pd.DataFrame | None, n: int = 50) -> str:
    return df.head(n).to_string(index=False) if df is not None and len(df) else "  nema nalaza"

def build_evidence_summary(integrity=None, split=None, dates=None, tamper=None, gaps=None, link=None,
                           params: dict | None = None, commit: str = "N/A") -> str:
    L = ["DOKAZNI SAŽETAK – AUTOMATIZIRANA ANALIZA JAVNIH PODATAKA",
         f"Generirano (UTC): {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
         "Status: INDICIJE ZA DALJNJU PROVJERU – nije pravno utvrđenje činjenica.", "", "1. INTEGRITET IZVORNIH PODATAKA"]
    for r in (integrity or []):
        L += [f"  Datoteka: {r.file}", f"  Očekivani SHA-256 : {r.expected}", f"  Izračunati SHA-256: {r.actual}",
              f"  Podudarnost: {'DA' if r.match else 'NE'}"]
        if not r.match:
            L += [f"  Dodano: {len(r.added)} | Obrisano: {len(r.deleted)} | Izmijenjeno polja: {len(r.modified)}",
                  f"  Baseline potvrđen sidrom: {r.baseline_trusted}", _t(r.modified, 30)]
    L += ["", "2. MOGUĆE CIJEPANJE NABAVE", _t(split),
          "", "3. LOGIKA DATUMA (račun/isplata/dospijeće)", _t(dates),
          "", "4. SUMNJA NA RETROAKTIVNI UPIS (prvo opažanje vs. tvrdnja)", _t(tamper),
          "", "5. VREMENSKE RUPE", _t(gaps), "", "6. POVEZANOST EKSCEDENCIJA I ISPLATA"]
    L.append(f"  pogodaka {link.get('pogodaka')}/{link.get('ekscedencija')}, permutacijski p = {link.get('p_value')}"
             if link and link.get("p_value") is not None else "  nije provedeno (nema podataka)")
    L += ["", "7. OGRANIČENJA", "  - Ponovljene isplate mogu biti legitimni ugovori; ravne linije mogu biti kvar senzora.",
          "  - Vremenska povezanost ne dokazuje uzročnost.", f"  - Parametri: {params or {}}; verzija koda: {commit}",
          "", "8. PRILOZI: popis datoteka s SHA-256, ledger first_seen_utc, izvorni URL i vrijeme preuzimanja."]
    return "\n".join(L)
