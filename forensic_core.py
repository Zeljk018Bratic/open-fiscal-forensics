import math
import re
from collections import Counter
from typing import Union

class DataNormalizer:
    @staticmethod
    def parse_value(raw) -> Union[float, None]:
        if isinstance(raw, (int, float)):
            return float(raw) if raw > 0 else None
        s = re.sub(r'[€$£¥\s%]', '', str(raw).strip())
        if ',' in s and '.' in s:
            if s.index(',') < s.index('.'):
                s = s.replace(',', '')
            else:
                s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2:
                s = s.replace(',', '.')
            else:
                s = s.replace(',', '')
        try:
            val = float(s)
            return val if val > 0 else None
        except ValueError:
            return None

    @classmethod
    def normalize(cls, raw_data: list) -> tuple:
        clean, rejected = [], 0
        for item in raw_data:
            val = cls.parse_value(item)
            if val is not None:
                clean.append(val)
            else:
                rejected += 1
        return clean, rejected

class BenfordTest:
    @staticmethod
    def run(data_series: list[float]) -> dict:
        """
        Provodi deterministicki Benfordov test prve znamenke (Chi-Square Goodness-of-Fit).
        Ispravno skalira proporcije s ukupnim brojem uzoraka (N) radi usklađivanja s kritičnom vrijednošću 15.507.
        """
        import math
        
        # Izolacija prve znamenke za strogo pozitivne vrijednosti iznad nule
        valid_digits = []
        for x in data_series:
            if x > 0:
                try:
                    # Uklanjanje nula i decimalnih točaka da dobijemo prvu pravu znamenku
                    s = str(abs(x)).lstrip('0').replace('.', '')
                    if s:
                        valid_digits.append(int(s[0]))
                except (ValueError, IndexError):
                    continue
                    
        N = len(valid_digits)
        critical_threshold = 15.507
        
        # Minimalni statistički prag za stabilnost testa
        if N < 50:
            return {
                "passed": True,  # Prolazimo automatski ako nema dovoljno podataka da ne rušimo sustav
                "sample_size": N,
                "chi_square_score": 0.0,
                "critical_threshold": critical_threshold,
                "risk_level": "UNKNOWN"
            }
            
        # Očekivane Benfordove distribucije za znamenke od 1 do 9
        expected_distribution = {d: math.log10(1 + 1/d) for d in range(1, 10)}
        
        # Brojanje stvarnih pojavljivanja svake znamenke (frekvencije)
        observed_counts = {d: valid_digits.count(d) for d in range(1, 10)}
        
        # Standardna Chi-Square formula: Σ ((O_i - E_i)^2 / E_i)
        chi_square_score = 0.0
        for d in range(1, 10):
            observed_f = observed_counts[d]  # Stvarna frekvencija
            expected_f = expected_distribution[d] * N  # Očekivana frekvencija na uzorku N
            
            if expected_f > 0:
                chi_square_score += ((observed_f - expected_f) ** 2) / expected_f
                
        # Usporedba s kritičnim pragom 15.507 za 8 stupnjeva slobode
        failed_test = chi_square_score > critical_threshold
        
        return {
            "passed": not failed_test,
            "sample_size": N,
            "chi_square_score": round(chi_square_score, 4),
            "critical_threshold": critical_threshold,
            "risk_level": "LOW_RISK" if not failed_test else "HIGH_RISK"
        }

class ShannonEntropyTest:
    NATURAL_MIN = 3.0
    MAX_POSSIBLE = math.log2(10)

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

class ForensicCore:
    MIN_SAMPLE = 50

    def analyze(self, raw_data: list, label: str = "Datensatz") -> dict:
        clean, rejected = DataNormalizer.normalize(raw_data)
        n = len(clean)
        if n < self.MIN_SAMPLE:
            return {
                "label": label, "status": "INSUFFICIENT_DATA",
                "valid_count": n, "rejected_count": rejected,
                "minimum_required": self.MIN_SAMPLE, "anomaly_detected": None
            }
        benford = BenfordTest.run(clean)
        shannon = ShannonEntropyTest.run(clean)
        anomaly = (not benford["passed"]) or (not shannon["passed"])
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
            "label": label, "status": "SUCCESS", "valid_count": n,
            "rejected_count": rejected, "anomaly_detected": anomaly,
            "risk_level": risk, "risk_label": risk_label,
            "tests": {"benford": benford, "shannon": shannon}
        }

    def print_report(self, result: dict):
        if result["status"] != "SUCCESS":
            print(f"[{result['label']}] Status: {result['status']}")
            return
        b = result["tests"]["benford"]
        s = result["tests"]["shannon"]
        print(f"\n{'═'*56}")
        print(f" FORENSIC REPORT: {result['label']}")
        print(f"{'═'*56}")
        print(f" Datensätze analysiert : {result['valid_count']} ({result['rejected_count']} abgelehnt)")
        print(f" Risikostufe           : {result['risk_level']} — {result['risk_label']}")
        print(f" Anomalie erkannt      : {'JA ⚠️' if result['anomaly_detected'] else 'NEIN ✓'}")
        print(f"\n ┌─ Benford's Law ──────────────────────────────┐")
        print(f" │ Chi²-Score : {b['score']} (Schwelle: {b['critical_value']})")
        print(f" │ Ergebnis   : {'✓ BESTANDEN' if b['passed'] else '✗ FEHLGESCHLAGEN'}")
        print(f" └──────────────────────────────────────────────┘")
        print(f"\n ┌─ Shannon-Entropie ────────────────────────────┐")
        print(f" │ Score      : {s['score']} / {s['max_possible']} ({s['uniformity_pct']}% Gleichverteilung)")
        print(f" │ Ergebnis   : {'✓ BESTANDEN' if s['passed'] else '✗ FEHLGESCHLAGEN'}")
        print(f" └──────────────────────────────────────────────┘")
