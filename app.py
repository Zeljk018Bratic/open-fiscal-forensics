"""Streamlit Milestone v2.0 dashboard for the Open Fiscal Forensics Framework."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from auto_adapter import detect_amount_column_from_csv
from database_registry import DatabaseRegistry
from pdf_generator import ForensicPDFGenerator

# Soft import of the P2P mesh engine (Phase 2)
try:
    from p2p_network_mesh import P2PNetworkMesh
    MESH_AVAILABLE = True
except ImportError:
    P2PNetworkMesh = None
    MESH_AVAILABLE = False

try:
    from forensic_core import ForensicCore
except ImportError:
    class ForensicCore:
        """Local compatibility shim for forensic evaluation."""

        @staticmethod
        def analyze(values: List[float], label: str = "Audit") -> Dict[str, Any]:
            """Analyze a pre-parsed list of float values directly to fix zero scores."""
            if not values:
                raise ValueError("No numeric values provided for forensic analysis.")

            chi2_score = _calculate_chi_square(values)
            entropy_score = _calculate_shannon_entropy(values)
            risk_level, risk_label = _classify_risk(chi2_score, entropy_score)

            return {
                "label": label,
                "risk_level": risk_level,
                "risk_label": risk_label,
                "metrics": {
                    "chi_square": round(chi2_score, 4),
                    "shannon_entropy": round(entropy_score, 4),
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



# ---------------------------------------------------------------------------
# Pure-Python helpers (unchanged from v1.2)
# ---------------------------------------------------------------------------


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

    cleaned = (
        text.replace("€", "")
        .replace("$", "")
        .replace("£", "")
        .replace("¥", "")
        .replace("₹", "")
    )
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
    """Compute a simple chi-square deviation score from leading digits (1-9 only)."""
    digit_counts = {str(d): 0 for d in range(1, 10)}
    total = 0
    for value in values:
        if value == 0:
            continue
        clean_str = f"{abs(value):.10f}".replace(".", "").lstrip("0")
        if not clean_str:
            continue
        first = clean_str[0]
        if first in digit_counts:
            digit_counts[first] += 1
            total += 1

    if total == 0:
        return 0.0

    expected_pct = [0, 0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]
    score = 0.0
    for digit in range(1, 10):
        observed = digit_counts[str(digit)]
        exp = total * expected_pct[digit]
        if exp > 0:
            score += ((observed - exp) ** 2) / exp
    return score


def _calculate_shannon_entropy(values: Iterable[float]) -> float:
    """Estimate Shannon entropy from the leading-digit distribution (1-9 only)."""
    counts: Dict[str, int] = {str(d): 0 for d in range(1, 10)}
    total = 0
    for value in values:
        if value == 0:
            continue
        clean_str = f"{abs(value):.10f}".replace(".", "").lstrip("0")
        if not clean_str:
            continue
        digit = clean_str[0]
        if digit in counts:
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


def _build_column_explanation(
    csv_path: str | os.PathLike[str], amount_column: int, values: List[float]
) -> str:
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


def _build_chart_image(
    metrics: Dict[str, Any], output_path: str | os.PathLike[str]
) -> str:
    """Generate a simple visual chart used by the PDF report and dashboard."""
    fig, ax = plt.subplots(figsize=(8, 4.4))
    values = [metrics.get("chi_square", 0.0), metrics.get("shannon_entropy", 0.0)]
    labels = ["Chi² score", "Entropy"]
    colours = [
        "#d72638" if values[0] >= 5 else "#2f9e44",
        "#0d6efd" if values[1] >= 2.9 else "#f59f00",
    ]

    bars = ax.bar(labels, values, color=colours, width=0.6)
    ax.set_ylim(0, max(10.0, max(values) * 1.5 + 1.0))
    ax.set_ylabel("Value")
    ax.set_title("Risk signal overview")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    for bar, value in zip(bars, values):
        height = float(value)
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.1,
            f"{height:.2f}",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()
    fig.savefig(output_path, dpi=180)
    plt.close(fig)
    return str(output_path)


def _ensure_public_pdf(
    pdf_generator: ForensicPDFGenerator,
    audit_result: Dict[str, Any],
    chart_path: str,
    output_path: str,
) -> str:
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


def _build_manifest(
    audit_result: Dict[str, Any], metadata: Dict[str, str], file_hash: str
) -> Dict[str, Any]:
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
            "explanation": audit_result.get(
                "amount_column_explanation",
                "AutoAdapter selected the amount column.",
            ),
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


def _build_audit_result(
    csv_file: str | os.PathLike[str], metadata: Dict[str, str]
) -> Dict[str, Any]:
    """Run the automated budget pipeline and return the structured result object."""
    amount_column = detect_amount_column_from_csv(csv_file)

    # 1) Parse clean numeric values first
    values: List[float] = []
    for row in _read_csv_rows(csv_file)[1:]:
        if amount_column >= len(row):
            continue
        numeric_value = _parse_numeric_token(row[amount_column])
        if numeric_value is not None:
            values.append(float(numeric_value))

    if not values:
        raise ValueError(
            f"No valid numeric monetary transactions found in column #{amount_column}"
        )

    label = metadata.get("municipality", "").strip() or "Audit"
    core = ForensicCore()

    # 2) Signature-safe analyze calls
    try:
        result = core.analyze(values, label=label)
    except TypeError:
        result = core.analyze(values)

    # 3) Attach metadata
    result["dataset_name"] = Path(csv_file).name
    result["provenance"] = _build_provenance_header(metadata)
    result["amount_column_explanation"] = _build_column_explanation(
        csv_file, amount_column, values
    )
    result["source_link"] = metadata.get("source_link", "")
    result["country"] = metadata.get("country", "")
    result["municipality"] = metadata.get("municipality", "")
    result["year"] = metadata.get("year", "")
    result["uploaded_by"] = metadata.get("uploaded_by", "")
    result["file_hash"] = metadata.get("file_hash", "")

    # 4) Ensure UI metrics are always present (Mapped exactly to your production tests)
    metrics = result.setdefault("metrics", {})
    
    # Izvlačimo tvoje stvarne rezultate iz rečnika tests
    tests_dict = result.get("tests", {})
    benford_score = tests_dict.get("benford", {}).get("score", 0.0)
    shannon_score = tests_dict.get("shannon", {}).get("score", 0.0)
    
    metrics["chi_square"] = float(benford_score)
    metrics["shannon_entropy"] = float(shannon_score)
    metrics.setdefault("amount_column_index", int(amount_column))
    metrics.setdefault("observation_count", len(values))

    return result



def _render_results(
    audit_result: Dict[str, Any],
    pdf_path: str | None = None,
    json_path: str | None = None,
) -> None:
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

    audit_notes_map = {
        "HIGH": (
            "⚠️ **CRITICAL FINDINGS DETECTED**\n\n"
            "The forensic analysis has identified a statistically significant anomaly pattern in this dataset. "
            "First-digit distribution and entropy measurements deviate substantially from Benford's Law expectations. "
            "This suggests either: (1) potential data fabrication or manual rounding, (2) genuine structural anomalies in the financial records, "
            "or (3) domain-specific legitimate patterns warranting human expert review. "
            "**Manual auditor verification is strongly recommended before publication or policy action.**"
        ),
        "MEDIUM": (
            "⚡ **MODERATE IRREGULARITIES DETECTED**\n\n"
            "The analysis has identified moderate deviations from Benford's Law baseline expectations. "
            "While not critical, these irregularities warrant closer examination by a financial auditor. "
            "The dataset shows patterns consistent with either natural variation or minor data quality issues. "
            "Consider performing targeted spot-checks on high-value transactions and date-range analysis."
        ),
        "LOW": (
            "✓ **INTEGRITY INDICATORS PASS**\n\n"
            "Statistical analysis shows no immediate anomaly signals. First-digit distribution aligns with Benford's Law expectations, "
            "and Shannon entropy remains within natural ranges. Data distribution appears consistent with authentic financial records. "
            "**Important:** This test is a mathematical integrity indicator and does not replace manual accounting review or institutional audit protocols."
        ),
    }

    st.subheader("Risk overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Risk level", risk_level, delta_color="off")
    col2.metric("Benford chi-square", f"{chi_score:.4f}")
    col3.metric("Shannon entropy", f"{entropy_score:.4f} bits")

    st.caption(f"Detected amount column: #{amount_column} · Records analyzed: {observations}")
    st.info(
        audit_result.get(
            "amount_column_explanation",
            "AutoAdapter isolated the monetary column with a statistically valid threshold.",
        )
    )

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

        html_table = f"""
        <table style="
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
            border: 1px solid #dfe2e6;
            border-radius: 8px;
            overflow: hidden;
        ">
            <thead>
                <tr style="background-color: #f8f9fa;">
                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #dfe2e6;">Metric</th>
                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #dfe2e6;">Value</th>
                    <th style="text-align: left; padding: 10px; border-bottom: 1px solid #dfe2e6;">Benchmark</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2;">Benford chi-square</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2; font-family: monospace;">{chi_score:.4f}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2;">Lower is better</td>
                </tr>
                <tr style="background-color: #fcfcfd;">
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2;">Shannon entropy</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2; font-family: monospace;">{entropy_score:.4f}</td>
                    <td style="padding: 10px; border-bottom: 1px solid #eef0f2;">Higher indicates greater distribution variability</td>
                </tr>
                <tr>
                    <td style="padding: 10px;">Amount column index</td>
                    <td style="padding: 10px; font-family: monospace;">#{amount_column}</td>
                    <td style="padding: 10px;">Detected automatically</td>
                </tr>
            </tbody>
        </table>
        """
        st.markdown(html_table, unsafe_allow_html=True)

    with right:
        st.subheader("Audit notes")
        st.markdown(audit_notes_map.get(risk_level, audit_notes_map["LOW"]))

        if file_hash:
            st.divider()
            st.markdown("**Dataset Hash (SHA256)**")
            st.code(file_hash, language="text")

        if pdf_path or json_path:
            st.divider()
            st.markdown("**Export & Download**")

        if pdf_path:
            with open(pdf_path, "rb") as handle:
                pdf_bytes = handle.read()
            st.download_button(
                label="📄 Download forensic PDF certificate",
                data=pdf_bytes,
                file_name=Path(pdf_path).name,
                mime="application/pdf",
                use_container_width=True,
            )
        if json_path:
            with open(json_path, "rb") as handle:
                manifest_bytes = handle.read()
            st.download_button(
                label="📋 Download audit manifest JSON",
                data=manifest_bytes,
                file_name=Path(json_path).name,
                mime="application/json",
                use_container_width=True,
            )


def _get_last_audit_metadata(db: DatabaseRegistry) -> Dict[str, str]:
    """Fetch the most recent audit's provenance metadata from the registry for form auto-population fallback."""
    try:
        last_audits = db.fetch_all_audits(limit=1)
        if last_audits:
            audit = last_audits[0]
            manifest = audit.get("manifest", {})
            provenance = manifest.get("provenance", {})
            return {
                "source_link": provenance.get("source_link", ""),
                "country": provenance.get("country", ""),
                "municipality": provenance.get("municipality", ""),
                "year": provenance.get("year", ""),
                "uploaded_by": provenance.get("uploaded_by", ""),
            }
    except Exception:
        pass
    return {
        "source_link": "",
        "country": "",
        "municipality": "",
        "year": "",
        "uploaded_by": "",
    }


