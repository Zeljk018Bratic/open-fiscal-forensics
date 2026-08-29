# #BajteBrothers Transparency Framework: User & Deployment Guide

This document provides a comprehensive operational guide for data analysts, investigative journalists, and open-source intelligence (OSINT) developers utilizing the `#BajteBrothers` framework to audit public finance datasets and government procurement budgets.

---

## 🏛️ Framework Philosophy & Methodology

The core objective of this framework is to establish an un-biased, programmatically verifiable layer of truth for public asset management. By evaluating datasets against established natural mathematical constraints, the framework bypasses subjective narrative biasses and isolates statistical anomalies directly at the source.

The diagnostic pipeline consists of two distinct mathematical layers:
1. **Benford's Law Compliance:** Measures the distribution frequency of leading digits against the logarithmic scale (\(P(d) = \log_{10}(1 + 1/d)\)) via a Chi-Square goodness-of-fit test. This mechanism detects macro-level artificial modifications.
2. **Shannon Entropy Analysis:** Computes the information density and structural randomness of all numerical positions. It acts as an absolute counter-measure against linear numerical invention, arbitrary rounding schemas, and hidden internal patterns that can slip past classical leading-digit tests.

---

## 🛠️ Step-by-Step Guide to Auditing National Budgets

The framework is optimized to interface with native, open-source data portals (such as GovData, OpenSpending, or official national data.gov infrastructure) using standard structured file formats.

### Step 1: Procurement of Government Datasets
1. Navigate to your regional or national public open-data repository (e.g., `govdata.de`, `data.gov.hr`, or equivalent public treasury databases).
2. Query specific datasets associated with federal expenditures, municipal spending accounts, or public subsidy allocation logs.
3. Apply filters to restrict the payload format strictly to structured Comma-Separated Values (`.csv`).
4. Download the physical file to your workstation.

### Step 2: Environmental Configuration & Execution
1. Relocate the downloaded expenditure spreadsheet directly into your local project root directory.
2. Rename the specific file exactly to: `pravi_budzet.csv`
3. Execute the visualization script via your native terminal interface:
   ```powershell
   python csv_budget_visualizer.py
   ```

### Step 3: Column Mapping Adjustments
Depending on the internal structural variations of varying sovereign ledgers, financial figures may reside in different database tables. If the transaction values are located outside the default index (Column 1), open `csv_budget_visualizer.py` inside a standard text editor and calibrate the `column_index` perimeter located at the entry block:

```python
if __name__ == "__main__":
    visualizer = BudgetVisualizer()
    # Calibrate index: 0 = Column A, 1 = Column B, 2 = Column C, etc.
    visualizer.run_csv_audit_and_plot("pravi_budzet.csv", column_index=1)
```

---

## 📊 Deciphering Diagnostic Outputs

Upon completion, the diagnostic pipeline will produce two clean audit vectors:

1. **Console Report Summary:**
   * **LOW RISK:** The dataset tightly correlates with logarithmic decay constants and maintains healthy informational randomness.
   * **MEDIUM RISK:** Minor deviation detected in one testing category. A manual granular forensic exploration of individual line items is recommended.
   * **HIGH RISK:** Severe mathematical discrepancies flagged across both Benford and Shannon matrices. Indicates a high mathematical probability of data manipulation or structural formatting distortion.

2. **Kryptographic Graph Visualization (`budget_audit_result.png`):**
   * The solid **green locus** traces the immutable path of natural numbers.
   * The **pink bars** project the observable truth of your local input data. Distinct structural anomalies or unexplained deviations will instantly illuminate mathematical discrepancies directly on your monitor.

---

## 🤝 Community Peer-Review & Code Integrity

This framework operates completely under an open, decentralized architectural model. We strictly discourage the use of non-verified, volatile third-party infrastructure. Every core script is hosted publicly to support peer-reviews, modular extensions, and rigorous defensive benchmarking. We welcome global developers to fork the ecosystem, clean the interfaces, and expand the statistical tool-mesh.
