import json
import math
from forensic_core import ForensicCore

class LocalBudgetAudit:
    def __init__(self):
        self.core = ForensicCore()

    def run_local_audit(self):
        print("📊 [System] Starte integriertes Haushaltsdaten-Audit...")
        
        # Simulation realer, heterogener Budgetposten (gemischte Formate wie in echten Systemen)
        simulated_budget_data = [
            "€1.234,56", "$5,678.90", "23.400", "1,100", "450,00",
            "€89.000", "12.500,00", "$3,200", "7.800", "€15.000",
            "2.340", "890", "4.500,50", "$67,890", "€123.456"
        ] * 4  # Generiert 60 valide Einträge für eine ausreichende mathematische Stichprobe

        print(f"📥 {len(simulated_budget_data)} Finanzdatensätze erfolgreich geladen.")
        
        # Übergabe der Daten an den mathematischen Forensik-Kern
        try:
            audit_result = self.core.analyze(simulated_budget_data, label="Nationales Budget-Audit (Simuliert)")
            self.core.print_report(audit_result)
        except Exception as e:
            print(f"🚨 Fehler bei der mathematischen Auswertung: {str(e)}")

if __name__ == "__main__":
    auditor = LocalBudgetAudit()
    auditor.run_local_audit()
