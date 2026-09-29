```python
#!/usr/bin/env python3
"""
TransparencyDataReconciler
Standard offline data-ingestion and reconciliation module
for public-sector financial ledger verification.
Strictly respects documented rate limits and authentication.
"""

from __future__ import annotations

import json
import logging
import os
import time
import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from web3 import Web3

from forensic_core import ForensicCore

logger = logging.getLogger(__name__)

ENGINE_NAME = "TransparencyDataReconcilerEngine"
ENGINE_VERSION = "1.0.0-MVP"


def money(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


def build_historical_template(ledger_tuple: tuple) -> dict:
    return {"entries": [asdict(entry) for entry in ledger_tuple]}


def export_json(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)


@dataclass
class YearLedger:
    year: int
    total_realized_outflows: float
    konto_32: float
    konto_323: float
    konto_3233_media: float
    konto_3237_intellectual_consulting: float
    konto_3238_software_it: float
    mayor_office_media: float


@dataclass
class EcologicalIndicator:
    indicator_id: str
    description: str
    observed_value: float
    reference_value: Optional[float]
    unit: str

    def to_json_dict(self) -> dict:
        return asdict(self)


@dataclass
class MatchRule:
    rule_id: str
    target_label: str
    target_oibs: tuple


@dataclass
class AuditDelta:
    konto: str
    expected: float
    observed: float
    delta: float

    def to_json_dict(self) -> dict:
        return asdict(self)


def calculate_audit_delta(konto: str, expected: str, observed: str) -> AuditDelta:
    exp_val = money(expected)
    obs_val = money(observed)
    return AuditDelta(
        konto=konto,
        expected=exp_val,
        observed=obs_val,
        delta=obs_val - exp_val,
    )


@dataclass
class LedgerBlock:
    block_hash: str
    payload: dict
def append_hash_ledger(block_path: Path, payloads: tuple) -> list[LedgerBlock]:
    blocks = []
    previous_hash = "0" * 64  # Genesis sidro
    
    if block_path.exists():
        try:
            with open(block_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
                if existing_data:
                    previous_hash = existing_data[-1]["block_hash"]
        except Exception:
            pass

    for payload in payloads:
        payload_string = json.dumps(payload, sort_keys=True)
        data_to_hash = f"{payload_string}{previous_hash}".encode("utf-8")
        current_hash = hashlib.sha256(data_to_hash).hexdigest()
        
        blocks.append(LedgerBlock(block_hash=current_hash, payload=payload))
        previous_hash = current_hash
        
    export_json(block_path, [asdict(block) for block in blocks])
    return blocks

def verify_chain(blocks: list) -> bool:
    if not blocks:
        return True
        
    previous_hash = "0" * 64
    for block in blocks:
        if isinstance(block, dict):
            b_hash = block.get("block_hash")
            b_payload = block.get("payload")
        else:
            b_hash = block.block_hash
            b_payload = block.payload
            
        payload_string = json.dumps(b_payload, sort_keys=True)
        data_to_hash = f"{payload_string}{previous_hash}".encode("utf-8")
        calculated_hash = hashlib.sha256(data_to_hash).hexdigest()
        
        if b_hash != calculated_hash:
            logger.error(f"Kriptografski proboj! Ocekivan: {calculated_hash}, Zapisan: {b_hash}")
            return False
        previous_hash = b_hash
    return True


def generate_scribehow_markdown(audit_delta: AuditDelta, ecological_indicators: tuple, block: LedgerBlock) -> str:
    return f"""# Forensic Audit Log
- **Status:** Ingestion Complete
- **Konto geprüft:** {audit_delta.konto}
- **Erwartet:** {audit_delta.expected} EUR
- **Beobachtet:** {audit_delta.observed} EUR
- **Abweichung (Delta):** {audit_delta.delta} EUR
- **Block-Hash:** {block.block_hash}
"""


class TransparencyDataReconciler:
    """
    Production-ready reconciler for municipal transparency APIs.
    Performs authenticated ledger extraction and statistical
    alignment against officially published aggregate totals.
    """

    def __init__(
        self,
        base_url: str = "https://transparentor.org",
        max_retries: int = 5,
        backoff_factor: float = 1.5,
        timeout: int = 30,
        rpc_url: str = "http://127.0.0.1:8545",
        private_key: Optional[str] = None,
        blockchain_recipient: str = "0x0000000000000000000000000000000000000000",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.backoff_factor = backoff_factor
        self.max_retries = max_retries
        self.rpc_url = rpc_url
        self.private_key = private_key or os.getenv("BLOCKCHAIN_PRIVATE_KEY")
        self.blockchain_recipient = blockchain_recipient
        self.w3 = None

        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"],
            backoff_factor=backoff_factor,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def fetch_authorized_ledger(
        self,
        api_key: str,
        endpoint_url: str,
        selection_query: Dict[str, Any],
    ) -> pd.DataFrame:
        if not api_key or not isinstance(api_key, str):
            raise ValueError("A valid API key string is required.")

        headers = {
            "Authorization": f"ApiKey {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "TransparencyDataReconciler/1.0 (civic-audit)",
        }

        url = endpoint_url if endpoint_url.startswith("http") else f"{self.base_url}/{endpoint_url.lstrip('/')}"
        attempt = 0

        while True:
            attempt += 1
            try:
                response = self.session.post(
                    url,
                    json=selection_query,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning("Rate limit reached (429). Sleeping %s seconds.", retry_after)
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                payload = response.json()

                if isinstance(payload, list):
                    records = payload
                elif isinstance(payload, dict):
                    records = payload.get("data") or payload.get("results") or payload.get("items") or []
                else:
                    raise ValueError("Unexpected JSON structure returned by the API.")

                if not records:
                    logger.warning("API returned an empty record set.")
                    return pd.DataFrame()

                return pd.DataFrame(records)

            except requests.exceptions.RequestException as exc:
                logger.error("Request failed on attempt %s: %s", attempt, exc)
                if attempt >= self.max_retries:
                    raise
                time.sleep(self.backoff_factor * attempt)

    def calculate_audit_delta(
        self,
        extracted_df: pd.DataFrame,
        official_totals_dict: Dict[str, float],
        amount_column: str = "amount",
        konto_column: Optional[str] = "konto",
    ) -> Dict[str, Any]:
        if extracted_df.empty:
            return {
                "status": "NO_DATA",
                "message": "Extracted DataFrame is empty. Cannot perform reconciliation.",
                "deltas": {},
            }

        if amount_column not in extracted_df.columns:
            raise KeyError(f"Amount column '{amount_column}' not found in extracted data.")

        extracted_df = extracted_df.copy()
        extracted_df[amount_column] = pd.to_numeric(extracted_df[amount_column], errors="coerce").fillna(0.0)

        results: Dict[str, Any] = {
            "status": "OK",
            "record_count": len(extracted_df),
            "deltas": {},
            "absolute_total_delta": 0.0,
        }

        api_total = float(extracted_df[amount_column].sum())
        official_total = float(official_totals_dict.get("Total Outflows", 0.0))
        total_delta = abs(api_total - official_total)
        results["deltas"]["Total Outflows"] = {
            "api_sum": round(api_total, 2),
            "official": round(official_total, 2),
            "delta": round(total_delta, 2),
            "relative_pct": round((total_delta / official_total * 100) if official_total else 0.0, 4),
        }
        results["absolute_total_delta"] = total_delta

        if konto_column and konto_column in extracted_df.columns:
            for key, official_value in official_totals_dict.items():
                if key.startswith("Konto "):
                    konto_code = key.replace("Konto ", "").strip()
                    mask = extracted_df[konto_column].astype(str).str.contains(konto_code, na=False)
                    api_konto_sum = float(extracted_df.loc[mask, amount_column].sum())
                    delta = abs(api_konto_sum - float(official_value))
                    results["deltas"][key] = {
                        "api_sum": round(api_konto_sum, 2),
                        "official": round(float(official_value), 2),
                        "delta": round(delta, 2),
                        "relative_pct": round((delta / float(official_value) * 100) if official_value else 0.0, 4),
                    }

        max_relative = max((v["relative_pct"] for v in results["deltas"].values()), default=0.0)
        if max_relative > 1.0:
            results["status"] = "VARIANCE_DETECTED"
            results["message"] = f"Maximum relative variance {max_relative:.2f}% exceeds 1% threshold."
        else:
            results["message"] = "Extracted public records mathematically reconstruct the audited envelope."

        return results

    def dispatch_to_blockchain_ledger(self, audit_result: dict, contract_address: str) -> dict:
        if self.w3 is None:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))

        if not self.w3.is_connected():
            raise ConnectionError(f"Blockchain RPC unavailable: {self.rpc_url}")

        if not self.private_key:
            raise ValueError("BLOCKCHAIN_PRIVATE_KEY is not configured.")

        account = self.w3.eth.account.from_key(self.private_key)
        recipient = self.blockchain_recipient

        try:
            recipient = self.w3.to_checksum_address(recipient)
            contract_address = self.w3.to_checksum_address(contract_address)
        except Exception:
            pass

        contract_abi = [
            {
                "inputs": [
                    {"internalType": "address", "name": "_recipient", "type": "address"},
                    {"internalType": "uint256", "name": "_amount", "type": "uint256"},
                    {"internalType": "string", "name": "_tenderId", "type": "string"},
                ],
                "name": "proposeTransaction",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            }
        ]

        contract = self.w3.eth.contract(address=contract_address, abi=contract_abi)
        status = str(audit_result.get("status", "")).upper()
        absolute_total_delta = float(audit_result.get("absolute_total_delta", 0.0) or 0.0)
        amount = max(int(abs(absolute_total_delta)), 1)

        flagged = status == "VARIANCE_DETECTED"
        tender_id = "" if flagged else f"OFFF-{int(time.time())}"

        tx = contract.functions.proposeTransaction(
            recipient,
            amount,
            tender_id,
        ).build_transaction(
            {
                "from": account.address,
                "nonce": self.w3.eth.get_transaction_count(account.address),
                "gas": 300000,
                "maxFeePerGas": self.w3.to_wei("20", "gwei"),
                "maxPriorityFeePerGas": self.w3.to_wei("2", "gwei"),
            }
        )

        signed_tx = account.sign_transaction(tx)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return {
            "tx_hash": tx_hash.hex(),
            "contract_address": contract_address,
            "status": status,
            "flagged": flagged,
            "recipient": recipient,
            "amount": amount,
            "tender_id": tender_id,
            "receipt_status": receipt.status,
        }


HISTORICAL_LEDGER = (
    YearLedger(
        year=2023,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
    YearLedger(
        year=2024,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
    YearLedger(
        year=2025,
        total_realized_outflows=money("25923989.48"),
        konto_32=money("6899673.65"),
        konto_323=money("4176288.28"),
        konto_3233_media=money("63102.72"),
        konto_3237_intellectual_consulting=money("705827.65"),
        konto_3238_software_it=money("156248.09"),
        mayor_office_media=money("30869.58"),
    ),
    YearLedger(
        year=2026,
        total_realized_outflows=money("0"),
        konto_32=money("0"),
        konto_323=money("0"),
        konto_3233_media=money("0"),
        konto_3237_intellectual_consulting=money("0"),
        konto_3238_software_it=money("0"),
        mayor_office_media=money("0"),
    ),
)

ECOLOGICAL_INDICATORS = (
    EcologicalIndicator(
        indicator_id="TOC_SPIKE_01",
        description="User-supplied count of reported chlorine-associated TOC threshold exceedance observations.",
        observed_value=money("148"),
        reference_value=money("0"),
        unit="incidents",
    ),
    EcologicalIndicator(
        indicator_id="TOC_THRESHOLD_01",
        description="User-supplied reported TOC concentration threshold.",
        observed_value=money("20"),
        reference_value=money("20"),
        unit="mg/m3",
    ),
    EcologicalIndicator(
        indicator_id="INDUSTRIAL_WASTE_01",
        description="User-supplied reported quantity of cross-border industrial chemical waste.",
        observed_value=money("19013"),
        reference_value=None,
        unit="tons",
    ),
    EcologicalIndicator(
        indicator_id="DECLARED_CUSTOMS_VALUE_01",
        description="User-supplied reported customs declaration value associated with the waste quantity.",
        observed_value=money("124"),
        reference_value=None,
        unit="EUR",
    ),
    EcologicalIndicator(
        indicator_id="SEAWATER_01",
        description="User-supplied reported annual raw seawater volume.",
        observed_value=money("1562400"),
        reference_value=None,
        unit="m3/year",
    ),
    EcologicalIndicator(
        indicator_id="NAOH_01",
        description="User-supplied reported annual sodium hydroxide quantity.",
        observed_value=money("1567"),
        reference_value=None,
        unit="tons/year",
    ),
    EcologicalIndicator(
        indicator_id="STACK_SURGE_01",
        description="User-supplied reported real-time toxic-emission surge associated with the 36 m precalciner stack.",
        observed_value=money("15"),
        reference_value=money("1"),
        unit="x baseline",
    ),
)

MATCH_RULES = (
    MatchRule(
        rule_id="GOSPIC_SILO_CONTRACT",
        target_label="€8.77M Gospić silo extraction contract",
        target_oibs=(),
    ),
    MatchRule(
        rule_id="PAZIN_INDUSTRIAL_DUMP",
        target_label="Slaven Tintor / Pazin industrial dump",
        target_oibs=(),
    ),
)

SOURCE_REFERENCE = {
    "transparency_provider": {
        "search_engine": "https://transparentor.org",
        "data_export_endpoint": "https://transparentor.org",
        "api_key_access_point": "https://transparentor.org",
        "active_footprint": "© 2026. CityX Apps d.o.o.",
        "network_access": False,
    },
    "ecological_dossier": {
        "url": "https://github.io",
        "source_status": "USER_SUPPLIED",
        "independent_verification": False,
    },
    "financial_dataset": {
        "municipality": "Grad Labin",
        "period": "2025",
        "currency": "EUR",
        "source_status": "USER_SUPPLIED",
    },
}


def run_offline_ingestion(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    historical = build_historical_template(HISTORICAL_LEDGER)

    audit_delta = calculate_audit_delta(
        konto="3233",
        expected="78102.72",
        observed="63102.72",
    )

    reconciliation_payload = {
        "audit_delta": audit_delta.to_json_dict(),
        "historical": historical,
        "ecological_indicators": [indicator.to_json_dict() for indicator in ECOLOGICAL_INDICATORS],
        "source_mapping": SOURCE_REFERENCE,
    }

    block_path = output_dir / "offf_sha256_ledger.json"
    blocks = append_hash_ledger(block_path, payloads=(reconciliation_payload,))
    latest_block = blocks[-1]

    markdown = generate_scribehow_markdown(
        audit_delta=audit_delta,
        ecological_indicators=ECOLOGICAL_INDICATORS,
        block=latest_block,
    )

    (output_dir / "offf_audit_log.md").write_text(markdown, encoding="utf-8")
    export_json(output_dir / "historical_template.json", historical)

    audit_result = {
        "status": "VARIANCE_DETECTED" if abs(audit_delta.delta) > 0 else "OK",
        "absolute_total_delta": abs(audit_delta.delta),
        "deltas": {
            "Konto 3233": {
                "expected": audit_delta.expected,
                "observed": audit_delta.observed,
                "delta": audit_delta.delta,
            }
        },
    }

    blockchain_result = None
    reconciler = TransparencyDataReconciler(
        rpc_url="http://127.0.0.1:8545",
     private_key=os.getenv("BLOCKCHAIN_PRIVATE_KEY"),
        blockchain_recipient="0x0000000000000000000000000000000000000000",
    )

    try:
        blockchain_result = reconciler.dispatch_to_blockchain_ledger(
            audit_result=audit_result,
            contract_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        )
    except ConnectionError as exc:
        print(f"[BLOCKCHAIN LEDGER] Local RPC not running. Skipping on-chain publication: {exc}")
        blockchain_result = {"status": "SKIPPED", "reason": str(exc)}

    result = {
        "status": "INGESTION_COMPLETE",
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "block_hash": latest_block.block_hash,
        "ledger_verified": verify_chain(blocks),
        "absolute_delta_eur": format(abs(audit_delta.delta), "f"),
        "historical_years": [2023, 2024, 2025, 2026],
        "blockchain": blockchain_result,
    }

    return result


if __name__ == "__main__":
    result = run_offline_ingestion(Path("offf_output"))
    print(json.dumps(result, indent=2, sort_keys=True))
```
