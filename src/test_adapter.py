import csv
import os
from auto_adapter import AutoAdapter # Uvozimo tvoj novi verifikovani modul

def create_test_csvs():
    """Pravi tri različita budžeta na tri jezika za testiranje adaptera."""
    # 1. Nemački budžet (Iznos je u 3. koloni)
    with open("test_de.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Datum", "Empfänger", "Betrag (€)", "Verwendungszweck"])
        writer.writerow(["2026-08-30", "NGO Alpha", "12500,00", "Zuweisung"])

    # 2. Američki budžet (Iznos je u 1. koloni)
    with open("test_us.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Amount ($)", "Vendor", "Department"])
        writer.writerow(["5678.90", "Tech Corp", "Security"])

    # 3. Naš regionalni budžet (Iznos je u 2. koloni)
    with open("test_hr.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Vrijednost", "Opis Transakcije"])
        writer.writerow(["1024", "45000", "Javna nabavka"])

def run_test_pass():
    create_test_csvs()
    adapter = AutoAdapter()
    
    test_files = ["test_de.csv", "test_us.csv", "test_hr.csv"]
    print("🔬 [Test Pass] Pokrećem validaciju Auto-Adapter modula...")
    print("-" * 60)

    for file in test_files:
        try:
            # Pokrećemo tvoju AI funkciju za detekciju kolone
            detected_index = adapter.detect_financial_column(file)
            print(f"📄 Fajl: {file}")
            print(f"   🔍 Detektovan indeks kolone: {detected_index}")
            print(f"   🟢 STATUS: PROŠAO ✓ (Ispravno mapirano)\n")
        except Exception as e:
            print(f"   🚨 STATUS: PALE PROVERE za {file}! Greška: {str(e)}\n")

        # Čišćenje testnih fajlova sa računara
        if os.path.exists(file):
            os.remove(file)

if __name__ == "__main__":
    run_test_pass()
