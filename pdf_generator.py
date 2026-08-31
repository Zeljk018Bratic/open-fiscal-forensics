"""
Open Fiscal Forensics Framework (OFFF)
ForensicPDFGenerator — Milestone v2.0 Production Certificate Engine

Generates a sterile, high-contrast institutional PDF audit certificate.
Strictly limited to the reportlab standard library (no extra dependencies).
Fully compatible with Windows Smart App Control.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Image,
    Table,
    TableStyle,
    KeepTogether,
    HRFlowable,
)


class ForensicPDFGenerator:
    """Sterile, institutional forensic audit certificate generator."""

    def __init__(self) -> None:
        self.styles = getSampleStyleSheet()

        # Dark institutional header title
        self.title_style = ParagraphStyle(
            "DocTitle",
            parent=self.styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.white,
            spaceAfter=4,
            alignment=0,
        )

        # Section headers (accent red)
        self.section_style = ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#ff0055"),
            spaceBefore=14,
            spaceAfter=6,
        )

        # Body text
        self.body_style = ParagraphStyle(
            "DocBody",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#222222"),
        )

        # Small mono-style for hashes
        self.mono_style = ParagraphStyle(
            "MonoHash",
            parent=self.styles["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#111111"),
        )

        # Footer / integrity statement
        self.footer_style = ParagraphStyle(
            "Footer",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555"),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_report(
        self,
        audit_result: Dict[str, Any],
        chart_path: str,
        output_pdf: str = "forensic_audit_report.pdf",
    ) -> str:
        """
        Build a complete forensic audit certificate PDF.

        Parameters
        ----------
        audit_result : dict
            Full result object produced by the analysis pipeline
            (must contain risk_level, risk_label, metrics, tests,
             and optionally provenance / file_hash / dataset_name).
        chart_path : str
            Path to the risk-signal PNG chart.
        output_pdf : str
            Destination file path.

        Returns
        -------
        str
            Absolute path of the written PDF.
        """
        print(f"📄 [PDF-Generator] Generating forensic certificate → {output_pdf}")

        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        story = []

        # --------------------------------------------------------------
        # 1. STERILE DARK HEADER
        # --------------------------------------------------------------
        header_data = [
            [
                Paragraph("FORENSIC AUDIT CERTIFICATE", self.title_style),
            ]
        ]
        header_table = Table(header_data, colWidths=[540])
        header_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#111111")),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                    ("TOPPADDING", (0, 0), (-1, -1), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
                    ("LEFTPADDING", (0, 0), (-1, -1), 16),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(header_table)
        story.append(Spacer(1, 12))

        # Dataset + Risk line
        dataset_name = (
            audit_result.get("dataset_name")
            or audit_result.get("label")
            or "Unknown Dataset"
        )
        risk_level = str(audit_result.get("risk_level", "UNKNOWN")).upper()
        risk_label = audit_result.get("risk_label", "")

        risk_color = {
            "HIGH": colors.HexColor("#d72638"),
            "MEDIUM": colors.HexColor("#f59f00"),
            "LOW": colors.HexColor("#2f9e44"),
        }.get(risk_level, colors.HexColor("#666666"))

        story.append(
            Paragraph(
                f"<b>Dataset:</b> {dataset_name}",
                self.body_style,
            )
        )
        story.append(
            Paragraph(
                f"<b>Risk Evaluation:</b> "
                f"<font color='{risk_color.hexval()}'><b>{risk_level}</b></font>"
                f" — {risk_label}",
                self.body_style,
            )
        )
        story.append(Spacer(1, 8))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.8,
                color=colors.HexColor("#dddddd"),
                spaceBefore=2,
                spaceAfter=8,
            )
        )

        # --------------------------------------------------------------
        # 2. FULL PROVENANCE MATRIX
        # --------------------------------------------------------------
        story.append(Paragraph("Provenance Matrix", self.section_style))

        provenance = audit_result.get("provenance") or {}
        metrics = audit_result.get("metrics") or {}

        source_link = (
            provenance.get("source_link")
            or audit_result.get("source_link")
            or "—"
        )
        municipality = (
            provenance.get("municipality")
            or audit_result.get("municipality")
            or "—"
        )
        country = provenance.get("country") or audit_result.get("country") or "—"
        year = provenance.get("year") or audit_result.get("year") or "—"
        uploaded_by = (
            provenance.get("uploaded_by")
            or audit_result.get("uploaded_by")
            or "—"
        )
        observation_count = metrics.get("observation_count", "—")

        # Truncate very long URLs for display
        display_source = source_link
        if len(display_source) > 78:
            display_source = display_source[:75] + "…"

        prov_data = [
            ["Field", "Value"],
            ["Municipality / Institution", str(municipality)],
            ["Country / Jurisdiction", str(country)],
            ["Fiscal Period", str(year)],
            ["Observation Count", str(observation_count)],
            ["Uploaded By", str(uploaded_by)],
            ["Source Link", display_source],
        ]

        prov_table = Table(prov_data, colWidths=[160, 380])
        prov_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#222222")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f5f5f5")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(prov_table)

        # --------------------------------------------------------------
        # 3. MATHEMATICAL MATRIX SUMMARY
        # --------------------------------------------------------------
        story.append(Paragraph("Mathematical Matrix Summary", self.section_style))

        tests = audit_result.get("tests") or {}
        b_test = tests.get("benford") or {
            "score": metrics.get("chi_square", 0.0),
            "critical_value": 10.0,
            "passed": False,
        }
        s_test = tests.get("shannon") or {
            "score": metrics.get("shannon_entropy", 0.0),
            "natural_minimum": 2.7,
            "passed": False,
        }

        math_data = [
            ["Diagnostic Layer", "Calculated Result", "Reference Rule", "Verdict"],
            [
                "Benford / Digit Distribution",
                f"{b_test.get('score', 0):.4f}",
                str(b_test.get("critical_value", 10.0)),
                "PASSED ✓" if b_test.get("passed") else "FAILED ✗",
            ],
            [
                "Shannon Entropy",
                f"{s_test.get('score', 0):.4f} bits",
                f">= {s_test.get('natural_minimum', 2.7)} bits",
                "PASSED ✓" if s_test.get("passed") else "FAILED ✗",
            ],
        ]

        math_table = Table(math_data, colWidths=[170, 120, 120, 130])
        math_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    (
                        "TEXTCOLOR",
                        (3, 1),
                        (3, 1),
                        colors.HexColor("#00aa44")
                        if b_test.get("passed")
                        else colors.HexColor("#ff0055"),
                    ),
                    (
                        "TEXTCOLOR",
                        (3, 2),
                        (3, 2),
                        colors.HexColor("#00aa44")
                        if s_test.get("passed")
                        else colors.HexColor("#ff0055"),
                    ),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(math_table)

        # --------------------------------------------------------------
        # 4. VISUAL EVIDENCE
        # --------------------------------------------------------------
        story.append(Paragraph("Visual Evidence", self.section_style))

        if chart_path and os.path.exists(chart_path):
            story.append(Image(chart_path, width=480, height=270))
        else:
            story.append(
                Paragraph(
                    "<i>Visual anomaly chart not available for this run.</i>",
                    self.body_style,
                )
            )

        # --------------------------------------------------------------
        # 5. CRYPTOGRAPHIC INTEGRITY LINE + QR PLACEHOLDER
        # --------------------------------------------------------------
        story.append(Paragraph("Cryptographic Integrity", self.section_style))

        file_hash = (
            audit_result.get("file_hash")
            or (audit_result.get("provenance") or {}).get("file_hash")
            or "—"
        )

        # Full un-truncated SHA-256
        story.append(
            Paragraph(
                f"<b>Dataset SHA-256</b>",
                self.body_style,
            )
        )
        story.append(Paragraph(str(file_hash), self.mono_style))
        story.append(Spacer(1, 8))

        # Placeholder box for future QR-code verification token
        qr_placeholder = Table(
            [
                [
                    Paragraph(
                        "<font size='8' color='#666666'>"
                        "QR VERIFICATION TOKEN<br/>"
                        "(reserved for future mesh attestation / IPFS CID binding)"
                        "</font>",
                        self.body_style,
                    )
                ]
            ],
            colWidths=[540],
            rowHeights=[48],
        )
        qr_placeholder.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#cccccc")),
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fafafa")),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        story.append(qr_placeholder)

        # --------------------------------------------------------------
        # 6. INTEGRITY STATEMENT / FOOTER
        # --------------------------------------------------------------
        story.append(Spacer(1, 16))
        story.append(
            HRFlowable(
                width="100%",
                thickness=0.6,
                color=colors.HexColor("#dddddd"),
                spaceBefore=4,
                spaceAfter=8,
            )
        )
        story.append(
            Paragraph(
                "<b>Integrity Statement:</b> This document was generated automatically "
                "from a forensic diagnostic pipeline. The statistical checks remain "
                "objective, reproducible, and independent from narrative framing.",
                self.footer_style,
            )
        )
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                "Prepared for media review, public release, and independent verification. "
                "#BajteBrothers · Open Fiscal Forensics Framework",
                self.footer_style,
            )
        )

        # Build PDF
        doc.build(story)
        print(f"✅ PDF certificate successfully written → {output_pdf}")
        return os.path.abspath(output_pdf)


# ----------------------------------------------------------------------
# Stand-alone smoke test
# ----------------------------------------------------------------------
if __name__ == "__main__":
    dummy_result = {
        "dataset_name": "isplate.csv",
        "label": "Budget Integrity Review",
        "risk_level": "HIGH",
        "risk_label": "Significant anomaly pattern detected",
        "file_hash": "d2ccb53cb1cd6a6d068895b3c7a274d48b6aef041b384a14dae73635717c2c35",
        "provenance": {
            "source_link": "https://transparentnost.zagreb.hr/hr/isplate/...",
            "country": "Croatia",
            "municipality": "Grad Zagreb",
            "year": "01.01.2025. - 31.12.2025.",
            "uploaded_by": "zeljko",
            "file_hash": "d2ccb53cb1cd6a6d068895b3c7a274d48b6aef041b384a14dae73635717c2c35",
        },
        "metrics": {
            "chi_square": 24.6958,
            "shannon_entropy": 2.7492,
            "observation_count": 1055,
        },
        "tests": {
            "benford": {
                "score": 24.6958,
                "critical_value": 10.0,
                "passed": False,
            },
            "shannon": {
                "score": 2.7492,
                "natural_minimum": 2.7,
                "passed": True,
            },
        },
    }

    gen = ForensicPDFGenerator()
    # Chart path can be empty for the smoke test
    gen.generate_report(dummy_result, chart_path="", output_pdf="test_forensic_certificate.pdf")
    print("Smoke test completed.")