def _render_audit_registry(db: DatabaseRegistry) -> None:
    """Render the historical audit registry tab."""
    st.subheader("Registry Statistics")

    total_count = db.get_audit_count()
    risk_summary = db.get_risk_summary()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total audits", total_count)
    col2.metric("🔴 High risk", risk_summary.get("HIGH", 0))
    col3.metric("🟡 Medium risk", risk_summary.get("MEDIUM", 0))
    col4.metric("🟢 Low risk", risk_summary.get("LOW", 0))

    st.write("---")

    if total_count == 0:
        st.info(
            "No audits have been registered yet. Upload and process a CSV to begin building the historical registry."
        )
        return

    st.subheader("Filter & Search")
    filter_col1, filter_col2 = st.columns(2)

    with filter_col1:
        filter_risk = st.selectbox(
            "Filter by risk level", ["All", "HIGH", "MEDIUM", "LOW"], key="filter_risk"
        )

    with filter_col2:
        limit_records = st.number_input(
            "Limit records displayed", min_value=1, max_value=1000, value=50, step=10
        )

    if filter_risk == "All":
        audits = db.fetch_all_audits(limit=limit_records)
    else:
        audits = db.fetch_audits_by_risk_level(filter_risk)
        audits = audits[:limit_records]

    if not audits:
        st.warning(f"No audits found with risk level: {filter_risk}")
        return

    st.subheader(f"Audit Records ({len(audits)})")

    for idx, audit in enumerate(audits, start=1):
        with st.expander(
            f"#{audit['id']} · {audit['dataset_name']} · {audit['risk_level']} · {audit['country'] or 'N/A'} · {audit['audit_year'] or 'N/A'}"
        ):
            col1, col2, col3 = st.columns(3)
            col1.metric("Risk level", audit["risk_level"], delta_color="off")
            col2.metric("Chi² score", f"{audit['chi_square']:.4f}")
            col3.metric("Shannon entropy", f"{audit['shannon_entropy']:.4f}")

            st.markdown("**Provenance**")
            prov_cols = st.columns(2)
            with prov_cols[0]:
                st.write(f"**Country:** {audit['country'] or 'N/A'}")
                st.write(f"**Municipality:** {audit['municipality'] or 'N/A'}")
                st.write(f"**Year:** {audit['audit_year'] or 'N/A'}")
            with prov_cols[1]:
                st.write(f"**Uploaded by:** {audit['uploaded_by'] or 'N/A'}")
                st.write(f"**Source:** {audit['source_link'] or 'N/A'}")

            st.markdown("**Analysis Metrics**")
            metric_cols = st.columns(3)
            with metric_cols[0]:
                st.write(f"**Observations:** {audit['observation_count']}")
            with metric_cols[1]:
                st.write(f"**Amount column:** #{audit['amount_column_index']}")
            with metric_cols[2]:
                benford_status = "✓ Passed" if audit["benford_passed"] else "✗ Failed"
                shannon_status = "✓ Passed" if audit["shannon_passed"] else "✗ Failed"
                st.write(f"**Benford:** {benford_status}")
                st.write(f"**Shannon:** {shannon_status}")

            st.markdown("**Timestamps**")
            ts_cols = st.columns(2)
            with ts_cols[0]:
                st.caption(f"**Audit:** {audit['generated_at_utc'][:19]}")
            with ts_cols[1]:
                st.caption(f"**Registered:** {audit['registered_at_utc'][:19]}")

            st.markdown("**Dataset Hash**")
            st.code(audit["file_sha256"], language="text")

            with st.expander("View full manifest (JSON)"):
                st.json(audit.get("manifest", {}))


