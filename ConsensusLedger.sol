solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ConsensusLedger {
    struct Transaction {
        address recipient;
        uint256 amount;
        string tenderId;
        uint256 approvalCount;
        bool executed;
        bool flagged;
    }

    // Registrierte, unabhängige Validierungs-Knoten (Peers)
    mapping(address => bool) public isValidator;
    uint256 public totalValidators;
    uint256 public requiredApprovalThreshold; // Benötigte Stimmen in Prozent (z.B. 60)

    mapping(uint256 => Transaction) public registry;
    // TransaktionsID => (Validator-Adresse => Hat gestimmt)
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    uint256 public txCount;

    event TransactionProposed(uint256 indexed txId, address indexed recipient, uint256 amount);
    event VoteCast(uint256 indexed txId, address indexed validator, bool approved);
    event TransactionExecuted(uint256 indexed txId, address indexed recipient, uint256 amount);
    event LedgerAnomalyFlagged(uint256 indexed txId, string reason);

    modifier onlyValidator() {
        require(isValidator[msg.sender], "UNAUTHORIZED_NODE");
        _;
    }

    constructor(address[] memory _initialValidators, uint256 _thresholdPercent) {
        require(_thresholdPercent <= 100, "INVALID_THRESHOLD");
        for (uint256 i = 0; i < _initialValidators.length; i++) {
            address val = _initialValidators[i];
            if (val != address(0) && !isValidator[val]) {
                isValidator[val] = true;
                totalValidators++;
            }
        }
        requiredApprovalThreshold = _thresholdPercent;
    }

    // Jeder Validator kann einen Budget-Posten zur Prüfung vorschlagen
    function proposeTransaction(address _recipient, uint256 _amount, string calldata _tenderId) external onlyValidator {
        txCount++;
        bool holdsNoTender = (bytes(_tenderId).length == 0);

        registry[txCount] = Transaction({
            recipient: _recipient,
            amount: _amount,
            tenderId: _tenderId,
            approvalCount: 0,
            executed: false,
            flagged: holdsNoTender
        });

        emit TransactionProposed(txCount, _recipient, _amount);

        if (holdsNoTender) {
            emit LedgerAnomalyFlagged(txCount, "MISSING_PUBLIC_TENDER_ID");
        }
    }

    // Dezentrales Voting: Peers stimmen über die Korrektheit der Daten ab
    function voteOnTransaction(uint256 _txId, bool _approve) external onlyValidator {
        Transaction storage txn = registry[_txId];
        require(!txn.executed, "ALREADY_EXECUTED");
        require(!hasVoted[_txId][msg.sender], "ALREADY_VOTED");

        hasVoted[_txId][msg.sender] = true;
        emit VoteCast(_txId, msg.sender, _approve);

        if (_approve && !txn.flagged) {
            txn.approvalCount++;
        }
    }

    // Ausführung erst nach Erreichen des mathematischen Konsenses
    function executeTransaction(uint256 _txId) external onlyValidator {
        Transaction storage txn = registry[_txId];
        require(!txn.executed, "ALREADY_EXECUTED");
        require(!txn.flagged, "BLOCKED_DUE_TO_ANOMALY");

        // Berechne, ob die prozentuale Hürde der Validatoren erreicht wurde
        uint256 currentApprovalPercent = (txn.approvalCount * 100) / totalValidators;
        require(currentApprovalPercent >= requiredApprovalThreshold, "CONSENSUS_NOT_REACHED");

        txn.executed = true;
        payable(txn.recipient).transfer(txn.amount);

        emit TransactionExecuted(_txId, txn.recipient, txn.amount);
    }
}
