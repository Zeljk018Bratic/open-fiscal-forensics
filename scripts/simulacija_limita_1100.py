import math
import random
import re
from collections import Counter
from typing import Union

# --- KOD IZ TVOG REPOZITORIJA (OFFF) ---

class DataNormalizer:
    @staticmethod
    def parse_value(raw) -> Union[float, None]:
        if isinstance(raw, (int, float)):
            return float(raw) if raw > 0 else None
        s = re.sub(r'[€$£¥\s%]', '', str(raw).strip())
        if ',' in s and '.' in s:
            if s.index(',') < s.index('.'): s = s.replace(',', '')
            else: s = s.replace('.', '').replace(',', '.')
        elif ',' in s:
            parts = s.split(',')
            if len(parts) == 2 and len(parts[1]) <= 2: s = s.replace(',', '.')
            else: s = s.replace(',', '')
        try:
            val = float(s)
            return val if val > 0 else None
        except ValueError:
            return None

class BenfordTest:
    @staticmethod
    def run(data_series: list[float]) -> dict:
        valid_digits = []
        for x in data_series:
            if x > 0:
                s = str(abs(x)).lstrip('0').replace('.', '')
                if s: valid_digits.append(int(s[0]))
        N = len(valid_digits)
        critical_threshold = 15.507
        if N < 50:
            return {"passed": True, "sample_size": N, "chi_square_score": 0.0, "critical_threshold": critical_threshold, "risk_level": "UNKNOWN"}
        
        expected_distribution = {d: math.log10(1 + 1/d) for d in range(1, 10)}
        observed_counts = {d: valid_digits.count(d) for d in range(1, 10)}
        
        chi_square_score = 0.0
        for d in range(1, 10):
            observed_f = observed_counts[d]
            expected_f = expected_distribution[d] * N
            if expected_f > 0:
                chi_square_score += ((observed_f - expected_f) ** 2) / expected_f
                
        failed_test = chi_square_score > critical_threshold
        return {
            "passed": not failed_test, "sample_size": N,
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
        for v in values: all_digits.extend(d for d in str(v) if d.isdigit())
        if not all_digits: return {"score": 0.0, "passed": False}
        total = len(all_digits)
        counts = Counter(all_digits)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts.values())
        entropy = round(entropy, 4)
        return {
            "score": entropy, "max_possible": round(cls.MAX_POSSIBLE, 4),
            "natural_minimum": cls.NATURAL_MIN, "passed": entropy >= cls.NATURAL_MIN,
            "uniformity_pct": round(entropy / cls.MAX_POSSIBLE * 100, 1)
        }

class ForensicCore:
    def analyze(self, raw_data: list, label: str = "Datensatz") -> dict:
        clean = [DataNormalizer.parse_value(x) for x in raw_data if DataNormalizer.parse_value(x) is not None]
        benford = BenfordTest.run(clean)
        shannon = ShannonEntropyTest.run(clean)
        anomaly = (not benford["passed"]) or (not shannon["passed"])
        
        failed = sum([not benford["passed"], not shannon["passed"]])
        risk = "LOW" if failed == 0 else "MEDIUM" if failed == 1 else "HIGH"
        
        return {
            "label": label, "valid_count": len(clean), "anomaly_detected": anomaly,
            "risk_level": risk, "tests": {"benford": benford, "shannon": shannon}
        }

# --- GENERIRANJE MOCK PODATAKA I SIMULACIJA LIMITA ---

def generate_mock_budget():
    """Generira 5000 transakcija kronološki (od 2020. do 2026.)."""
    random.seed(42) # Fiksno radi reproducibilnosti
    database = []
    
    # Razdoblje 2020 - 2024: Namjerno štelani ugovori tik ispod praga javne nabave
    # Ovdje dominiraju prve znamenke 2 (npr. 24.500€, 26.100€) i niska entropija (ponavljanje istih iznosa)
    for _ in range(3900):
        if random.random() < 0.4:
            # Sumnjive transakcije: štelanje ispod praga od 26.540 EUR
            val = random.choice([24500.00, 25800.00, 26100.00, 4900.00])
        else:
            # Organske transakcije
            val = round(random.uniform(10, 10000), 2)
        database.append(val)
        
    # Razdoblje 2025 - 2026 (Najnovijih 1100 redaka): Čisti podaci, bez očitih anomalija
    for _ in range(1100):
        val = round(random.uniform(50, 50000), 2) # Potpuno prirodna raspodjela brojeva
        database.append(val)
        
    return database

# Pokretanje simulacije i analize
if __name__ == "__main__":
    full_database = generate_mock_budget()
    
    # 1. Što vidi javnost zbog limita sustava (Zadnjih 1100 zapisa)
    visible_export = full_database[-1100:]
    
    # 2. Što je ostalo sakriveno u starijim razdobljima (Prvih 3900 zapisa)
    hidden_data = full_database[:3900]
    
    forensic = ForensicCore()
    
    report_visible = forensic.analyze(visible_export, "JAVNI IZVOZ (Limit 1100 redaka)")
    report_hidden = forensic.analyze(hidden_data, "SKRIVENI PODACI (2020-2024)")
    
    # Ispis rezultata za javni izvoz
    print(f"=== REZULTAT ZA: {report_visible['label']} ===")
    print(f"Analizirano redaka: {report_visible['valid_count']}")
    print(f"Razina rizika     : {report_visible['risk_level']}")
    print(f"Chi²-Score        : {report_visible['tests']['benford']['chi_square_score']} (Prag: 15.507)")
    print(f"Anomalija uočena  : {'DA ⚠️' if report_visible['anomaly_detected'] else 'NEIN ✓'}")
    
    # Ispis rezultata za skriveni dio proračuna
    print(f"\n=== REZULTAT ZA: {report_hidden['label']} ===")
    print(f"Analizirano redaka: {report_hidden['valid_count']}")
    print(f"Razina rizika     : {report_hidden['risk_level']} ⚠️⚠️⚠️")
    print(f"Chi²-Score        : {report_hidden['tests']['benford']['chi_square_score']} (Prag: 15.507)")
    print(f"Anomalija uočena  : {'DA ⚠️' if report_hidden['anomaly_detected'] else 'NEIN ✓'}")