# ---------------------------------------------------------------------------
# Phase 3 — Mesh Validation Network tab (Lazy-Polling)
# ---------------------------------------------------------------------------


def _ensure_mesh_node(port: int = 6001) -> Optional[Any]:
    """
    Lazily create or return the P2PNetworkMesh instance stored in session_state.
    The node object lives across Streamlit reruns; network work stays in daemon threads.
    """
    if not MESH_AVAILABLE or P2PNetworkMesh is None:
        return None

    if "mesh_node" not in st.session_state or st.session_state.mesh_node is None:
        st.session_state.mesh_node = P2PNetworkMesh(
            host="127.0.0.1",
            port=port,
            node_id=f"Node_{secrets_token_hex_safe()}",
        )
    return st.session_state.mesh_node


def secrets_token_hex_safe(nbytes: int = 4) -> str:
    """Tiny helper so we do not need to import secrets at module level for the fallback path."""
    import secrets

    return secrets.token_hex(nbytes)


def _render_mesh_tab() -> None:
    """
    Third tab: 🌐 Mesh Validation Network
    Thread-safe node control + live telemetry via Lazy-Polling.
    """
    st.subheader("🌐 Mesh Validation Network")
    st.caption(
        "Secure GossipSub transport layer · stdlib-only · HMAC-SHA256 signed packets · "
        "bounded seen-set · automatic dead-peer pruning"
    )

    if not MESH_AVAILABLE:
        st.error(
            "P2PNetworkMesh module not found. Place the validated `p2p_network_mesh.py` "
            "from Phase 2 next to `app.py` and restart the dashboard."
        )
        return

    # ---- Node control panel ----
    st.markdown("### Node Control")
    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])

    with ctrl_col1:
        listen_port = st.number_input(
            "Local listener port",
            min_value=1024,
            max_value=65535,
            value=int(st.session_state.get("mesh_port", 6001)),
            step=1,
            key="mesh_port_input",
        )
        st.session_state.mesh_port = listen_port

    node = _ensure_mesh_node(port=int(listen_port))

    with ctrl_col2:
        if st.button("▶️ Start P2P Engine", use_container_width=True, type="primary"):
            if node is not None:
                # Recreate if port changed
                if getattr(node, "port", None) != int(listen_port) or not node.is_active:
                    if node.is_active:
                        node.stop_node()
                    st.session_state.mesh_node = P2PNetworkMesh(
                        host="127.0.0.1",
                        port=int(listen_port),
                        node_id=node.node_id,
                    )
                    node = st.session_state.mesh_node
                node.start_node()
                st.success(f"Engine active on 127.0.0.1:{listen_port}")
                st.rerun()

    with ctrl_col3:
        if st.button("⏹ Stop P2P Engine", use_container_width=True):
            if node is not None and node.is_active:
                node.stop_node()
                st.info("Engine stopped.")
                st.rerun()

    # ---- Telemetry grid (from node.status()) ----
    st.markdown("### Live Telemetry")
    if node is None:
        st.warning("Mesh node not initialised.")
        return

    status = node.status()
    is_active = status.get("is_active", False)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Node ID", status.get("node_id", "—"))
    m2.metric("Engine", "🟢 ACTIVE" if is_active else "🔴 OFFLINE")
    m3.metric("Connected peers", status.get("peer_count", 0))
    m4.metric("Seen messages", status.get("seen_messages", 0))

    # Peer table (native HTML, no pandas)
    peers = status.get("peers", [])
    if peers:
        st.markdown("#### Active Peers")
        rows_html = ""
        for p in peers:
            rows_html += (
                f"<tr>"
                f"<td style='padding:8px;border-bottom:1px solid #eef0f2;font-family:monospace;'>{p.get('node_id','?')}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eef0f2;'>{p.get('host','?')}:{p.get('port','?')}</td>"
                f"<td style='padding:8px;border-bottom:1px solid #eef0f2;'>{p.get('last_seen_ago_sec','?')} s ago</td>"
                f"</tr>"
            )
        peer_table = f"""
        <table style="width:100%;border-collapse:collapse;font-size:0.9rem;border:1px solid #dfe2e6;border-radius:8px;overflow:hidden;">
            <thead>
                <tr style="background:#f8f9fa;">
                    <th style="text-align:left;padding:10px;border-bottom:1px solid #dfe2e6;">Node ID</th>
                    <th style="text-align:left;padding:10px;border-bottom:1px solid #dfe2e6;">Address</th>
                    <th style="text-align:left;padding:10px;border-bottom:1px solid #dfe2e6;">Last seen</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
        """
        st.markdown(peer_table, unsafe_allow_html=True)
    else:
        st.caption(
            "No active peers yet. Use **Connect to peer** below or wait for inbound connections."
        )

    # Manual peer connection
    with st.expander("🔗 Connect to remote peer"):
        peer_host = st.text_input("Peer host", value="127.0.0.1", key="peer_host_input")
        peer_port = st.number_input(
            "Peer port", min_value=1024, max_value=65535, value=6002, key="peer_port_input"
        )
        if st.button("Connect", key="connect_peer_btn"):
            if node.is_active:
                ok = node.connect_to_peer(peer_host, int(peer_port))
                if ok:
                    st.success(f"Connected to {peer_host}:{peer_port}")
                else:
                    st.error("Connection failed.")
                st.rerun()
            else:
                st.warning("Start the P2P engine first.")

    st.write("---")

    # ---- Incoming gossip stream (drain_inbox) ----
    st.markdown("### Incoming Gossip Stream")
    refresh_col, clear_col = st.columns([1, 1])
    with refresh_col:
        if st.button("🔄 Refresh inbox", use_container_width=True):
            st.rerun()
    with clear_col:
        if st.button("🗑 Clear local history view", use_container_width=True):
            st.session_state.mesh_history = []
            st.rerun()

    # Accumulate history in session_state so the operator can review past packets
    if "mesh_history" not in st.session_state:
        st.session_state.mesh_history = []

    if node.is_active:
        new_packets = node.drain_inbox()
        for pkt in new_packets:
            st.session_state.mesh_history.append(pkt)
        # Keep a bounded local view
        if len(st.session_state.mesh_history) > 200:
            st.session_state.mesh_history = st.session_state.mesh_history[-200:]

    history = st.session_state.mesh_history
    if not history:
        st.info(
            "Inbox empty. When other validators broadcast AUDIT_MANIFEST or ATTESTATION packets they will appear here."
        )
    else:
        st.caption(f"Showing last {len(history)} packets (newest first)")
        for pkt in reversed(history[-50:]):  # newest first, limited display
            mtype = pkt.get("message_type", "?")
            sender = pkt.get("sender_node", "?")
            ts = pkt.get("timestamp_utc", "")[:19]
            msg_id = pkt.get("msg_id", "")[:18]

            icon = {"AUDIT_MANIFEST": "📦", "ATTESTATION": "🗳️", "HEARTBEAT": "💓"}.get(
                mtype, "📨"
            )
            title = f"{icon} {mtype} · {sender} · {ts}"

            with st.expander(title):
                if mtype == "AUDIT_MANIFEST":
                    payload = pkt.get("payload", {})
                    st.markdown(
                        f"**Municipality:** {payload.get('municipality', '—')}  \n"
                        f"**Year:** {payload.get('year', '—')}  \n"
                        f"**Chi²:** `{payload.get('chi_square', '—')}`  \n"
                        f"**Entropy:** `{payload.get('shannon_entropy', '—')}`  \n"
                        f"**Risk:** `{payload.get('risk_level', '—')}`  \n"
                        f"**File SHA-256:** `{pkt.get('file_sha256', '—')}`"
                    )
                elif mtype == "ATTESTATION":
                    payload = pkt.get("payload", {})
                    vote = payload.get("vote", "?")
                    colour = "#2f9e44" if vote == "AGREE" else "#d72638"
                    st.markdown(
                        f"<span style='color:{colour};font-weight:700;'>Vote: {vote}</span>  \n"
                        f"**Target msg:** `{payload.get('target_msg_id', '—')}`  \n"
                        f"**File SHA-256:** `{payload.get('file_sha256', '—')}`  \n"
                        f"**Reason:** {payload.get('reason', '—')}",
                        unsafe_allow_html=True,
                    )
                else:
                    st.json(pkt)

                st.caption(
                    f"msg_id: {msg_id}… · ttl={pkt.get('ttl')} · version={pkt.get('version')}"
                )


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------


