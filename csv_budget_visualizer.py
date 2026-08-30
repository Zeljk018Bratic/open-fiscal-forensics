import csv
import os
import matplotlib.pyplot as plt
from forensic_core import ForensicCore, DataNormalizer, BenfordTest

class BudgetVisualizer:
    def __init__(self):
        self.core = ForensicCore()

    def run_csv_audit_and_plot(self, csv_filename, column_index=0):
        print(f"📊 [System] Otvaram CSV datoteku: {csv_filename}...")
        
        if not os.path.exists(csv_filename):
            print(f"⚠️ Datoteka {csv_filename} ne postoji! Kreiram testni primer za proveru...")
            self._create_dummy_csv(csv_filename)

        raw_data = []
        with open(csv_filename, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Preskačemo zaglavlje (header) ako postoji
            next(reader, None) 
            for row in reader:
                if row and len(row) > column_index:
                    raw_data.append(row[column_index])

        print(f"📥 Učitano {len(raw_data)} redova iz kolone {column_index}.")
        
        # 1. Pokretanje forenzičke analize
        result = self.core.analyze(raw_data, label=f"Audit: {csv_filename}")
        self.core.print_report(result)

        # 2. Vizuelizacija i crtanje grafikona
        if result["status"] == "SUCCESS":
            self._generate_chart(result, csv_filename)

    def _generate_chart(self, result, filename):
        benford_data = result["tests"]["benford"]["distribution"]
        
        digits = [str(i) for i in range(1, 10)]
        observed = [benford_data[d]["observed_pct"] for d in digits]
        expected = [benford_data[d]["expected_pct"] for d in digits]

        plt.figure(figsize=(10, 6))
        
        # Crtanje stubića za stvarne podatke
        plt.bar(digits, observed, alpha=0.6, color='#ff0055', label='Tvoji podaci (Obserivirano)')
        # Crtanje linije za Benfordov zakon
        plt.plot(digits, expected, color='#00ff66', marker='o', linewidth=2, label='Benfordov Zakon (Očekivano)')

        plt.title(f"Forenzička analiza distribucije cifara - {filename}", fontsize=12, fontweight='bold')
        plt.xlabel("Prva značajna cifra", fontsize=10)
        plt.ylabel("Procenat zastupljenosti (%)", fontsize=10)
        plt.legend()
        plt.grid(axis='y', linestyle='--', alpha=0.5)

        # Čuvanje grafikona kao slike
        output_image = "budget_audit_result.png"
        plt.savefig(output_image)
        plt.close()
        print(f"🎨 [Grafikon] Vizuelni izveštaj uspešno sačuvan kao slika: {output_image}")

    def _create_dummy_csv(self, filename):
        # Automatski pravi testni CSV ako korisnik nema spreman fajl
        with open(filename, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["Iznos", "Opis"]) # Zaglavlje
            # Simulacija realističnog budžeta (Log-Normalna raspodela)
            import random
            random.seed(42)
            for i in range(150):
                val = round(random.lognormvariate(8, 1.5), 2)
                writer.writerow([f"€{val}", f"Transakcija_{i}"])

if __name__ == "__main__":
    visualizer = BudgetVisualizer()
    # Pokrećemo skriptu nad fajlom "pravi_budzet.csv", gledajući prvu kolonu (indeks 0)
    visualizer.run_csv_audit_and_plot("pravi_budzet.csv", column_index=0)
