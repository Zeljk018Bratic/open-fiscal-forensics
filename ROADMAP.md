1. ROADMAP.md (refactored)
Markdown
# Roadmap

## Mission

#BajteBrothers is a local-first, open-source civic intelligence platform for public budget transparency. The roadmap below defines the technical evolution from a validated single-user forensic dashboard into a resilient, community-reviewed, and decentralized evidence network.

The system objective is strict and technical: produce verifiable budget intelligence using open datasets, maintain source provenance, and support independent validation without introducing a single point of failure.

---

## Development Principle

All milestones below are intentionally constrained to software architecture, reproducibility, and verifiable technical delivery. They are designed to preserve the existing forensic logic while expanding the platform around it.

---

## Milestone v1.1 — Data Enrichment & Local Reporting

**Status: Completed**

### Objective
Increase the operational value of the current dashboard by turning the local workflow into a structured forensic evidence pipeline with metadata-aware reporting and exportable summaries.

### Delivered
- Automatic CSV column detection via `auto_adapter.py` integrated into the Streamlit upload workflow
- Provenance metadata embedded in PDF certificates (source, jurisdiction, year, uploader, SHA-256, timestamp)
- JSON and Markdown export of audit payloads
- Clean public summary block for journalists and reviewers

---

## Milestone v1.2 — Community Submission Registry

**Status: Completed & Closed**

### Objective
Turn the project into a local registry for validated budget submissions, enabling traceable intake, review management, and independent review workflows without requiring a full external infrastructure.

### Delivered
- SQLite-backed `DatabaseRegistry` with full audit lifecycle schema
- Review-status model preparation (Verified / Pending / Flagged / Rejected)
- Form-state persistence across Streamlit reruns
- Immutable registration of every successful audit (metrics, provenance, full JSON manifest)
- Risk-level filtering and historical query interface

---

## Milestone v2.0 — Decentralized Validation Layer

**Status: Phase 2 & Phase 3 Completed · Phase 4 (Hardening) In Progress**

### Objective
Move from a local trusted registry to a decentralized validation mesh where independent nodes can share audit results and exchange evidence using peer-to-peer protocols while preserving privacy and traceability.

### Phase 2 — P2P Mesh Hardening (Completed & Closed)
- Secure GossipSub-style message schema (`AUDIT_MANIFEST`, `ATTESTATION`, `HEARTBEAT`)
- HMAC-SHA256 signature verification (timing-safe)
- Strict dictionary schema validation with instant drop of malformed packets
- Bounded sliding seen-set (`BoundedSeenSet` / OrderedDict LRU) preventing re-broadcast loops
- Multi-thread architecture (listener, heartbeat, peer prune) — all daemon, soft-fail
- Epidemic fanout gossip (default fanout = 3) with TTL decrement
- Zero external dependencies (pure Python standard library)

### Phase 3 — App Integration (Completed & Closed)
- Third Streamlit tab: **🌐 Mesh Validation Network**
- Thread-safe node lifecycle control (Start / Stop) with dynamic listener port
- Automated gossip fanout: successful Tab-1 audits are automatically broadcast when the engine is active
- Live telemetry grid driven by `node.status()` (peers, seen messages, inbox)
- Native HTML/CSS peer table and expandable gossip stream (pandas-free)
- Lazy-polling inbox drain — main Streamlit thread never blocks

### Phase 4 — Production Hardening & Documentation (Current)
- Configuration surface for peers and HMAC secret
- Operator deployment guide (this document)
- ROADMAP formal closure of completed phases
- Optional pure-Python IPFS CID resolver stub (future)

### Phase 5 — Community Validation Mesh (Planned)
- Public bootstrap peer list
- Attestation scoring and challenge protocol
- Independent third-party confirmation of audits without trusting the originator

---

## Technical Priority Order (Updated)

1. ~~v1.1 — Data Enrichment & Local Reporting~~ → **Done**
2. ~~v1.2 — Community Submission Registry~~ → **Done**
3. ~~v2.0 Phase 2/3 — GossipSub + Mesh Tab~~ → **Done**
4. v2.0 Phase 4 — Hardening & Docs → **In Progress**
5. v2.0 Phase 5 — Community Mesh → Future

---

## Final State Target

