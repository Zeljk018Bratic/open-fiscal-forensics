# Open Fiscal Forensics Framework (OFFF)

A local-first, open-source platform designed for deterministic public ledger auditing, automated anomaly detection, and data-driven risk screening.

By analyzing structured state financial data against immutable statistical constants (such as Benford's Law and Shannon Entropy), this framework isolates metadata variances and algorithmic patterns. These mathematical indicators serve as statistical anomalies signaling potential irregularities—such as manual ledger adjustments, rounding inflation, or synthetic record generation. These metrics function purely as a triage mechanism to flag high-risk entries for targeted human expertise and formal forensic audits, rather than serving as definitive legal proof of systemic manipulation.

## 📊 Core Analytical Methodology

The framework balances analytical automation through a two-layer mathematical screening pipeline:

1. **Logarithmic Frequency Deviation:** Evaluates first-digit conformity utilizing the Chi-Square ($X^2$) goodness-of-fit test.
2. **Information Density Measurement:** Computes numeric randomness using Shannon Entropy matrices to detect synthetic or linear batch entry generation.

## 🔧 Technical Blueprint: Rule #3 (Blockchain Budgeting)

The technical core of this repository provides an alternative architecture for state fiscal operations. By shifting fiscal management to a public ledger governed by automated smart contracts, the system programmatically mitigates administrative human error and structural corruption risks.

### 🛡️ Smart Contract Governance Model

```text
       [ Public Revenue ] -> ( Taxes, Fees, Sovereign Inflow )
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  SMART CONTRACT ENGINE  │
                     └─────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ Audit Check: Public Tender Verified? ]         [ Market Price Alignment Check ]
         │                                                 │
         ├─► YES: Execute Transfer                         ├─► MATCH: Secure Transaction
         │                                                 │
         └─► NO: BLOCK TRANSACTION                         └─► MISMATCH: FLAG ANOMALY
```

### 📋 Protocol Core Mechanics:

* **Public Ledger Transparency:** Every vector of state revenue, tax collection, and administrative assessment is bound to universally verifiable public addresses.
* **Conditional Disbursement:** Funds are programmatically locked. If a transaction lacks precise metadata specifications or fails to verify an open public tender, the execution contract throws an exception and rolls back the state transition.
* **Automated Anomaly Tagging:** If procurement values significantly deviate from indexed open-market baselines, the transaction is automatically flagged and halted on-chain.
* **Deficit Elimination:** Real-time visibility into the expenditure-to-revenue ratio neutralizes undocumented balance sheet leakages.

### 💻 Reference Implementation: `TransparencyBudget.sol`

Below is the conceptual smart contract implementation validating Rule #3:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TransparencyBudget {
    address public auditor;
    
    struct Transaction {
        address recipient;
        uint256 amount;
        string specification;
        bool hasPublicTender;
        uint256 marketPriceLimit;
        bool isFlagged;
        bool executed;
    }
    
    mapping(uint256 => Transaction) public registry;
    uint256 public txCount;

    event TransactionProposed(uint256 txId, address recipient, uint256 amount);
    event TransactionExecuted(uint256 txId, address recipient, uint256 amount);
    event AnomalyFlagged(uint256 txId, string reason);

    modifier onlyAuditor() {
        require(msg.sender == auditor, "Unauthorized access.");
        _;
    }

    constructor() {
        auditor = msg.sender;
    }

    function proposeTransaction(
        address _recipient, 
        uint256 _amount, 
        string memory _specification, 
        bool _hasPublicTender,
        uint256 _marketPriceLimit
    ) external onlyAuditor {
        txCount++;
        
        bool flag = false;
        if (_amount > _marketPriceLimit) {
            flag = true;
            emit AnomalyFlagged(txCount, "Price exceeds verified open-market rates.");
        }

        registry[txCount] = Transaction({
            recipient: _recipient,
            amount: _amount,
            specification: _specification,
            hasPublicTender: _hasPublicTender,
            marketPriceLimit: _marketPriceLimit,
            isFlagged: flag,
            executed: false
        });

        emit TransactionProposed(txCount, _recipient, _amount);
    }

    function executeTransaction(uint256 _txId) external {
        Transaction storage txn = registry[_txId];
        
        require(!txn.executed, "Transaction already processed.");
        require(txn.hasPublicTender, "BLOCKED: No open public tender verified.");
        require(!txn.isFlagged, "BLOCKED: Unresolved pricing anomaly detected.");
        require(bytes(txn.specification).length > 0, "BLOCKED: Specification missing.");

        txn.executed = true;
        payable(txn.recipient).transfer(txn.amount);
        
        emit TransactionExecuted(_txId, txn.recipient, txn.amount);
    }

    receive() external payable {}
}
```

## 🔬 Forensic Chain 361

This repository maintains comprehensive documentation trails tracking structural linkages within global network vectors:

* **Corporate Transformations:** Chronological mapping of legacy corporate entities (e.g., Tutogen) transitioning through structural consolidations (RTI, 2008).
* **Backchannel Audit Vectors:** Structural analysis of corporate shells and financial proxy mechanics (e.g., Maxim Group "361 backdoor" notifications).
* **Network Nodes:** Documented communication paths linking high-profile asset management structures (e.g., Epstein network vectors / Steven Victor internal data logs).
* **Procurement Audits:** Tracking institutional war profiteering through the European Transparency Register and military expenditure subsidies.

## 🔗 Repository File Index & Live Documentation

Explore the components of this framework directly:

* 📜 `index.html` (Live Page) – Core multilingual architectural and interface hub.
* ⚡ `index-manifest.html` (Live Page) – Freedom Manifesto: 4 Universal Rules and Merit-Order analysis (€1.485T audit scope).
* 🧪 `sound_of_freedom_awareness.html` (Live Page) – Global missing children tracking portal and international awareness node.
* ⛓️ `361-lanac.html` (Live Page) – Granular forensic evidence chain (Tutogen, RTI, Maxim Group, Epstein network datasets).
* 🗺️ `blockchain-361-vodic.html` (Live Page) – Structural technical blueprint for decentralized budgetary architectures.

## 🛡️ Anonymous Whistleblower Protocol (Anti-Censorship Node)

To protect investigators and insiders reporting illicit logistics, systemic corruption, or energy market manipulation, the framework integrates a fully functional, zero-knowledge client-side encryption and decentralized dispatch engine directly within `361-lanac.html`.

```text
 [ Whistleblower / Citizen ] 
            │
            ▼
