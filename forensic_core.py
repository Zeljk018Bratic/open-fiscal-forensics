"""
forensic_core.py
================
Open-Source Forensic Data Integrity Analyzer
Kombiniert: Datennormalisierung + Benford's Law + Shannon-Entropie

Verwendung:
    from forensic_core import ForensicCore
    result = ForensicCore().analyze(data, label="Haushaltsdaten 2024")
"""

import math
import re
from collections import Counter
from typing import Union


# ─── Schicht 1: Datennormalisierung ──────────────────────────────────────────

class DataNormalizer:
    """
    Bereinigt Rohdaten aus heterogenen Quellen (CSV, API, HTML-Scraping).
    Verarbeitet Währungssymbole, europäische/angloamerikanische Formate.
    """

    @staticmethod
    def parse_value(raw) -> Union[float, None]:
        if isinstance(raw, (int, float)):
            return float(raw) if raw > 0 else None

        s = re.sub(r'[€$£¥\s%]', '', str(raw).strip())

        # Format-Erkennung
        if ',' in s and '.' in s:
            if s.index(',') < s.index('.'):
                s = s.replace(',', '')           # 1,234.56 → 1234.56
            else:
                s = s.replace('.', '').replace(',', '.')  # 1.234,56 → 1234.56
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(',', '.')           # 3,14 → 3.14
            else:
                s = s.replace(',', '')            # 1,000 → 1000

        try:
            val = float(s)
            return val if val > 0 else None
        except ValueError:
            return None

    @classmethod
    def normalize(cls, raw_data: list) -> tuple:
        """
        Returns: (clean_values: list[float], rejected_count: int)
        """
        clean, rejected = [], 0
        for item in raw_data:
            val = cls.parse_value(item)
            if val is not None:
                clean.append(val)
            else:
                rejected += 1
        return clean, rejected


# ─── Schicht 2: Statistische Tests ───────────────────────────────────────────

class BenfordTest:
    """Prüft die Verteilung der ersten Ziffer gegen das Benfordsche Gesetz."""

    EXPECTED = [0, 0.301, 0.176, 0.125, 0.097, 0.079, 0.067, 0.058, 0.051, 0.046]
    CRITICAL_VALUE = 15.507  # df=8, p=0.05

    @classmethod
    def run(cls, values: list[float]) -> dict:
        counts = [0] * 10
        for v in values:
            d = cls._first_digit(v)
            if d:
                counts[d] += 1

        total = sum(counts[1:])
        if total == 0:
            return {"score": 0, "passed": True, "distribution": {}}

        chi2 = sum(
            ((counts[i] / total - cls.EXPECTED[i]) ** 2) / cls.EXPECTED[i]
            for i in range(1, 10)
        )

        distribution = {
            str(i): {
                "observed_pct": round(counts[i] / total * 100, 2),
                "expected_pct": round(cls.EXPECTED[i] * 100, 2),
                "delta_pct": round((counts[i] / total - cls.EXPECTED[i]) * 100, 2)
            }
            for i in range(1, 10)
        }

        return {
            "score": round(chi2, 4),
            "critical_value": cls.CRITICAL_VALUE,
            "passed": chi2 <= cls.CRITICAL_VALUE,
            "distribution": distribution
        }

    @staticmethod
    def _first_digit(v: float) -> Union[int, None]:
        try:
            s = f"{abs(v):.10f}".replace('.', '').lstrip('0')
            return int(s[0]) if s else None
        except (ValueError, IndexError):
            return None


class ShannonEntropyTest:
    """
    Misst die Informationsdichte aller Ziffern im Datensatz.
    Natürliche Daten: Entropie ~3.0–3.32
    Manipulierte/runde Zahlen: Entropie deutlich niedriger
    """

    NATURAL_MIN = 3.0   # Untere Grenze für natürliche Daten
    MAX_POSSIBLE = math.log2(10)  # 3.3219 — theoretisches Maximum

    @classmethod
    def run(cls, values: list[float]) -> dict:
        all_digits = []
        for v in values:
            all_digits.extend(d for d in str(v) if d.isdigit())

        if not all_digits:
            return {"score": 0.0, "passed": False}

        total = len(all_digits)
        counts = Counter(all_digits)
        entropy = -sum(
            (c / total) * math.log2(c / total)
            for c in counts.values()
        )
        entropy = round(entropy, 4)

        return {
            "score": entropy,
            "max_possible": round(cls.MAX_POSSIBLE, 4),
            "natural_minimum": cls.NATURAL_MIN,
            "passed": entropy >= cls.NATURAL_MIN,
            "uniformity_pct": round(entropy / cls.MAX_POSSIBLE * 100, 1)
        }


# ─── Schicht 3: Hauptanalysator ──────────────────────────────────────────────

