# Roadmap

## Mission

#BajteBrothers is a local-first, open-source civic intelligence platform for public budget transparency. The roadmap below defines the technical evolution from a validated single-user forensic dashboard into a resilient, community-reviewed, and decentralized evidence network.

The system objective is strict and technical: produce verifiable budget intelligence using open datasets, maintain source provenance, and support independent validation without introducing a single point of failure.

---

## Development Principle

All milestones below are intentionally constrained to software architecture, reproducibility, and verifiable technical delivery. They are designed to preserve the existing forensic logic while expanding the platform around it.

---

## Milestone v1.1 — Data Enrichment & Local Reporting

Status: Short-term / immediate implementation

### Objective

Increase the operational value of the current dashboard by turning the local workflow into a structured forensic evidence pipeline with metadata-aware reporting and exportable summaries.

### Technical Scope

#### 1. Integrate automatic CSV column detection into the Streamlit UI
- Connect the upload workflow directly to `auto_adapter.py`.
- Detect the monetary column automatically after the CSV is uploaded.
- Surface the detected index and column name in the dashboard.
- Preserve fallback logic when the header is non-standard or multilingual.
- Log the selected column in the report context for transparency.

#### 2. Add provenance metadata to the PDF certificate
- Extend `pdf_generator.py` to include provenance fields in the generated report.
- Embed metadata in the final PDF such as:
  - source name / link
  - jurisdiction / municipality
  - fiscal year
  - uploader identity
  - SHA-256 file hash
  - upload timestamp
- Keep the report layout clean and publication-ready for public release.

#### 3. Export structured summaries in machine-readable formats
- Add JSON export for the audit payload.
- Add Markdown export for quick release summaries.
- Include both raw technical results and human-readable risk notes.
- Generate a compact public summary suitable for journalists, technical reviewers, and community distribution.

#### 4. Improve report composition and public readability
- Add a summary block with:
  - dataset name
  - source
  - year
  - risk level
  - detected amount column
  - pass/fail thresholds
- Keep the visual output deterministic and reproducible.

### Expected Deliverables
- Streamlit upload + detection workflow integrated end-to-end
- PDF certificate enriched with provenance metadata
- JSON and Markdown export actions from the UI
- Consolidated public summary output for reuse and sharing

### Acceptance Criteria
- A CSV upload automatically resolves the financial column without manual intervention.
- The generated PDF includes provenance and validation context.
- Users can export technical and public-facing summaries directly from the dashboard.
- The existing forensic logic remains unchanged and reproducible.

---

## Milestone v1.2 — Community Submission Registry

Status: Medium-term / next operational layer

### Objective

Turn the project into a local registry for validated budget submissions, enabling traceable intake, review management, and independent review workflows without requiring a full external infrastructure.

### Technical Scope

#### 1. Local registry with persistent storage
- Implement a local SQLite database as the canonical metadata store.
- Create a schema for:
  - dataset metadata
  - provenance details
  - analysis result snapshots
  - reviewer notes
  - status transitions
  - checksum records
- Support historical queries by dataset, source, municipality, and year.

#### 2. Review-status lifecycle
Implement a formal review state model:
- Verified
- Pending
- Flagged
- Rejected

Each dataset should track:
- current status
- who changed the status
- timestamp of change
- reason for transition
- evidence references

#### 3. Independent validator preparation
- Add a validator record model with identity and signing capability metadata.
- Prepare a signature log so that future validators can attest to results without changing the underlying analytics engine.
- Store signed summaries in a local append-only log format.
- Keep signature verification local and reproducible.

#### 4. Audit history and reproducibility
- Each run should save a snapshot of:
  - source file hash
  - parsed amount column index
  - result metrics
  - generated PDF path
  - generation timestamp
- Preserve the original dataset and analysis output for later inspection.

### Expected Deliverables
- SQLite-based submission registry
- Dataset review queue with lifecycle management
- Signed audit history records
- Local validator identity and attestation layer

### Acceptance Criteria
- Every uploaded budget is persisted with provenance and run history.
- Review status transitions are recorded immutably in the local database.
- A validator can inspect a dataset and sign a result without altering the core analysis rules.
- The system remains local-first and does not require a server deployment.

---

## Milestone v2.0 — Decentralized Validation Layer

Status: Long-term / network-scale extension

### Objective

Move from a local trusted registry to a decentralized validation mesh where independent nodes can share audit results and exchange evidence using peer-to-peer protocols while preserving privacy and traceability.

### Technical Scope

#### 1. Serverless P2P groundwork
- Implement a browser- and Node-compatible peer layer with `js-libp2p`.
- Use a modular peer identity and connection lifecycle.
- Define message schemas for:
  - dataset announcement
  - provenance hash exchange
  - audit result broadcast
  - validator attestation
  - evidence request / response

#### 2. Gossipsub channel architecture
- Create dedicated channels for:
  - dataset announcements
  - audit result publication
  - validator signatures
  - community challenge events
- Ensure messages are compact and signed to avoid spam and spoofing.
- Allow rapid propagation of findings across the mesh network.

#### 3. WebRTC direct evidence exchange
- Support direct peer-to-peer connections between browser nodes.
- Exchange signed PDF summaries, metadata packs, or verification bundles.
- Use WebRTC for low-latency evidence transfer in local network or adjacent peer setups.
- Keep the protocol optional and privacy-aware; raw sensitive files should remain local unless explicitly shared.

#### 4. Decentralized trust model
- Introduce multiple independent validator identities.
- Allow network peers to confirm provenance and audit attestation.
- Model trust as consensus over signed observations rather than a central authority.
- Enable public validation without centralized control.

### Expected Deliverables
- Peer-to-peer validation protocol layer
- Gossipsub-based result propagation
- WebRTC-based evidence transport
- Signed decentralized audit network

### Acceptance Criteria
- Independent nodes can announce and share verified budget findings.
- Results propagate through the mesh without reliance on a single server.
- Evidence can be exchanged directly between peers with traceable provenance.
- The platform remains aligned with civic transparency and open-source verification principles.

---

## Technical Priority Order

### Phase priority
1. v1.1 — Data Enrichment & Local Reporting
2. v1.2 — Community Submission Registry
3. v2.0 — Decentralized Validation Layer

### Rationale
- v1.1 makes the current forensic pipeline production-usable and publication-ready.
- v1.2 turns the system into a documented and reviewable evidence archive.
- v2.0 extends the system into a resilient distributed validation network without compromising the local-first design.

---

## Implementation Notes

- Preserve the mathematical and forensic core as an invariant layer.
- Expand around the analytics engine rather than rewriting it.
- Favor plain, verifiable data formats: CSV, JSON, Markdown, SQLite, signed JSON payloads.
- Keep private-sensitive data local wherever possible.
- Design all network interactions as optional overlays to the core local workflow.

---

## Final State Target

The end state is a transparent, reproducible, and community-governed budget intelligence platform capable of:
- ingesting public budget data locally
- identifying the financial signal automatically
- generating forensic PDF evidence
- registering provenance and review history
- distributing validation results across a decentralized trust network

This roadmap defines a technically disciplined path from a validated MVP into a robust civic watchdog system.