┌───────────────────────────────────────┐
│ Browser locally encrypts the payload  │ -> Utilizing the #BajteBrothers Public PGP Key
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Encrypted payload upload to IPFS      │ -> Decentralized, censorship-resistant delivery
└───────────────────────────────────────┘
            │
            ▼
 [ Immutable IPFS Hash (CID) Generated ] -> Anchored directly into the Blockchain Budget Ledger
```

### ⚙️ Production Infrastructure

* **Zero-Knowledge Architecture:** Files are securely encrypted via OpenPGP within the user’s localized browser sandbox context using OpenPGP.js (v5.11.1). No unencrypted payloads or cleartext vectors are ever exposed to the network spine.
* **Live Web3 Routing:** Fully integrated with the decentralized Crust Network IPFS API (https://crustwebsites.net) for permissionless, permanent, and immutable hosting, neutralizing corporate takedown notices or bureaucratic suppression.
* **Global Access & Validation:** Broadcasted payloads generate an unalterable Content Identifier (CID). This permanent cryptographic timestamp can be registered within our Solidity budget ledger ecosystem and retrieved instantaneously via any public IPFS gateway worldwide (e.g., `ipfs.io` or `gateway.ipfs.io`).

### 📦 Network Data Envelope Format

Upon submission, the engine automates the following secure payload envelope:

```text
[ Raw Document ] ──► ( Local Browser Sandbox ) ──► [ OpenPGP Encrypted Blob ]
                                                           │
                                                           ▼
[ Public IPFS Grid ] ◄── ( Live HTTPS POST ) ◄── [ Multi-part Form Data (.pgp) ]
           │
           ▼
