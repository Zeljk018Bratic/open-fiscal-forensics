import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ForensicPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        # Custom-Styles für ein sauberes, steriles OSINT-Design
        self.title_style = ParagraphStyle(
            'DocTitle',
            parent=self.styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#111111'),
            spaceAfter=15
        )
        self.section_style = ParagraphStyle(
            'SectionTitle',
            parent=self.styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#ff0055'),
            spaceBefore=12,
            spaceAfter=8
        )
        self.body_style = ParagraphStyle(
            'DocBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=14,
            textColor=colors.HexColor('#333333')
        )

    def generate_report(self, audit_result: dict, chart_path: str, output_pdf: str = "forensic_audit_report.pdf"):
        """Generiert ein professionelles PDF-Zertifikat der Datenintegrität."""
        print(f"📄 [PDF-Generator] Erzeuge forensischen Bericht: {output_pdf}...")
        
        doc = SimpleDocTemplate(
            output_pdf,
            pagesize=letter,
            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
        )
        
        story = []
        
        # 1. Dokumenten-Header
        story.append(Paragraph(f"Forensic Audit Certificate", self.title_style))
        story.append(Paragraph(f"<b>Target Dataset:</b> {audit_result.get('label', 'Sovereign Budget Ledger')}", self.body_style))
        story.append(Paragraph(f"<b>Risk Evaluation:</b> {audit_result.get('risk_level', 'UNKNOWN')} — {audit_result.get('risk_label', '')}", self.body_style))
        story.append(Spacer(1, 15))
        
        # 2. Statistische Kennzahlen (Tabelle)
        story.append(Paragraph("Mathematical Matrix Summary", self.section_style))
        
        b_test = audit_result["tests"]["benford"]
        s_test = audit_result["tests"]["shannon"]
        
        data = [
            ["Metric Analysis Layer", "Calculated Score", "Threshold Metric", "Status Verdict"],
            ["Benford's Law (Chi²)", str(b_test["score"]), str(b_test["critical_value"]), "PASSED ✓" if b_test["passed"] else "FAILED ✗"],
            ["Shannon Entropy", f"{s_test['score']} bits", f">= {s_test['natural_minimum']} bits", "PASSED ✓" if s_test["passed"] else "FAILED ✗"]
        ]
        
        # Širine kolona su sada fiksirane (ukupno 530 tačaka, što savršeno staje na Letter format)
        table = Table(data, colWidths=[180, 110, 120, 120])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#111111')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,0), 10),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,1), (-1,-1), 9),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dddddd')),
            ('TEXTCOLOR', (3,1), (3,1), colors.HexColor('#00aa44') if b_test["passed"] else colors.HexColor('#ff0055')),
            ('TEXTCOLOR', (3,2), (3,2), colors.HexColor('#00aa44') if s_test["passed"] else colors.HexColor('#ff0055')),
        ]))
        
        story.append(table)
        story.append(Spacer(1, 20))
        
        # 3. Visuelles Diagramm einbinden
        story.append(Paragraph("Digit Frequency Deviation Chart", self.section_style))
        if os.path.exists(chart_path):
            story.append(Image(chart_path, width=480, height=288))
        else:
            story.append(Paragraph("<i>Visual anomaly chart not found. Pipeline skip.</i>", self.body_style))
            
        story.append(Spacer(1, 15))
        
        # 4. Footer & Legal Disclaimer
        story.append(Paragraph("<b>Audit Integrity Verification:</b> This document was generated automatically by an independent, open-source multi-agent diagnostic core. Statistical validation is permanent and un-biased.", self.body_style))
        
        # Dokument schreiben
        doc.build(story)
        print(f"✅ PDF-Zertifikat erfolgreich exportiert: {output_pdf}")

if __name__ == "__main__":
    # Test-Harness direkt im File integriert
    from forensic_core import ForensicCore
    core = ForensicCore()
    dummy_data = ["123", "456", "789", "111", "222"] * 15
    res = core.analyze(dummy_data, label="Standard Integration Test")
    
    gen = ForensicPDFGenerator()
    # Osiguravamo da povlači sliku koju smo već napravili u prethodnom koraku
    gen.generate_report(res, "budget_audit_result.png")
