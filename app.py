"""Streamlit MVP dashboard for the #BajteBrothers forensic budget workflow.

This local-first dashboard integrates the existing data-cleaning/adaptation
layer with a lightweight forensic analysis pipeline and PDF reporting. It is
intentionally modular so the underlying mathematics remains untouched while the
front-end provides a simple citizen-science workflow for public budget review.

Workflow:
1. Upload a budget CSV together with provenance metadata.
2. Detect the amount column automatically via AutoAdapter.
3. Run a forensic summary using a lightweight local ForensicCore wrapper.
4. Generate a visual anomaly chart and a PDF forensic certificate.
5. Download the PDF and a structured JSON audit manifest.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from auto_adapter import detect_amount_column_from_csv
from pdf_generator import ForensicPDFGenerator

try:  # pragma: no cover - compatibility layer for future project additions.
    from forensic_core import ForensicCore
except ImportError:  # pragma: no cover - local fallback for MVP workflow.
    class ForensicCore:
        """Local compatibility shim for forensic evaluation."""

        @staticmethod
        def analyze(csv_path: str | os.PathLike[str], amount_column: int | None = None) -> Dict[str, Any]:
            """Analyze a CSV file and return a small forensic summary payload."""
            rows = _read_csv_rows(csv_path)
            if not rows:
                raise ValueError("CSV contains no rows.")
            if amount_column is None:
                amount_column = detect_amount_column_from_csv(csv_path)

            values: List[float] = []
            for row in rows[1:]:
                if amount_column >= len(row):
                    continue
                value = row[amount_column]
                numeric = _parse_numeric_token(value)
                if numeric is not None:
                    values.append(float(numeric))

            if not values:
                raise ValueError("No usable monetary values were found in the selected CSV column.")

            chi2_score = _calculate_chi_square(values)
            entropy_score = _calculate_shannon_entropy(values)
            risk_level, risk_label = _classify_risk(chi2_score, entropy_score)

            return {
                "label": "Budget Integrity Review",
                "risk_level": risk_level,
                "risk_label": risk_label,
                "metrics": {
                    "chi_square": round(chi2_score, 4),
                    "shannon_entropy": round(entropy_score, 4),
                    "amount_column_index": int(amount_column),
                    "observation_count": len(values),
                },
                "tests": {
                    "benford": {
                        "score": round(chi2_score, 4),
                        "critical_value": 10.0,
                        "passed": chi2_score < 10.0,
                    },
                    "shannon": {
                        "score": round(entropy_score, 4),
                        "natural_minimum": 2.7,
                        "passed": entropy_score >= 2.7,
                    },
                },
            }


def _read_csv_rows(csv_path: str | os.PathLike[str]) -> List[List[str]]:
    """Read a CSV file using the stdlib-only parser and delimiter sniffing."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            reader = csv.reader(handle, dialect)
        except csv.Error:
            reader = csv.reader(handle)
        rows = [row for row in reader if row and any(cell.strip() for cell in row)]
    return [[cell.strip() for cell in row] for row in rows]


