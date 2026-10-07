"""
Open Fiscal Forensics Framework (OFFF)
Glavna ulazna točka.

Pokreće:
  - simulaciju limita od 1.100 redaka
  - forenzičku analizu nad stvarnim CSV-om
"""

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from forensic_core import ForensicCore
    from auto_adapter import detect_amount_column_from_csv
except ImportError as e:
    print(f"[UPOZORENJE] Ne mogu uvesti core module: {e}", file=sys.stderr)
    ForensicCore = None
    detect_amount_column_from_csv = None


def pokreni_simulaciju_limita():
    skripta = ROOT / "scripts" / "simulacija_limita_1100.py"
    if not skripta.exists():
        print(f"[GREŠKA] Skripta nije pronađena: {skripta}", file=sys.stderr)
        return 1

    result = subprocess.run(
        [sys.executable, str(skripta)],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def analiziraj_csv(csv_path: str, label: str = "CSV"):
    if ForensicCore is None:
        print("[GREŠKA] ForensicCore nije dostupan.", file=sys.stderr)
        return 1

    putanja = Path(csv_path)
    if not putanja.exists():
        print(f"[GREŠKA] CSV nije pronađen: {putanja}", file=sys.stderr)
        return 1

    try:
        idx = detect_amount_column_from_csv(putanja)
        print(f"[INFO] Detektiran stupac s iznosima: indeks {idx}")
    except Exception as e:
        print(f"[GREŠKA] Ne mogu detektirati stupac s iznosima: {e}", file=sys.stderr)
        return 1

    vrijednosti = []
    with putanja.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        for row in reader:
            if idx < len(row):
                vrijednosti.append(row[idx])

    if not vrijednosti:
        print("[GREŠKA] Nema podataka u odabranom stupcu.", file=sys.stderr)
        return 1

    core = ForensicCore()
    report = core.analyze(vrijednosti, label=label)

    if report.get("status") != "SUCCESS":
        print(f"\n[{report['label']}] Status: {report['status']}")
        print(f" Valjanih zapisa   : {report.get('valid_count', 0)}")
        print(f" Odbijenih zapisa  : {report.get('rejected_count', 0)}")
        print(f" Minimum potreban  : {report.get('minimum_required', 50)}")
        return 1

    print(f"\n{'═' * 56}")
    print(f" FORENZIČKI IZVJEŠTAJ: {report['label']}")
    print(f"{'═' * 56}")
    print(f" Analizirano zapisa : {report['valid_count']} ({report['rejected_count']} odbijeno)")
    print(f" Razina rizika      : {report['risk_level']} — {report['risk_label']}")
    print(f" Anomalija          : {'DA ⚠️' if report['anomaly_detected'] else 'NE ✓'}")

    b = report["tests"]["benford"]
    s = report["tests"]["shannon"]

    print(f"\n ┌─ Benford ─────────────────────────────────────┐")
    print(f" │ Chi²        : {b['chi_square_score']} (prag: {b['critical_threshold']})")
    print(f" │ Uzorak      : {b['sample_size']}")
    print(f" │ Prošao      : {'DA ✓' if b['passed'] else 'NE ✗'}")
    print(f" └───────────────────────────────────────────────┘")

    print(f"\n ┌─ Shannon ─────────────────────────────────────┐")
    print(f" │ Entropija   : {s['score']} / {s['max_possible']}")
    print(f" │ Uniformnost : {s['uniformity_pct']}%")
    print(f" │ Prošao      : {'DA ✓' if s['passed'] else 'NE ✗'}")
    print(f" └───────────────────────────────────────────────┘")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="OFFF — Open Fiscal Forensics Framework"
    )
    parser.add_argument("--simulacija", action="store_true",
                        help="Pokreni simulaciju limita od 1.100 redaka")
    parser.add_argument("--csv", type=str,
                        help="Putanja do CSV datoteke za forenzičku analizu")
    parser.add_argument("--label", type=str, default="CSV analiza",
                        help="Oznaka izvještaja")

    args = parser.parse_args()

    if args.simulacija:
        return pokreni_simulaciju_limita()
    if args.csv:
        return analiziraj_csv(args.csv, label=args.label)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
