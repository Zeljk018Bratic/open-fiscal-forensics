# forensic_core/cross_border_integrity.py
from __future__ import annotations
import pandas as pd
from pathlib import Path
from typing import Optional, Set, Dict, Any
import json

class CrossBorderIntegrityMonitor:
    """
    Modularni forenzički monitor za unakrsnu provjeru proračuna, 
    ZPPI podataka o medijima i registra rizičnih entiteta (OIB-a).
    """
    def __init__(self, risk_oibs: Optional[Set[str]] = None):
        self.risk_oibs: Set[str] = risk_oibs or set()

    @classmethod
    def from_risk_file(cls, path: str | Path) -> "CrossBorderIntegrityMonitor":
        """Učitava rizične OIB-ove iz vanjske JSON liste ili CSV-a."""
        path = Path(path)
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            oibs = {str(x).strip() for x in data}
        else:
            df = pd.read_csv(path, dtype=str)
            col = "oib" if "oib" in df.columns else df.columns[0]
            oibs = set(df[col].dropna().astype(str).str.strip())
        return cls(risk_oibs=oibs)

    def evaluate_media_outflow_density(
        self,
        budget_csv: str | Path,
        zppi_media_csv: str | Path,
        date_col_budget: str = "datum",
        amount_col_budget: str = "iznos",
        date_col_media: str = "datum",
        amount_col_media: str = "iznos",
    ) -> Dict[str, Any]:
        """Računa postotni udio (gustoću) isplata lokalnim medijima u ukupnom proračunu."""
        budget = pd.read_csv(budget_csv, dtype=str)
        media = pd.read_csv(zppi_media_csv, dtype=str)

        budget[amount_col_budget] = pd.to_numeric(budget[amount_col_budget], errors="coerce")
        media[amount_col_media] = pd.to_numeric(media[amount_col_media], errors="coerce")

        total_budget = budget[amount_col_budget].sum(skipna=True)
        total_media = media[amount_col_media].sum(skipna=True)
        density = (total_media / total_budget * 100) if total_budget else 0.0

        monthly = None
        if date_col_budget in budget.columns and date_col_media in media.columns:
            budget["_m"] = pd.to_datetime(budget[date_col_budget], errors="coerce").dt.to_period("M")
            media["_m"] = pd.to_datetime(media[date_col_media], errors="coerce").dt.to_period("M")
            b_m = budget.groupby("_m")[amount_col_budget].sum()
            m_m = media.groupby("_m")[amount_col_media].sum()
            monthly = pd.DataFrame({"budget": b_m, "media": m_m}).fillna(0)
            monthly["media_pct"] = (monthly["media"] / monthly["budget"] * 100).round(2)

        return {
            "total_budget_outflow": float(total_budget),
            "total_media_outflow": float(total_media),
            "media_density_pct": round(density, 2),
            "monthly_breakdown": monthly.to_dict() if monthly is not None else None,
        }

    def flag_entity_risk_correlation(
        self,
        procurement_csv: str | Path,
        oib_col: str = "oib",
    ) -> pd.DataFrame:
        """Križa OIB-ove iz javne nabave s vanjskom listom rizičnih subjekata."""
        df = pd.read_csv(procurement_csv, dtype=str)
        if oib_col not in df.columns:
            raise ValueError(f"Stupac '{oib_col}' nije pronađen u datoteci javne nabave")

        df["_oib_clean"] = df[oib_col].astype(str).str.strip()
        matched = df[df["_oib_clean"].isin(self.risk_oibs)].copy()
        return matched.reset_index(drop=True)
