import streamlit as st
import os
import hashlib
import csv
import matplotlib.pyplot as plt
# Importujemo tvoje bezbedne i proverene module sa GitHub-a
from forensic_core import ForensicCore, DataNormalizer, BenfordTest
from auto_adapter import AutoAdapter
from pdf_generator import ForensicPDFGenerator

class BajteBrothersSafeDashboard:
    def __init__(self):
        self.core = ForensicCore()
        self.adapter = AutoAdapter()
        self.pdf_gen = ForensicPDFGenerator()
        
        # Konfiguracija aplikacije u čistom stilu
        st.set_page_config(page_title="#BajteBrothers - Audit Dashboard", page_icon="🤖", layout="wide")

    def calculate_file_hash(self, uploaded_file):
        """Računa stabilan SHA-256 hash direktno iz memorije."""
        sha256_hash = hashlib.sha256()
        bytes_data = uploaded_file.getvalue()
        sha256_hash.update(bytes_data)
        return sha256_hash.hexdigest()

    def run(self):
        st.title("🌍 #BajteBrothers - Citizen Budget Intelligence Platform")
        st.markdown("### Dezentrale Validierungs- & Forensik-Zentrale v1.0.0-MVP (Safe Mode)")
        st.write("---")

        # Bočna traka za unos porekla podataka (Provenance Tracking)
        st.sidebar.header("🛡️ Data Import & Provenance Tracking")
        uploaded_file = st.sidebar.file_uploader("Haushalts- oder NGO-Ausgaben (CSV)", type=["csv"])
        
        source_link = st.sidebar.text_input("Zugehörige Quelle / Link", placeholder="https://transparentno.labin...")
        region = st.sidebar.text_input("Land / Gemeinde", placeholder="Grad Labin")
        year = st.sidebar.text_input("Haushaltsjahr", placeholder="2025")
        uploaded_by = st.sidebar.text_input("Verifiziert von (User-Knoten)", placeholder="Node_42")

        if uploaded_file is not None:
            file_hash = self.calculate_file_hash(uploaded_file)
            st.sidebar.success("🔒 Datei-Hash verifiziert!")
            st.sidebar.code(f"SHA-256:\n{file_hash[:32]}...")

            # Privremeno čuvanje fajla za analitičku obradu
            temp_path = "temp_uploaded_budget.csv"
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            st.info("⚡ Starte automatische Pipeline... Durchleuchte Spaltenstrukturen...")
            try:
                # 1. Automatsko pronalaženje finansijske kolone preko tvog auto_adapter modula
                detected_column_index = self.adapter.detect_financial_column(temp_path)
                
                # 2. Reisto Python CSV čitanje (Sve je ugrađeno, Windows ne može da blokira)
                raw_values = []
                with open(temp_path, mode='r', encoding='utf-8-sig') as f:
                    sample = f.read(2048)
                    f.seek(0)
                    delimiter = ';' if ';' in sample else ','
                    
                    reader = csv.reader(f, delimiter=delimiter)
                    next(reader, None) # Preskačemo zaglavlje tabele
                    
                    for row in reader:
                        if row and len(row) > detected_column_index:
                            val = row[detected_column_index].strip()
                            if val:
                                raw_values.append(val)
                
                st.success(f"🎯 Automatische Erkennung erfolgreich: Finanzdaten in Spalten-Index {detected_column_index} isoliert.")
                st.write(f"Anzahl verarbeiteter Datensätze: **{len(raw_values)}**")
                
                # 3. Pokretanje matematičke analize u tvom ForensicCore jezgru
                audit_label = f"Audit: {region} ({year})" if region and year else f"Audit: {uploaded_file.name}"
                result = self.core.analyze(raw_values, label=audit_label)
                
                if result["status"] == "SUCCESS":
                    # Prikazivanje grafika i rezultata na ekranu
                    self.display_metrics_and_results(result)
                    
                    # 4. Automatsko štampanje PDF sertifikata u pozadini
                    chart_img_path = "temp_dashboard_chart.png"
                    pdf_output_path = "forensic_audit_report.pdf"
                    
                    self.pdf_gen.generate_report(result, chart_img_path, output_pdf=pdf_output_path)
                    
                    # Dugme za preuzimanje izveštaja
                    if os.path.exists(pdf_output_path):
                        with open(pdf_output_path, "rb") as pdf_file:
                            st.download_button(
                                label="📥 ZERTIFIZIERTES FORENSIK-PDF HERUNTERLADEN",
                                data=pdf_file,
                                file_name=f"BajteBrothers_Audit_{region or 'Report'}_{year or '2026'}.pdf",
                                mime="application/pdf"
                            )
                else:
                    st.error(f"❌ Fehler im Forensik-Kern: {result.get('status')}. Zu wenige valide Datenpunkte.")

            except Exception as e:
                st.error(f"🚨 Pipeline-Abbruch durch Sicherheits- oder Verarbeitungsfehler: {str(e)}")
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        else:
            st.warning("📡 Warte auf Daten-Upload in der linken Spalte, um das Sumpf-Radar zu aktivieren...")

    def display_metrics_and_results(self, result):
        b_test = result["tests"]["benford"]
        s_test = result["tests"]["shannon"]
        
        risk_colors = {"LOW": "green", "MEDIUM": "orange", "HIGH": "red"}
        color = risk_colors.get(result["risk_level"], "white")
        
        st.markdown(f"## Risikostufe: :{color}[{result['risk_level']}] — {result['risk_label']}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="Benford's Law Chi²-Score", value=f"{b_test['score']}", delta=f"Schwelle: {b_test['critical_value']}", delta_color="inverse")
            st.write("Ergebnis:", "✅ BESTANDEN" if b_test["passed"] else "❌ ANOMALIE FLAGGED ⚠️")
            
        with col2:
            st.metric(label="Shannon-Entropie", value=f"{s_test['score']} bits", delta=f"Min. Erwartet: {s_test['natural_minimum']} bits")
            st.write("Ergebnis:", "✅ BESTANDEN" if s_test["passed"] else "❌ ANOMALIE FLAGGED ⚠️")

        st.markdown("### 📊 Verteilungs-Abgleich auf Pixelebene")
        
        digits = [str(i) for i in range(1, 10)]
        observed = [b_test["distribution"][d]["observed_pct"] for d in digits]
        expected = [b_test["distribution"][d]["expected_pct"] for d in digits]

        fig, ax = plt.subplots(figsize=(10, 4))
        ax.bar(digits, observed, alpha=0.6, color='#ff0055', label='Gemessene Struktur (Eingabe)')
        ax.plot(digits, expected, color='#00ff66', marker='o', linewidth=2, label='Benford-Gesetz (Natur-Soll)')
        ax.set_ylabel("Prozent (%)")
        ax.set_xlabel("Erste Ziffer")
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.3)
        
        fig.savefig("temp_dashboard_chart.png", dpi=100, bbox_inches='tight')
        st.pyplot(fig)

if __name__ == "__main__":
    dashboard = BajteBrothersSafeDashboard()
    dashboard.run()