class ForensicCore:
    """
    Zentraler Einstiegspunkt für forensische Datenintegritätsprüfung.
    Kombiniert Normalisierung, Benford-Test und Shannon-Entropie.
    """

    MIN_SAMPLE = 50

    def analyze(self, raw_data: list, label: str = "Datensatz") -> dict:
        """
        Vollständige forensische Analyse eines Rohdatensatzes.

        Args:
            raw_data: Liste von Zahlen oder Strings (Beträge, Budgetposten)
            label:    Bezeichnung für den Bericht

        Returns:
            Strukturiertes Analyse-Dict mit Einzeltests und Gesamturteil
        """
        # Schicht 1: Normalisierung
        clean, rejected = DataNormalizer.normalize(raw_data)
        n = len(clean)

        if n < self.MIN_SAMPLE:
            return {
                "label": label,
                "status": "INSUFFICIENT_DATA",
                "valid_count": n,
                "rejected_count": rejected,
                "minimum_required": self.MIN_SAMPLE,
                "anomaly_detected": None
            }

        # Schicht 2: Tests
        benford = BenfordTest.run(clean)
        shannon = ShannonEntropyTest.run(clean)

        # Gesamturteil: Anomalie wenn EINER der Tests fehlschlägt
        anomaly = (not benford["passed"]) or (not shannon["passed"])

        # Risikostufe
        failed = sum([not benford["passed"], not shannon["passed"]])
        if failed == 0:
            risk = "LOW"
            risk_label = "Keine Anomalie erkannt — Daten erscheinen integer"
        elif failed == 1:
            risk = "MEDIUM"
            risk_label = "Ein Test auffällig — manuelle Prüfung empfohlen"
        else:
            risk = "HIGH"
            risk_label = "Beide Tests auffällig — starker Manipulationsverdacht"

        return {
            "label": label,
            "status": "SUCCESS",
            "valid_count": n,
            "rejected_count": rejected,
            "anomaly_detected": anomaly,
            "risk_level": risk,
            "risk_label": risk_label,
            "tests": {
                "benford": benford,
                "shannon": shannon
            }
        }

    def print_report(self, result: dict):
        """Gibt einen lesbaren Konsolenbericht aus."""
        if result["status"] != "SUCCESS":
            print(f"[{result['label']}] Status: {result['status']} "
                  f"(n={result.get('valid_count', 0)}, "
                  f"benötigt: {result.get('minimum_required', self.MIN_SAMPLE)})")
            return

        b = result["tests"]["benford"]
        s = result["tests"]["shannon"]

        print(f"\n{'═'*56}")
        print(f"  FORENSIC REPORT: {result['label']}")
        print(f"{'═'*56}")
        print(f"  Datensätze analysiert : {result['valid_count']} "
              f"({result['rejected_count']} abgelehnt)")
        print(f"  Risikostufe           : {result['risk_level']} — {result['risk_label']}")
        print(f"  Anomalie erkannt      : {'JA ⚠️' if result['anomaly_detected'] else 'NEIN ✓'}")
        print(f"\n  ┌─ Benford's Law ──────────────────────────────┐")
        print(f"  │  Chi²-Score    : {b['score']} "
              f"(Schwelle: {b['critical_value']})")
        print(f"  │  Ergebnis      : {'✓ BESTANDEN' if b['passed'] else '✗ FEHLGESCHLAGEN'}")
        print(f"  └──────────────────────────────────────────────┘")
        print(f"\n  ┌─ Shannon-Entropie ────────────────────────────┐")
        print(f"  │  Score         : {s['score']} / {s['max_possible']} "
              f"({s['uniformity_pct']}% Gleichverteilung)")
        print(f"  │  Mindest-Score : {s['natural_minimum']}")
        print(f"  │  Ergebnis      : {'✓ BESTANDEN' if s['passed'] else '✗ FEHLGESCHLAGEN'}")
        print(f"  └──────────────────────────────────────────────┘")

        if not b["passed"] and "distribution" in b:
            print(f"\n  Benford-Abweichungen (|Δ| > 4%):")
            for d, v in b["distribution"].items():
                if abs(v["delta_pct"]) > 4:
                    print(f"    Ziffer {d}: {v['observed_pct']}% "
                          f"(erwartet {v['expected_pct']}%, Δ={v['delta_pct']:+.1f}%)")


# ─── Tests ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import random
    random.seed(42)

    core = ForensicCore()

    datasets = [
        ("Linearer manipulierter Datensatz",
         [f"{i * 10}.00" for i in range(1, 120)]),

        ("Runde Zahlen (typische NGO-Fälschung)",
         [f"{i}000.00" for i in range(1, 120)]),

        ("Fibonacci — natürlich, Benford-konform",
         [str(__import__('functools').reduce(
             lambda acc, _: acc + [acc[-1] + acc[-2]], range(200), [1, 1]
         )[i]) for i in range(200)]),

        ("Log-Normal — realistisches Budget",
         [round(random.lognormvariate(8, 2), 2) for _ in range(200)]),

        ("Gemischte Rohdaten mit Formatfehlern",
         ["€1.234,56", "$5,678.90", "23.400", "1,100", "450,00",
          "€89.000", "12.500,00", "$3,200", "7.800", "€15.000"] * 8),
    ]

    for label, data in datasets:
        result = core.analyze(data, label=label)
        core.print_report(result)