[ Permanent IPFS CID Hash Generated ]
```

## 👥 Contribution Guidelines

We encourage independent developers, financial auditors, and open-source advocates to audit our decentralized blueprints:

* **Data Review:** Inspect raw document provenance records located in the index arrays.
* **Deployment & Testing:** Audit the algorithmic implementation mechanics of `TransparencyBudget`.
* **Public Discourse:** Engage in verified ecosystem analytics via our official YouTube Community Node.

Join the architecture. Eliminate the undocumented leakages.

🔬 Open-Source Forensic Analytics Core

The repository includes a functional Python core for data integrity evaluation and a decentralized Solidity consensus engine for peer validation.

📊 Statistical Anomaly Screening (forensic_core.py)

To identify structural data drift and mathematical distribution anomalies, the Python runtime utilizes a dual-layer statistical screening process:
• Benford's Law (First-Digit Anomalies): Executes a Chi-Square ($X^2$) goodness-of-fit test on the distribution of leading digits within financial datasets. Significant deviations from the logarithmic baseline function as statistical indicators of anomalous distributions, rather than definitive legal proof of ledger falsification.
• Shannon Entropy (Digit Randomness): Measures information density and character uniformity to flag synthetically generated patterns or unusual structural uniformity. These flags serve as a triage layer to prioritize target arrays for comprehensive human accounting reviews.

⛓️ Multi-Signature Voting Validation (ConsensusLedger.sol)

To neutralize the Single Point of Failure (SPOF) risks inherent in centralized administrative accounts, the ecosystem utilizes a decentralized ledger validation model.
Financial ingestion tracks and public procurement IDs can pass a peer-governed multi-signature verification loop prior to ledger state synchronization. These blockchain consensus barriers verify protocol compliance and metadata alignment, ensuring data state consistency while human auditors execute substantive verification of fact.
We invite peer-reviewers, data journalists, and OSINT developers to clone, extend, and benchmark these core mathematical screening modules against active public ledger resources.

🚀 Live Interactive Dashboard & Real-World Validation (MVP Launch)

The framework has evolved from a local command-line runtime into a fully deployed, desktop-first web application interface built with Streamlit (app.py), bridging the transparency gap between raw ledger databases and public readability.

🛡️ Privacy-First Execution (privacy_banner.js)

To ensure absolute alignment with global digital privacy mandates, the interface enforces a strict Privacy-by-Design consensus banner. All automated live-audit features and local processes run 100% locally within the client’s browser sandbox environment. No data vectors or temporary memory streams are ever cached or transmitted to external server arrays.

📊 Empirical Case Study: City of Labin 2025 Ledger Audit

The analytical pipeline was successfully benchmarked and validated using authentic federal expenditure assets extracted from the official open-data registry of the City of Labin (Croatia) for the fiscal year 2025.
• Automated Processing Ingestion (auto_adapter.py): The engine dynamically parsed the localized spreadsheet matrix, isolated the financial volume column at index 1, and routed transaction streams directly into the forensic analyzer core with zero manual mapping.
• Forensic Audit Reporting Output (forensic_audit_report.pdf):
	• Benford's Law Chi² Score: 0.0134 (Critical Threshold: 15.507) -> PASSED ✓
	• Shannon Entropy Value: 3.2868 bits (Natural Baseline Minimum: >= 3.0) -> PASSED ✓
	• Risk Assessment: LOW RISK — The distribution functions of leading and internal digits exhibit high logarithmic conformity to Benford's Law and expected information density metrics. This serves as an operational integrity checkpoint indicating consistent formatting baselines, though it remains a statistical screening model and does not replace substantive institutional or legal verifications of truth.

⚙️ Local Deployment & Sandbox Sandbox Setup

To initialize the interactive sandbox dashboard configuration on your local workstation, clone the repository, navigate to the source directory, and deploy the application layer:
```powershell

1. Install verified, safe-mode execution libraries

pip install streamlit matplotlib reportlab

2. Launch the interactive Citizen Platform Central Control

streamlit run app.py
```

🗺️ Framework Evolution & Strategic Roadmap

To explore the long-term decentralized roadmap planning, permissionless peer networks, and upcoming ledger historicization milestones, consult our main core blueprint:
🔗 Read the complete technical roadmap (ROADMAP.md)

📦 Release Verification

v1.0.0-MVP — Initial Open-Source Civic Audit Core
The #BajteBrothers Citizen Budget Intelligence Platform has successfully completed its initial verification cycle.
The framework ships with a functional Benford's Law and Shannon Entropy screening engine, automated dataframe identification mechanics, integrated Streamlit interface layers, and automated PDF certification export tools. By decoupling the architecture from monolithic monolithic cloud dependencies, the system delivers an unalterable, fully reproducible civic audit environment.
The execution without data exceptions over the entire 2025 fiscal ledger of the City of Labin proves that transparent civic validation loops require zero central gatekeepers—only clean logic, public traceability, and mathematically consistent evidence.
This release finalizes the complete MVP stack:
• forensic_core.py
• auto_adapter.py
• app.py
• pdf_generator.py
• .gitignore
• LICENSE
• ROADMAP.md
The project is now formally structured under the open-source MIT License. This concludes the primary repository standardization phase. The logic is now public infrastructure.
Sound of Freedom — MVP Polish Pass Checkpoint
feat: finalize MVP polish pass for civic audit dashboard
Disclaimer: This framework provides statistical and data structure analytics. All computations and anomaly identification output serve as probability models to direct human expert review and formal forensic auditing. They do not constitute a final declaration of legal or fiscal non-compliance.

