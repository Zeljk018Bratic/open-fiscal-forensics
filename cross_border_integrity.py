# cross_border_integrity.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Set, Union

import pandas as pd


class CrossBorderIntegrityMonitor:
    """
    Modular forensic monitor for cross-checking municipal budgets,
    ZPPI media responses and external risk OIB registries.
    Hardened for real Croatian municipal CSV exports
    (semicolon-separated + double-quoted fields).
    """

    def __init__(self, risk_oibs: Optional[Set[str]] = None):
        self.risk_oibs: Set[str] = risk_oibs or set()

    # ------------------------------------------------------------------
    # Bullet-proof loader for the exact Croatian municipal format
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_read_csv(path: Union[str, Path]) -> pd.DataFrame:
        """
        Force semicolon parsing and aggressively strip enclosing double quotes
        from both headers and data cells. Designed for the exact layout of
        pravi_budzet.csv and similar EU/Croatian exports.
        """
        path = Path(path)

        # Primary strategy: semicolon + QUOTE_MINIMAL / QUOTE_ALL
        try:
            df = pd.read_csv(
                path,
                sep=";",
                dtype=str,
                engine="python",
                quoting=1,              # QUOTE_ALL
                on_bad_lines="warn",
                encoding="utf-8-sig",
            )
        except Exception:
            # Fallback: ignore quoting rules completely
            df = pd.read_csv(
                path,
                sep=";",
                dtype=str,
                engine="python",
                quoting=3,              # QUOTE_NONE
                on_bad_lines="warn",
                encoding="utf-8-sig",
            )

        # Clean column names – remove surrounding quotes and whitespace
        df.columns = (
            df.columns.astype(str)
            .str.replace(r'^["\']+|["\']+$', "", regex=True)
            .str.strip()
        )

        # Clean every cell – strip surrounding quotes
        for col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(r'^["\']+|["\']+$', "", regex=True)
                .str.strip()
            )

        return df

    # ------------------------------------------------------------------
    # Case-insensitive substring column locator
    # ------------------------------------------------------------------
    @staticmethod
    def _find_column(df: pd.DataFrame, *candidates: str) -> Optional[str]:
        """
        Return the first column whose cleaned name contains any of the
        candidate strings (case-insensitive).
        Handles real headers such as "OIB", "Iznos na poziciji", "Datum".
        """
        for col in df.columns:
            col_lower = str(col).lower()
            for cand in candidates:
                if cand.lower() in col_lower:
                    return col
        return None

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def from_risk_file(cls, path: Union[str, Path]) -> "CrossBorderIntegrityMonitor":
        path = Path(path)
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            oibs = {str(x).strip() for x in data}
        else:
            df = cls._safe_read_csv(path)
            col = cls._find_column(df, "oib") or (df.columns[0] if len(df.columns) else None)
            if col is None:
                oibs = set()
            else:
                oibs = set(df[col].dropna().astype(str).str.strip())
        return cls(risk_oibs=oibs)

    # ------------------------------------------------------------------
    # Media density
    # ------------------------------------------------------------------
    def evaluate_media_outflow_density(
        self,
        budget_csv: Union[str, Path],
        zppi_media_csv: Union[str, Path],
        date_col_budget: str = "datum",
        amount_col_budget: str = "iznos",
        date_col_media: str = "datum",
        amount_col_media: str = "iznos",
    ) -> Dict[str, Any]:
        budget = self._safe_read_csv(budget_csv)
        media = self._safe_read_csv(zppi_media_csv)

        # Locate amount columns (real header = "Iznos na poziciji")
        amount_col_budget = (
            self._find_column(budget, "Iznos na poziciji", "Iznos", "amount", "suma")
            or amount_col_budget
        )
        amount_col_media = (
            self._find_column(media, "Iznos na poziciji", "Iznos", "amount", "suma")
            or amount_col_media
        )

        if amount_col_budget not in budget.columns:
            raise ValueError(
                f"Amount column not found in budget file. Available: {list(budget.columns)}"
            )
        if amount_col_media not in media.columns:
            raise ValueError(
                f"Amount column not found in media file. Available: {list(media.columns)}"
            )

        # Strip any residual quotes then convert
        budget[amount_col_budget] = (
            budget[amount_col_budget]
            .astype(str)
            .str.replace(r'["\']', "", regex=True)
            .str.replace(",", ".", regex=False)   # just in case of European decimal
        )
        media[amount_col_media] = (
            media[amount_col_media]
            .astype(str)
            .str.replace(r'["\']', "", regex=True)
            .str.replace(",", ".", regex=False)
        )

        budget[amount_col_budget] = pd.to_numeric(budget[amount_col_budget], errors="coerce")
        media[amount_col_media] = pd.to_numeric(media[amount_col_media], errors="coerce")

        total_budget = float(budget[amount_col_budget].sum(skipna=True))
        total_media = float(media[amount_col_media].sum(skipna=True))
        density = (total_media / total_budget * 100.0) if total_budget else 0.0

        # Optional monthly breakdown
        date_col_budget = self._find_column(budget, "Datum", "datum", "date") or date_col_budget
        date_col_media = self._find_column(media, "Datum", "datum", "date") or date_col_media

        monthly = None
        if date_col_budget in budget.columns and date_col_media in media.columns:
            budget = budget.copy()
            media = media.copy()
            budget["_m"] = pd.to_datetime(budget[date_col_budget], errors="coerce").dt.to_period("M")
            media["_m"] = pd.to_datetime(media[date_col_media], errors="coerce").dt.to_period("M")
            b_m = budget.groupby("_m", dropna=True)[amount_col_budget].sum()
            m_m = media.groupby("_m", dropna=True)[amount_col_media].sum()
            monthly = (
                pd.DataFrame({"budget": b_m, "media": m_m})
                .fillna(0)
                .assign(media_pct=lambda d: (d["media"] / d["budget"] * 100).round(2))
            )

        return {
            "total_budget_outflow": total_budget,
            "total_media_outflow": total_media,
            "media_density_pct": round(density, 2),
            "monthly_breakdown": monthly.to_dict() if monthly is not None else None,
        }

    # ------------------------------------------------------------------
    # OIB intersection
    # ------------------------------------------------------------------
    def flag_entity_risk_correlation(
        self,
        procurement_csv: Union[str, Path],
        oib_col: str = "oib",
    ) -> pd.DataFrame:
        df = self._safe_read_csv(procurement_csv)

        # Locate the real OIB column (header contains "OIB")
        detected = self._find_column(df, "OIB", "oib", "partner_oib", "maticni")
        if detected is None:
            raise ValueError(
                f"No OIB column found. Available columns: {list(df.columns)}"
            )
        oib_col = detected

        df = df.copy()
        # Final clean of OIB values – strip quotes and whitespace
        df["_oib_clean"] = (
            df[oib_col]
            .astype(str)
            .str.replace(r'["\']', "", regex=True)
            .str.strip()
        )

        matched = df[df["_oib_clean"].isin(self.risk_oibs)].copy()
        matched = matched.drop(columns=["_oib_clean"])
        return matched.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Optional audit checklist
    # ------------------------------------------------------------------
    def audit_status_summary(
        self,
        has_independent_source_code_audit: bool,
        has_admin_access_logs: bool,
        has_write_permission_matrix: bool,
    ) -> Dict[str, Any]:
        checks = {
            "independent_source_code_audit": has_independent_source_code_audit,
            "admin_access_logs_available": has_admin_access_logs,
            "write_permission_matrix_available": has_write_permission_matrix,
        }
        missing = [k for k, v in checks.items() if not v]
        return {
            "checks": checks,
            "missing_items": missing,
            "all_present": len(missing) == 0,
        }
