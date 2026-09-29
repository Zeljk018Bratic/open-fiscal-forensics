```python
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

from eth_abi import decode as abi_decode
from eth_rlp import decode as rlp_decode
from eth_utils import keccak
from web3 import Web3


PROPOSE_SELECTOR = Web3.keccak(text="proposeTransaction(address,uint256,string)")[:4].hex()
TRANSACTIONS = {}


def decode_mock_propose_transaction(raw_hex: str):
    raw_hex = raw_hex.lower()
    if not raw_hex.startswith("0x"):
        raw_hex = "0x" + raw_hex

    raw_bytes = bytes.fromhex(raw_hex[2:])
    tx_fields = rlp_decode(raw_bytes)

    if len(tx_fields) < 6:
        return {
            "recipient": "0x0000000000000000000000000000000000000000",
            "amount": 0,
            "tender_id": "",
            "flagged": False,
        }

    tx_data = tx_fields[5]
    data_hex = "0x" + tx_data.hex()

    if len(data_hex) <= 10:
        return {
            "recipient": "0x0000000000000000000000000000000000000000",
            "amount": 0,
            "tender_id": "",
            "flagged": False,
        }

    selector_hex = data_hex[:10]
    if selector_hex != "0x" + PROPOSE_SELECTOR:
        return {
            "recipient": "0x0000000000000000000000000000000000000000",
            "amount": 0,
            "tender_id": "",
            "flagged": False,
        }

    call_data = bytes.fromhex(data_hex[2:][8:])
    recipient, amount, tender_id = abi_decode(["address", "uint256", "string"], call_data)
    return {
        "recipient": recipient.lower(),
        "amount": int(amount),
        "tender_id": tender_id,
        "flagged": tender_id == "",
    }


class MockBlockchainRPCHandler(BaseHTTPRequestHandler):
    server_version = "MockBlockchainRPC/1.0"

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path not in ("/", ""):
            self._send_json_error(-32601, f"Unknown path: {parsed.path}")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(raw_body)
        except json.JSONDecodeError:
            self._send_json_error(-32700, "Invalid JSON payload")
            return

        method = payload.get("method")
        params = payload.get("params", [])
        rpc_id = payload.get("id", 1)

        result = None
        error = None

        try:
            if method == "eth_blockNumber":
                result = "0x1"

            elif method == "eth_getTransactionCount":
                result = "0x0"

            elif method == "eth_sendRawTransaction":
                raw_hex = params[0]
                tx_info = decode_mock_propose_transaction(raw_hex)
                tx_hash = "0x" + Web3.keccak(bytes.fromhex(raw_hex[2:])).hex()
                TRANSACTIONS[tx_hash] = {
                    "hash": tx_hash,
                    "from": "0x0000000000000000000000000000000000000000",
                    "to": tx_info["recipient"],
                    "amount": tx_info["amount"],
                    "tender_id": tx_info["tender_id"],
                    "flagged": tx_info["flagged"],
                    "status": 0 if tx_info["flagged"] else 1,
                    "blockHash": "0x1111111111111111111111111111111111111111111111111111111111111111",
                    "blockNumber": "0x1",
                    "transactionIndex": "0x0",
                }

                if tx_info["flagged"]:
                    print("[BLOCKCHAIN LEDGER] ANOMALIE ERKANNT - STATUS: BLOCKED ❌")
                else:
                    print("[BLOCKCHAIN LEDGER] TRANSACTION APPROVED ✓")

                result = tx_hash

            elif method == "eth_getTransactionReceipt":
                tx_hash = params[0]
                tx = TRANSACTIONS.get(tx_hash)
                if tx is None:
                    result = None
                else:
                    result = {
                        "transactionHash": tx["hash"],
                        "transactionIndex": "0x0",
                        "blockHash": tx["blockHash"],
                        "blockNumber": tx["blockNumber"],
                        "from": tx["from"],
                        "to": tx["to"],
                        "cumulativeGasUsed": "0x0",
                        "gasUsed": "0x0",
                        "contractAddress": None,
                        "logs": [],
                        "status": "0x1" if tx["status"] == 1 else "0x0",
                        "effectiveGasPrice": "0x0",
                    }

            else:
                error = {"code": -32601, "message": f"Method not found: {method}"}

        except Exception as exc:
            error = {"code": -32000, "message": str(exc)}

        response = {"jsonrpc": "2.0", "id": rpc_id}
        if error is not None:
            response["error"] = error
        else:
            response["result"] = result

        self._send_json(response)

    def _send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json_error(self, code, message):
        self._send_json({"jsonrpc": "2.0", "id": 1, "error": {"code": code, "message": message}})

    def log_message(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8545), MockBlockchainRPCHandler)
    print("[BLOCKCHAIN NODE] Mock JSON-RPC server running on http://127.0.0.1:8545")
    server.serve_forever()
```
