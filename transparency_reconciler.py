#!/usr/bin/env python3
"""
TransparencyDataReconciler
Standard offline data-ingestion and reconciliation module
for public-sector financial ledger verification.
Strictly respects documented rate limits and authentication.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class TransparencyDataReconciler:
    """
    Production-ready reconciler for municipal transparency APIs.
    Performs authenticated ledger extraction and statistical
    alignment against officially published aggregate totals.
    """

    def __init__(
        self,
        base_url: str = "https://transparentor.org",
        max_retries: int = 5,
        backoff_factor: float = 1.5,
        timeout: int = 30,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=backoff_factor,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_authorized_ledger(
        self,
        api_key: str,
        endpoint_url: str,
        selection_query: Dict[str, Any],
    ) -> pd.DataFrame:
        """
        Authenticated POST request to a documented open-data endpoint.
        Handles HTTP 429 (rate limiting) via exponential backoff.
        Returns a pandas DataFrame of the ledger records.
        """
        if not api_key or not isinstance(api_key, str):
            raise ValueError("A valid API key string is required.")

        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TransparencyDataReconciler/1.0 (civic-audit)",
        }

        url = endpoint_url if endpoint_url.startswith("http") else f"{self.base_url}/{endpoint_url.lstrip('/')}"

        attempt = 0
        while True:
            attempt += 1
            try:
                response = self.session.post(
                    url,
                    json=selection_query,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(
                        "Rate limit reached (429). Sleeping %s seconds (attempt %s).",
                        retry_after,
                        attempt,
                    )
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                payload = response.json()

                # Expect either a list of records or a dict with a data key
                if isinstance(payload, list):
                    records = payload
                elif isinstance(payload, dict):
                    records = payload.get("data") or payload.get("results") or payload.get("items") or []
                else:
                    raise ValueError("Unexpected JSON structure returned by the API.")

                if not records:
                    logger.warning("API returned an empty record set.")
                    return pd.DataFrame()

                df = pd.DataFrame(records)
                logger.info("Successfully retrieved %s ledger rows.", len(df))
                return df

            except requests.exceptions.RequestException as exc:
                logger.error("Request failed on attempt %s: %s", attempt, exc)
                if attempt >= 5:
                    raise
                time.sleep(self.session.adapters["https://"].max_retries.backoff_factor * attempt)

    def calculate_audit_delta(
        self,
        extracted_df: pd.DataFrame,
        official_totals_dict: Dict[str, float],
        amount_column: str = "amount",
        konto_column: Optional[str] = "konto",
    ) -> Dict[str, Any]:
        """
        Compute absolute statistical variance (delta) between
        the sum of records exposed via the API and the official
        published aggregate benchmarks.
        """
        if extracted_df.empty:
            return {
                "status": "NO_DATA",
                "message": "Extracted DataFrame is empty. Cannot perform reconciliation.",
                "deltas": {},
            }

        if amount_column not in extracted_df.columns:
            raise KeyError(f"Amount column '{amount_column}' not found in extracted data.")

        # Ensure numeric
        extracted_df = extracted_df.copy()
        extracted_df[amount_column] = pd.to_numeric(extracted_df[amount_column], errors="coerce").fillna(0.0)

        results: Dict[str, Any] = {
            "status": "OK",
            "record_count": len(extracted_df),
            "deltas": {},
            "absolute_total_delta": 0.0,
        }

        # Total outflows
        api_total = float(extracted_df[amount_column].sum())
        official_total = float(official_totals_dict.get("Total Outflows", 0.0))
        total_delta = abs(api_total - official_total)
        results["deltas"]["Total Outflows"] = {
            "api_sum": round(api_total, 2),
            "official": round(official_total, 2),
            "delta": round(total_delta, 2),
            "relative_pct": round((total_delta / official_total * 100) if official_total else 0.0, 4),
        }
        results["absolute_total_delta"] = total_delta

        # Optional konto-level checks
        if konto_column and konto_column in extracted_df.columns:
            for key, official_value in official_totals_dict.items():
                if key.startswith("Konto "):
                    konto_code = key.replace("Konto ", "").strip()
                    mask = extracted_df[konto_column].astype(str).str.contains(konto_code, na=False)
                    api_konto_sum = float(extracted_df.loc[mask, amount_column].sum())
                    delta = abs(api_konto_sum - float(official_value))
                    results["deltas"][key] = {
                        "api_sum": round(api_konto_sum, 2),
                        "official": round(float(official_value), 2),
                        "delta": round(delta, 2),
                        "relative_pct": round((delta / float(official_value) * 100) if official_value else 0.0, 4),
                    }

        # Integrity flag
        max_relative = max(
            (v["relative_pct"] for v in results["deltas"].values()),
            default=0.0,
        )
        if max_relative > 1.0:  # > 1 % variance triggers attention
            results["status"] = "VARIANCE_DETECTED"
            results["message"] = (
                f"Maximum relative variance {max_relative:.2f}% exceeds 1% threshold. "
                "Manual review of source data and mapping recommended."
            )
        else:
            results["message"] = "Extracted public records mathematically reconstruct the audited envelope within tolerance."

        return results


# ---------------------------------------------------------------------------
# Example integration point for a local Streamlit dashboard (app.py)
# ---------------------------------------------------------------------------
def render_integrity_report(reconciler: TransparencyDataReconciler, api_key: str) -> None:
    """
    Defensive reporting utility intended for Streamlit.
    Call this from your Streamlit page after user provides a valid API key.
    """
    import streamlit as st

    st.subheader("Public Ledger Integrity Report")

    official_totals = {
        "Total Outflows": 25_923_989.48,
        "Konto 3237": 705_827.65,
        "Konto 3238": 156_248.09,
    }

    # Example documented query payload – adjust to the exact schema
    # published in the official API documentation of the municipality.
    selection_query = {
        "year": 2025,
        "type": "outflow",
        "limit": 10000,
    }

    with st.spinner("Fetching authorized ledger..."):
        try:
            df = reconciler.fetch_authorized_ledger(
                api_key=api_key,
                endpoint_url="/api/v1/ledger",  # replace with documented path
                selection_query=selection_query,
            )
        except Exception as exc:
            st.error(f"Unable to retrieve ledger: {exc}")
            return

    report = reconciler.calculate_audit_delta(df, official_totals)

    st.metric("Records retrieved", report["record_count"])
    st.write("**Status:**", report["status"])
    st.write(report.get("message", ""))

    if report["deltas"]:
        delta_df = pd.DataFrame.from_dict(report["deltas"], orient="index")
        st.dataframe(delta_df, use_container_width=True)

    if report["status"] == "VARIANCE_DETECTED":
        st.warning(
            "Detected variance between API-exposed records and official audited totals. "
            "Cross-check against the published annual financial statements."
        )
    else:
        st.success("Reconciliation within acceptable tolerance.")
        # ---------------------------------------------------------------------------
# Supplied multi-year schema.
# Replace USER_SUPPLIED placeholders with independently verified source
# records before treating the dataset as an evidentiary record.
# ---------------------------------------------------------------------------

HISTORICAL_LEDGER = (
    YearLedger(
        year=2023,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
    YearLedger(
        year=2024,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
    YearLedger(
        year=2025,
        total_realized_outflows=money("25923989.48"),
        konto_32=money("6899673.65"),
        konto_323=money("4176288.28"),
        konto_3233_media=money("63102.72"),
        konto_3237_intellectual_consulting=money("705827.65"),
        konto_3238_software_it=money("156248.09"),
        mayor_office_media=money("30869.58"),
    ),
    YearLedger(
        year=2026,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
)

ECOLOGICAL_INDICATORS = (
    EcologicalIndicator(
        indicator_id="TOC_SPIKE_01",
        description="User-supplied count of reported chlorine-associated TOC threshold exceedance observations.",
        observed_value=money("148"),
        reference_value=money("0"),
        unit="incidents",
    ),
    EcologicalIndicator(
        indicator_id="TOC_THRESHOLD_01",
        description="User-supplied reported TOC concentration threshold.",
        observed_value=money("20"),
        reference_value=money("20"),
        unit="mg/m3",
    ),
    EcologicalIndicator(
        indicator_id="INDUSTRIAL_WASTE_01",
        description="User-supplied reported quantity of cross-border industrial chemical waste.",
        observed_value=money("19013"),
        reference_value=None,
        unit="tons",
    ),
    EcologicalIndicator(
        indicator_id="DECLARED_CUSTOMS_VALUE_01",
        description="User-supplied reported customs declaration value associated with the waste quantity.",
        observed_value=money("124"),
        reference_value=None,
        unit="EUR",
    ),
    EcologicalIndicator(
        indicator_id="SEAWATER_01",
        description="User-supplied reported annual raw seawater volume.",
        observed_value=money("1562400"),
        reference_value=None,
        unit="m3/year",
    ),
    EcologicalIndicator(
        indicator_id="NAOH_01",
        description="User-supplied reported annual sodium hydroxide quantity.",
        observed_value=money("1567"),
        reference_value=None,
        unit="tons/year",
    ),
    EcologicalIndicator(
        indicator_id="STACK_SURGE_01",
        description="User-supplied reported real-time toxic-emission surge associated with the 36 m precalciner stack.",
        observed_value=money("15"),
        reference_value=money("1"),
        unit="x baseline",
    ),
)

MATCH_RULES = (
    MatchRule(
        rule_id="GOSPIC_SILO_CONTRACT",
        target_label="€8.77M Gospić silo extraction contract",
        target_oibs=(),
    ),
    MatchRule(
        rule_id="PAZIN_INDUSTRIAL_DUMP",
        target_label="Slaven Tintor / Pazin industrial dump",
        target_oibs=(),
    ),
)

SOURCE_REFERENCE = {
    "transparency_provider": {
        "search_engine": "https://transparentor.org",
        "data_export_endpoint": "https://transparentor.org/api-dokumentacija",
        "api_key_access_point": "https://transparentor.org/zatrazi-api-kljuc",
        "active_footprint": "© 2026. CityX Apps d.o.o.",
        "network_access": False,
    },
    "ecological_dossier": {
        "url": "https://github.io",
        "source_status": "USER_SUPPLIED",
        "independent_verification": False,
    },
    "financial_dataset": {
        "municipality": "Grad Labin",
        "period":,
        "currency": "EUR",
        "source_status": "USER_SUPPLIED",
    },
}

def run_offline_ingestion(output_dir: Path) -> dict[str, Any]:
    """Execute the complete offline reconciliation workflow."""
    output_dir.mkdir(parents=True, exist_ok=True)

    historical = build_historical_template(HISTORICAL_LEDGER)

    audit_delta = calculate_audit_delta(
        konto="3233",
        expected="78102.72",
        observed="63102.72",
    )

    reconciliation_payload = {
        "audit_delta": audit_delta.to_json_dict(),
        "historical": historical,
        "ecological_indicators": [
            indicator.to_json_dict()
            for indicator in ECOLOGICAL_INDICATORS
        ],
        "source_mapping": SOURCE_REFERENCE,
    }

    block_path = output_dir / "offf_sha256_ledger.json"

    blocks = append_hash_ledger(
        block_path,
        payloads=(reconciliation_payload,),
    )

    latest_block = blocks[-1]

    markdown = generate_scribehow_markdown(
        audit_delta=audit_delta,
        ecological_indicators=ECOLOGICAL_INDICATORS,
        block=latest_block,
    )

    (output_dir / "offf_audit_log.md").write_text(
        markdown,
        encoding="utf-8",
    )

    export_json(
        output_dir / "historical_template.json",
        historical,
    )

    return {
        "status": "INGESTION_COMPLETE",
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "block_hash": latest_block.block_hash,
        "ledger_verified": verify_chain(blocks),
        "absolute_delta_eur": format(abs(audit_delta.delta), "f"),
        "historical_years":,
    }

if __name__ == "__main__":
    result = run_offline_ingestion(
        Path("offf_output"),
    )
    print(json.dumps(result, indent=2, sort_keys=True))