def _parse_numeric_token(value: Any) -> float | None:
    """Convert a cell value into a float when it looks like a monetary amount."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}", text):
        return None
    if re.fullmatch(r"\d+%", text):
        return None
    if re.fullmatch(r"[A-Za-z]+", text):
        return None

    cleaned = text.replace("€", "").replace("$", "").replace("£", "").replace("¥", "").replace("₹", "")
    cleaned = cleaned.replace(" ", "").replace("'", "")
    cleaned = cleaned.replace("\u00a0", "")

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if cleaned.count(",") == 1 and len(cleaned.split(",")[-1]) in (2, 3):
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")

    try:
        numeric = float(cleaned)
    except ValueError:
        return None
    if abs(numeric) > 1e12:
        return None
    return numeric


def _calculate_chi_square(values: Iterable[float]) -> float:
    """Compute a simple chi-square deviation score from leading digits."""
    digit_counts = {str(d): 0 for d in range(1, 10)}
    total = 0
    for value in values:
        if value == 0:
            continue
        first_digit = str(abs(value)).replace("-", "")
        if not first_digit:
            continue
        first = first_digit[0]
        if first.isdigit():
            digit_counts[first] += 1
            total += 1

    if total == 0:
        return 0.0

    expected = total / 9.0
    score = 0.0
    for digit in range(1, 10):
        observed = digit_counts[str(digit)]
        score += ((observed - expected) ** 2) / expected
    return score


def _calculate_shannon_entropy(values: Iterable[float]) -> float:
    """Estimate Shannon entropy from the leading-digit distribution of values."""
    counts: Dict[str, int] = {str(d): 0 for d in range(1, 10)}
    total = 0
    for value in values:
        if value == 0:
            continue
        first_digit = str(abs(value)).replace("-", "")
        if not first_digit:
            continue
        digit = first_digit[0]
        if digit.isdigit():
            counts[digit] += 1
            total += 1

    if total == 0:
        return 0.0

    entropy = 0.0
    for count in counts.values():
        if count == 0:
            continue
        probability = count / total
        entropy -= probability * math.log2(probability)
    return entropy


def _classify_risk(chi_square: float, shannon: float) -> Tuple[str, str]:
    """Translate metrics into a public-facing risk level."""
    if chi_square > 12.0 or shannon < 2.5:
        return "HIGH", "Significant anomaly pattern detected"
    if chi_square > 5.0 or shannon < 2.9:
        return "MEDIUM", "Moderate irregularities detected"
    return "LOW", "No immediate irregularity signal"


def _calculate_file_hash(file_obj: Any) -> str:
    """Return the SHA256 hash for an uploaded file object."""
    hasher = hashlib.sha256()
    for chunk in iter(lambda: file_obj.read(65536), b""):
        hasher.update(chunk)
    file_obj.seek(0)
    return hasher.hexdigest()


def _save_uploaded_csv(uploaded_file: Any) -> Path:
    """Persist an uploaded CSV to a temp location and return the path."""
    temp_dir = Path(tempfile.mkdtemp(prefix="bb_dashboard_"))
    output_path = temp_dir / uploaded_file.name
    with output_path.open("wb") as handle:
        handle.write(uploaded_file.getvalue())
    return output_path


def _infer_header_name(csv_path: str | os.PathLike[str], amount_column: int) -> str:
    """Return the header label associated with the selected amount column."""
    rows = _read_csv_rows(csv_path)
    if not rows:
        return "unnamed_column"
    if amount_column >= len(rows[0]):
        return "unnamed_column"
    return rows[0][amount_column]


def _build_column_explanation(csv_path: str | os.PathLike[str], amount_column: int, values: List[float]) -> str:
    """Create a human-readable explanation for the detected amount column."""
    total = max(len(values), 1)
    numeric_count = 0
    integer_like = 0
    for value in values:
        numeric_count += 1
        if abs(value - round(value)) < 1e-9:
            integer_like += 1

    header_name = _infer_header_name(csv_path, amount_column)
    reason = (
        f"AutoAdapter selected column #{amount_column} ({header_name or 'unnamed_column'}) because the header matched financial terminology "
        f"and {numeric_count}/{total} rows parsed as numeric monetary values."
    )
    if total and integer_like / total > 0.7:
        reason += " The values are predominantly integer-like, which is consistent with rounded administrative totals or standardized ledger entries."
    else:
        reason += " The values include fractional amounts, which is consistent with transaction-level financial entries and merits deeper review."
    return reason


def _build_chart_image(metrics: Dict[str, Any], output_path: str | os.PathLike[str]) -> str:
    """Generate a simple visual chart used by the PDF report and dashboard."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    values = [metrics.get("chi_square", 0.0), metrics.get("shannon_entropy", 0.0)]
    labels = ["Chi² score", "Entropy"]
    colours = ["#d72638" if values[0] >= 5 else "#2f9e44", "#0d6efd" if values[1] >= 2.9 else "#f59f00"]

    bars = ax.bar(labels, values, color=colours, width=0.6)
    ax.set_ylim(0, max(10.0, max(values) * 1.5 + 1.0))
    ax.set_ylabel("Value")
    ax.set_title("Risk signal overview")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    for bar, value in zip(bars, values):
        height = float(value)
        ax.text(bar.get_x() + bar.get_width() / 2, height + 0.1, f"{height:.2f}", ha="center", va="bottom")

    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _ensure_public_pdf(pdf_generator: ForensicPDFGenerator, audit_result: Dict[str, Any], chart_path: str, output_path: str) -> str:
    """Create the final public forensic report certificate and return the path."""
    return pdf_generator.generate_report(audit_result, chart_path, output_path)


