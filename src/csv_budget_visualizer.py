import csv
import os
from pathlib import Path
import matplotlib.pyplot as plt
from forensic_core import ForensicCore
from auto_adapter import detect_amount_column_from_csv, _read_csv_rows


class BudgetVisualizer:
    def __init__(self):
        self.core = ForensicCore()

    def run_csv_audit_and_plot(self, csv_filename, column_index=None):
        """column_index=None -> AutoAdapter odabire stupac iznosa (npr. 'Iznos na poziciji')."""
        if not os.path.exists(csv_filename):
            raise FileNotFoundError(csv_filename)
        if column_index is None:
            column_index = detect_amount_column_from_csv(csv_filename)
        rows = _read_csv_rows(csv_filename)          # sniffa ';' i BOM
        raw_data = [r[column_index] for r in rows[1:] if len(r) > column_index]
        print(f"Učitano {len(raw_data)} redova iz kolone {column_index}.")

        result = self.core.analyze(raw_data, label=f"Audit: {Path(csv_filename).name}")
        self.core.print_report(result)
        if result["status"] == "SUCCESS":
            self._generate_chart(result, csv_filename)
        return result

    def _generate_chart(self, result, filename):
        dist = result["tests"]["benford"]["distribution"]
        digits = [str(i) for i in range(1, 10)]
        observed = [dist[d]["observed_pct"] for d in digits]
        expected = [dist[d]["expected_pct"] for d in digits]
        plt.figure(figsize=(10, 6))
        plt.bar(digits, observed, alpha=0.6, color="#ff0055", label="Opaženo")
        plt.plot(digits, expected, color="#00aa44", marker="o", linewidth=2, label="Benford (očekivano)")
        plt.title(f"Distribucija prve znamenke - {Path(filename).name}")
        plt.xlabel("Prva značajna znamenka"); plt.ylabel("Udio (%)")
        plt.legend(); plt.grid(axis="y", linestyle="--", alpha=0.5)
        plt.savefig("budget_audit_result.png"); plt.close()


if __name__ == "__main__":
    BudgetVisualizer().run_csv_audit_and_plot("pravi_budzet.csv")