def main() -> None:
    """Launch the Milestone v2.0 Streamlit dashboard with three-tab architecture."""
    st.set_page_config(
        page_title="Citizen Budget Intelligence Platform (v2.0)",
        page_icon="🧾",
        layout="wide",
    )

    st.title("Citizen Budget Intelligence Platform")
    st.caption(
        "Milestone v2.0 · Local-first public transparency dashboard · "
        "Forensic budget review · Persistent registry · Decentralized validation mesh"
    )

    # Initialize database
    db = DatabaseRegistry("audit_registry.db")

    # Fetch last audit metadata as fallback for form auto-population
    last_audit_metadata = _get_last_audit_metadata(db)

    # Session-state defaults
    st.session_state.setdefault(
        "source_link", last_audit_metadata.get("source_link", "")
    )
    st.session_state.setdefault("country", last_audit_metadata.get("country", ""))
    st.session_state.setdefault(
        "municipality", last_audit_metadata.get("municipality", "")
    )
    st.session_state.setdefault("year", last_audit_metadata.get("year", ""))
    st.session_state.setdefault(
        "uploaded_by", last_audit_metadata.get("uploaded_by", "")
    )
    st.session_state.setdefault("uploaded_file", None)
    st.session_state.setdefault("mesh_port", 6001)
    st.session_state.setdefault("mesh_node", None)
    st.session_state.setdefault("mesh_history", [])

    # Three main tabs
    tab_live, tab_registry, tab_mesh = st.tabs(
        [
            "📊 Live Budget Pipeline",
            "📜 Historical Audit Registry",
            "🌐 Mesh Validation Network",
        ]
    )

    # ------------------------------------------------------------------
    # Tab 1 — Live Budget Pipeline
    # ------------------------------------------------------------------
    with tab_live:
        st.subheader("Upload & Process Budget Data")

        with st.form("budget_ingest"):
            uploaded_file = st.file_uploader(
                "Upload budget CSV",
                type=["csv"],
                help="Upload a municipal or state budget file in CSV format.",
            )
            st.text_input(
                "Source / link",
                key="source_link",
                help="Link to the budget source document or public portal",
            )
            st.text_input(
                "Country / jurisdiction",
                key="country",
                help="Country or jurisdiction name",
            )
            st.text_input(
                "Municipality / institution",
                key="municipality",
                help="Municipality or institution name",
            )
            st.text_input("Year", key="year", help="Budget year or fiscal period")
            st.text_input(
                "Uploaded by", key="uploaded_by", help="Name or identifier of uploader"
            )
            submit = st.form_submit_button(
                "Run audit pipeline", use_container_width=True
            )

        if not submit or uploaded_file is None:
            st.info(
                "Upload a CSV file and complete the provenance metadata to begin the automated forensic review."
            )
        else:
            metadata = {
                "source_link": st.session_state.source_link,
                "country": st.session_state.country,
                "municipality": st.session_state.municipality,
                "year": st.session_state.year,
                "uploaded_by": st.session_state.uploaded_by,
            }

            with st.spinner("Processing CSV file and generating forensic report..."):
                temp_csv = _save_uploaded_csv(uploaded_file)
                metadata["file_hash"] = _calculate_file_hash(uploaded_file)
                audit_result = _build_audit_result(temp_csv, metadata)
                audit_result["file_hash"] = metadata["file_hash"]

                # Generate chart
                chart_dir = Path(tempfile.mkdtemp(prefix="bb_chart_"))
                chart_path = chart_dir / "budget_analysis.png"
                _build_chart_image(audit_result.get("metrics", {}), str(chart_path))

                # Generate manifest and persist
                report_dir = Path(tempfile.mkdtemp(prefix="bb_report_"))
                pdf_path = report_dir / "forensic_audit_report.pdf"
                json_path = report_dir / "audit_manifest.json"

                manifest = _build_manifest(
                    audit_result, metadata, metadata["file_hash"]
                )

                # Write manifest to JSON
                with json_path.open("w", encoding="utf-8") as handle:
                    json.dump(manifest, handle, indent=2, ensure_ascii=False)

                # Persist manifest to database registry
                try:
                    audit_id = db.register_audit(manifest)
                    st.success(f"✓ Audit persisted to registry (ID: {audit_id})")
                except Exception as e:
                    st.error(f"Failed to persist audit to registry: {e}")

                # ---- Phase 3: Automated Gossip Fanout ----
                node = st.session_state.get("mesh_node")
                if (
                    MESH_AVAILABLE
                    and node is not None
                    and getattr(node, "is_active", False)
                ):
                    try:
                        metrics = audit_result.get("metrics", {})
                        gossip_pkt = node.build_audit_manifest(
                            file_sha256=metadata["file_hash"],
                            municipality=metadata.get("municipality") or "Unknown",
                            year=metadata.get("year") or "",
                            chi_square=float(metrics.get("chi_square", 0.0)),
                            shannon_entropy=float(
                                metrics.get("shannon_entropy", 0.0)
                            ),
                            risk_level=str(audit_result.get("risk_level", "UNKNOWN")),
                        )
                        sent = node.broadcast_gossip(gossip_pkt)
                        st.info(
                            f"📡 AUDIT_MANIFEST broadcast to mesh ({sent} peer(s) reached)"
                        )
                    except Exception as exc:
                        st.warning(f"Mesh broadcast skipped: {exc}")

                # Generate PDF
                pdf_generator = ForensicPDFGenerator()
                final_pdf = _ensure_public_pdf(
                    pdf_generator, audit_result, str(chart_path), str(pdf_path)
                )

                st.success("Audit pipeline completed successfully.")
                st.image(str(chart_path), use_container_width=True)
                _render_results(audit_result, final_pdf, str(json_path))

    # ------------------------------------------------------------------
    # Tab 2 — Historical Audit Registry
    # ------------------------------------------------------------------
    with tab_registry:
        st.subheader("Historical Audit Registry")
        _render_audit_registry(db)

    # ------------------------------------------------------------------
    # Tab 3 — Mesh Validation Network
    # ------------------------------------------------------------------
    with tab_mesh:
        _render_mesh_tab()


if __name__ == "__main__":
    main()