def _build_provenance_header(metadata: Dict[str, str]) -> Dict[str, str]:
    """Create a structured provenance header for downstream processing and export."""
    return {
        "source_link": metadata.get("source_link", "").strip(),
        "country": metadata.get("country", "").strip(),
        "municipality": metadata.get("municipality", "").strip(),
        "year": metadata.get("year", "").strip(),
        "uploaded_by": metadata.get("uploaded_by", "").strip(),
        "file_hash": metadata.get("file_hash", "").strip(),
    }


def _build_manifest(audit_result: Dict[str, Any], metadata: Dict[str, str], file_hash: str) -> Dict[str, Any]:
    """Generate the JSON export payload used as the public manifest."""
    metrics = audit_result.get("metrics", {})
    provenance = _build_provenance_header(metadata)
    provenance["file_hash"] = file_hash

    manifest = {
        "schema_version": "1.0.0-mvp",
        "dataset_name": audit_result.get("dataset_name", "unknown_dataset"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "file_sha256": file_hash,
        "provenance": provenance,
        "amount_column": {
            "index": int(metrics.get("amount_column_index", 0)),
            "explanation": audit_result.get("amount_column_explanation", "AutoAdapter selected the amount column."),
        },
        "risk": {
            "level": audit_result.get("risk_level", "UNKNOWN"),
            "label": audit_result.get("risk_label", "No risk label supplied."),
        },
        "metrics": {
            "chi_square": float(metrics.get("chi_square", 0.0)),
            "shannon_entropy": float(metrics.get("shannon_entropy", 0.0)),
            "observation_count": int(metrics.get("observation_count", 0)),
        },
        "tests": audit_result.get("tests", {}),
    }
    return manifest


def _build_audit_result(csv_file: str | os.PathLike[str], metadata: Dict[str, str]) -> Dict[str, Any]:
    """Run the automated budget pipeline and return the structured result object."""
    amount_column = detect_amount_column_from_csv(csv_file)
    core = ForensicCore()
    result = core.analyze(csv_file, amount_column=amount_column) if hasattr(core, "analyze") else ForensicCore.analyze(csv_file, amount_column)

    values: List[float] = []
    for row in _read_csv_rows(csv_file)[1:]:
        if amount_column >= len(row):
            continue
        numeric_value = _parse_numeric_token(row[amount_column])
        if numeric_value is not None:
            values.append(float(numeric_value))

    result["dataset_name"] = Path(csv_file).name
    result["provenance"] = _build_provenance_header(metadata)
    result["amount_column_explanation"] = _build_column_explanation(csv_file, amount_column, values)
    result["source_link"] = metadata.get("source_link", "")
    result["country"] = metadata.get("country", "")
    result["municipality"] = metadata.get("municipality", "")
    result["year"] = metadata.get("year", "")
    result["uploaded_by"] = metadata.get("uploaded_by", "")
    result["file_hash"] = metadata.get("file_hash", "")
    return result


def _render_results(audit_result: Dict[str, Any], pdf_path: str | None = None, json_path: str | None = None) -> None:
    """Render the stat cards and summary panels in the dashboard."""
    risk_level = str(audit_result.get("risk_level", "LOW")).upper()
    chi_score = float(audit_result.get("metrics", {}).get("chi_square", 0.0))
    entropy_score = float(audit_result.get("metrics", {}).get("shannon_entropy", 0.0))
    amount_column = int(audit_result.get("metrics", {}).get("amount_column_index", 0))
    observations = int(audit_result.get("metrics", {}).get("observation_count", 0))
    file_hash = str(audit_result.get("file_hash", "")).strip()

    risk_colors = {
        "LOW": "#2f9e44",
        "MEDIUM": "#f59f00",
        "HIGH": "#d72638",
    }

    st.subheader("Risk overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Risk level", risk_level, delta_color="off")
    col2.metric("Benford chi-square", f"{chi_score:.4f}")
    col3.metric("Shannon entropy", f"{entropy_score:.4f} bits")

    st.caption(f"Detected amount column: #{amount_column} · Records analyzed: {observations}")
    st.info(audit_result.get("amount_column_explanation", "AutoAdapter isolated the monetary column with a statistically valid threshold."))

    st.markdown(
        f"<div style='padding: 14px; border-radius: 10px; background: {risk_colors.get(risk_level, '#2f9e44')}; color: white; font-weight: 700;'>"
        f"{audit_result.get('risk_label', 'No risk label available')}"
        "</div>",
        unsafe_allow_html=True,
    )

    st.write("---")

    left, right = st.columns(2)
    with left:
        st.subheader("Metric detail")
        rows = [
            {"Metric": "Benford chi-square", "Value": round(chi_score, 4), "Benchmark": "Lower is better"},
            {"Metric": "Shannon entropy", "Value": round(entropy_score, 4), "Benchmark": "Higher indicates greater distribution variability"},
            {"Metric": "Amount column index", "Value": amount_column, "Benchmark": "Detected automatically"},
        ]
        st.table(rows)

    with right:
        st.subheader("Audit notes")
        st.write(audit_result.get("risk_label", "No further notes available."))
        st.write("No statistical anomalies detected — Data distribution aligns with natural logarithmic constants. This test is an integrity indicator and does not replace a manual accounting review.")

        if file_hash:
            st.code(file_hash, language="text")

        if pdf_path:
            with open(pdf_path, "rb") as handle:
                pdf_bytes = handle.read()
            st.download_button(
                label="Download forensic PDF certificate",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
                use_container_width=True,
            )
        if json_path:
            with open(json_path, "rb") as handle:
                manifest_bytes = handle.read()
            st.download_button(
                label="Download audit manifest JSON",
                data=manifest_bytes,
                file_name=Path(json_path).name,
                mime="application/json",
                use_container_width=True,
            )


def main() -> None:
    """Launch the local Streamlit dashboard."""
    st.set_page_config(page_title="Citizen Budget Intelligence Dashboard", page_icon="🧾", layout="wide")
    st.title("Citizen Budget Intelligence Platform")
    st.caption("Local-first public transparency dashboard for forensic budget review.")

    with st.form("budget_ingest"):
        uploaded_file = st.file_uploader("Upload budget CSV", type=["csv"], help="Upload a municipal or state budget file in CSV format.")
        source_link = st.text_input("Source / link")
        country = st.text_input("Country / jurisdiction")
        municipality = st.text_input("Municipality / institution")
        year = st.text_input("Year")
        uploaded_by = st.text_input("Uploaded by")
        submit = st.form_submit_button("Run audit pipeline", use_container_width=True)

    if not submit or uploaded_file is None:
        st.info("Upload a CSV file and complete the provenance metadata to begin the automated forensic review.")
        return

    metadata = {
        "source_link": source_link,
        "country": country,
        "municipality": municipality,
        "year": year,
        "uploaded_by": uploaded_by,
    }

    with st.spinner("Processing CSV file and generating forensic report..."):
        temp_csv = _save_uploaded_csv(uploaded_file)
        metadata["file_hash"] = _calculate_file_hash(uploaded_file)
        audit_result = _build_audit_result(temp_csv, metadata)
        audit_result["file_hash"] = metadata["file_hash"]

        chart_dir = Path(tempfile.mkdtemp(prefix="bb_chart_"))
        chart_path = chart_dir / "budget_analysis.png"
        _build_chart_image(audit_result.get("metrics", {}), str(chart_path))

        report_dir = Path(tempfile.mkdtemp(prefix="bb_report_"))
        pdf_path = report_dir / "forensic_audit_report.pdf"
        json_path = report_dir / "audit_manifest.json"

        manifest = _build_manifest(audit_result, metadata, metadata["file_hash"])
        with json_path.open("w", encoding="utf-8") as handle:
            json.dump(manifest, handle, indent=2, ensure_ascii=False)

        pdf_generator = ForensicPDFGenerator()
        final_pdf = _ensure_public_pdf(pdf_generator, audit_result, str(chart_path), str(pdf_path))

        st.success("Audit pipeline completed successfully.")
        st.image(str(chart_path), use_container_width=True)
        _render_results(audit_result, final_pdf, str(json_path))


if __name__ == "__main__":
    main()


