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
    """

    def __init__(self, risk_oibs: Optional[Set[str]] = None):
        self.risk_oibs: Set[str] = risk_oibs or set()

    # ------------------------------------------------------------------
    # Robust CSV loader (handles both , and ; + embedded commas)
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_read_csv(path: Union[str, Path]) -> pd.DataFrame:
        """
        Bullet-proof CSV reader for Croatian / EU municipal exports.
        Tries comma, then semicolon, then falls back to the Python engine
        with automatic separator detection. Never raises on field-count
        mismatches.
        """
        path = Path(path)

        # 1) Fast path – standard comma
        try:
            return pd.read_csv(
                path,
                dtype=str,
                sep=",",
                engine="c",
                quoting=1,          # QUOTE_ALL
                on_bad_lines="warn",
                encoding="utf-8-sig",
            )
        except Exception:
            pass

        # 2) Common EU / Croatian export – semicolon
        try:
            return pd.read_csv(
                path,
                dtype=str,
                sep=";",
                engine="c",
                quoting=1,
                on_bad_lines="warn",
                encoding="utf-8-sig",
            )
        except Exception:
            pass

        # 3) Last-resort – Python engine, automatic separator detection
        return pd.read_csv(
            path,
            dtype=str,
            sep=None,               # let the engine sniff
            engine="python",
            on_bad_lines="warn",
            encoding="utf-8-sig",
        )

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------
    @classmethod
    def from_risk_file(cls, path: Union[str, Path]) -> "CrossBorderIntegrityMonitor":
        """Load risk OIBs from an external JSON list or CSV."""
        path = Path(path)
        if path.suffix.lower() == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            oibs = {str(x).strip() for x in data}
        else:
            df = cls._safe_read_csv(path)
            col = "oib" if "oib" in df.columns else df.columns[0]
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
        """
        Calculate the percentage share of media payments inside the total
        budget outflow. Returns a pure numeric summary.
        """
        budget = self._safe_read_csv(budget_csv)
        media = self._safe_read_csv(zppi_media_csv)

        # Flexible amount column detection (common aliases)
        for alias in (amount_col_budget, "iznos", "amount", "vrijednost", "suma"):
            if alias in budget.columns:
                amount_col_budget = alias
                break
        for alias in (amount_col_media, "iznos", "amount", "vrijednost", "suma"):
            if alias in media.columns:
                amount_col_media = alias
                break

        budget[amount_col_budget] = pd.to_numeric(
            budget[amount_col_budget], errors="coerce"
        )
        media[amount_col_media] = pd.to_numeric(
            media[amount_col_media], errors="coerce"
        )

        total_budget = float(budget[amount_col_budget].sum(skipna=True))
        total_media = float(media[amount_col_media].sum(skipna=True))
        density = (total_media / total_budget * 100.0) if total_budget else 0.0

        monthly = None
        if date_col_budget in budget.columns and date_col_media in media.columns:
            budget = budget.copy()
            media = media.copy()
            budget["_m"] = pd.to_datetime(
                budget[date_col_budget], errors="coerce"
            ).dt.to_period("M")
            media["_m"] = pd.to_datetime(
                media[date_col_media], errors="coerce"
            ).dt.to_period("M")
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
        """
        Return only those procurement rows whose OIB appears in the
        externally supplied risk set. Pure set intersection.
        """
        df = self._safe_read_csv(procurement_csv)

        # Flexible OIB column detection
        candidates = [oib_col, "oib", "OIB", "partner_oib", "maticni_broj"]
        for col in candidates:
            if col in df.columns:
                oib_col = col
                break
        else:
            raise ValueError(
                f"No OIB column found. Available columns: {list(df.columns)}"
            )

        df = df.copy()
        df["_oib_clean"] = df[oib_col].astype(str).str.strip()
        matched = df[df["_oib_clean"].isin(self.risk_oibs)].copy()
        matched = matched.drop(columns=["_oib_clean"])
        return matched.reset_index(drop=True)

    # ------------------------------------------------------------------
    # Optional audit checklist (unchanged public API)
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