The end state remains a transparent, reproducible, and community-governed budget intelligence platform capable of:
- ingesting public budget data locally
- identifying the financial signal automatically
- generating forensic PDF evidence
- registering provenance and review history
- distributing validation results across a decentralized trust network

This roadmap records a technically disciplined path from a validated MVP into a robust civic watchdog system.

2. P2P Deployment Guide
Markdown
# P2P Node Deployment Guide
## Open Fiscal Forensics Framework — Mesh Validation Network

**Audience:** Independent operators, civic auditors, OSINT researchers  
**Requirements:** Python 3.10+, Streamlit, the two Phase-2/3 modules (`p2p_network_mesh.py`, `app.py`)  
**Dependencies:** None beyond the Python standard library for the mesh engine.

---

### 1. Launch the Dashboard

```bash
streamlit run app.py
Open the browser at the address shown (normally http://localhost:8501 ).

2. Activate the Local Node
Switch to the third tab: 🌐 Mesh Validation Network.
Set the desired Local listener port (default 6001).
Choose a free port above 1024. Avoid privileged ports.
Click ▶️ Start P2P Engine.
The telemetry panel will show 🟢 ACTIVE and your Node ID.
The node now listens for inbound TCP connections and runs background heartbeat / peer-pruning threads. The Streamlit UI remains fully responsive.

3. Connect to Bootstrap Peers
Under 🔗 Connect to remote peer:
Enter the remote operator’s host (IP or hostname) and port.
Click Connect.
Successful connections appear in the Active Peers table together with last-seen timestamps. Dead peers are automatically pruned after 90 seconds of silence.
For a minimal two-node test on the same machine:
Node
Port
Action
A
6001
Start engine
B
6002
Start engine → Connect to 127.0.0.1:6001


4. Automatic Evidence Propagation
Whenever an operator completes a successful budget audit in 📊 Live Budget Pipeline while the local engine is active, the application:
Persists the audit to the SQLite registry.
Constructs a signed AUDIT_MANIFEST packet (municipality, year, Chi², entropy, risk level, file SHA-256).
Broadcasts the packet via epidemic fanout to the current peer set.
Receiving nodes validate the HMAC signature, perform schema checks, deduplicate via the bounded seen-set, and may issue an ATTESTATION (AGREE / CHALLENGE).

5. Monitoring
Live Telemetry shows Node ID, engine state, peer count and total seen messages.
Incoming Gossip Stream lists the most recent packets. Use 🔄 Refresh inbox to pull newly arrived messages. Packets are also accumulated in a local session history (max 200 entries).

6. Operational Notes
The default HMAC secret is a bootstrap shared value suitable only for trusted initial meshes. Replace it before public exposure (future Phase-4 configuration surface).
All network work runs in daemon threads. Stopping the Streamlit process cleanly shuts the node down.
No central server is required. Bootstrap is performed by explicit peer connection or by sharing a short list of known listening addresses among operators.
Full CSV files never leave the local machine unless an explicit evidence-request protocol (future) is used. Only cryptographic digests and aggregate metrics travel the mesh.

7. Verification Checklist
Engine shows 🟢 ACTIVE
At least one peer appears in the Active Peers table
A completed audit in Tab 1 produces a “📡 AUDIT_MANIFEST broadcast” notice
The remote node’s Gossip Stream displays the corresponding packet
Signature and schema validation reject any tampered packet

Document version: Milestone v2.0 Phase 4 · #BajteBrothers
text
---

### 3. Conventional Git Commit Message
feat(mesh): complete Milestone v2.0 Phase 2/3 — GossipSub engine + Mesh Validation tab
Introduce production-grade decentralized validation layer:
p2p_network_mesh.py: stdlib-only GossipSub node with HMAC-SHA256 signatures, strict schema validation, BoundedSeenSet deduplication, epidemic fanout, heartbeat/peer pruning, and thread-safe inbox.
app.py: third tab "🌐 Mesh Validation Network" with Start/Stop controls, dynamic listener port, live telemetry from node.status(), native HTML peer table, and automated AUDIT_MANIFEST broadcast after registry save.
ROADMAP.md: mark v1.2 and v2.0 Phase 2/3 as completed and closed.
All network work remains non-blocking; zero new runtime dependencies.
Validated against compilation and schema test suite.
Refs: #BajteBrothers Milestone v2.0

