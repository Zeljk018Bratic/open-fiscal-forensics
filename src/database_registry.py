"""Persistent SQLite audit registry for the Open Fiscal Forensics Framework.

This module provides a lightweight relational database interface for storing
and retrieving forensic audit manifests. It uses SQLite for local-first storage
without external dependencies, maintaining compatibility with Windows Smart App
Control and other restricted environments.

The DatabaseRegistry class manages the complete audit lifecycle:
- register_audit(manifest): Persists a forensic audit record to SQLite
- fetch_all_audits(): Retrieves all historical audit records
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseRegistry:
    """Lightweight SQLite registry for forensic audit manifests."""

    def __init__(self, db_path: str | Path = "audit_registry.db") -> None:
        """Initialize the database connection and schema.

        Parameters
        ----------
        db_path : str | Path, optional
            Path to the SQLite database file. Defaults to 'audit_registry.db'
            in the current working directory.
        """
        self.db_path = Path(db_path)
        self._initialize_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Return a fresh SQLite connection with row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _initialize_schema(self) -> None:
        """Create the audit registry table if it does not exist."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registered_at_utc TEXT NOT NULL,
                schema_version TEXT NOT NULL,
                dataset_name TEXT NOT NULL,
                generated_at_utc TEXT NOT NULL,
                file_sha256 TEXT NOT NULL,
                source_link TEXT,
                country TEXT,
                municipality TEXT,
                audit_year TEXT,
                uploaded_by TEXT,
                amount_column_index INTEGER,
                amount_column_explanation TEXT,
                risk_level TEXT NOT NULL,
                risk_label TEXT NOT NULL,
                chi_square REAL NOT NULL,
                shannon_entropy REAL NOT NULL,
                observation_count INTEGER NOT NULL,
                benford_passed BOOLEAN NOT NULL,
                shannon_passed BOOLEAN NOT NULL,
                manifest_json TEXT NOT NULL
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audits_registered_at
            ON audits(registered_at_utc DESC)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audits_risk_level
            ON audits(risk_level)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_audits_file_sha256
            ON audits(file_sha256)
            """
        )

        conn.commit()
        conn.close()

    def register_audit(self, manifest: Dict[str, Any]) -> int:
        """Persist a forensic audit manifest to the database.

        Parameters
        ----------
        manifest : dict
            The audit manifest dictionary returned by _build_manifest().
            Expected to contain: schema_version, dataset_name, generated_at_utc,
            file_sha256, provenance, amount_column, risk, metrics, and tests.

        Returns
        -------
        int
            The rowid of the inserted audit record.

        Raises
        ------
        ValueError
            If the manifest is missing required keys.
        """
        # Validate required keys
        required_keys = ["schema_version", "dataset_name", "generated_at_utc", "file_sha256", "risk", "metrics", "tests"]
        for key in required_keys:
            if key not in manifest:
                raise ValueError(f"Manifest missing required key: {key}")

        # Extract fields
        provenance = manifest.get("provenance", {})
        amount_column = manifest.get("amount_column", {})
        risk = manifest.get("risk", {})
        metrics = manifest.get("metrics", {})
        tests = manifest.get("tests", {})

        registered_at_utc = datetime.now(timezone.utc).isoformat()

        # Extract test results
        benford_test = tests.get("benford", {})
        shannon_test = tests.get("shannon", {})

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO audits (
                registered_at_utc, schema_version, dataset_name, generated_at_utc,
                file_sha256, source_link, country, municipality, audit_year, uploaded_by,
                amount_column_index, amount_column_explanation, risk_level, risk_label,
                chi_square, shannon_entropy, observation_count, benford_passed, shannon_passed,
                manifest_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                registered_at_utc,
                manifest.get("schema_version", ""),
                manifest.get("dataset_name", ""),
                manifest.get("generated_at_utc", ""),
                manifest.get("file_sha256", ""),
                provenance.get("source_link", ""),
                provenance.get("country", ""),
                provenance.get("municipality", ""),
                provenance.get("year", ""),
                provenance.get("uploaded_by", ""),
                amount_column.get("index", None),
                amount_column.get("explanation", ""),
                risk.get("level", "UNKNOWN"),
                risk.get("label", ""),
                metrics.get("chi_square", 0.0),
                metrics.get("shannon_entropy", 0.0),
                metrics.get("observation_count", 0),
                benford_test.get("passed", False),
                shannon_test.get("passed", False),
                json.dumps(manifest, ensure_ascii=False, indent=2),
            ),
        )

        conn.commit()
        rowid = cursor.lastrowid
        conn.close()

        return rowid

    def fetch_all_audits(self, limit: int | None = None, offset: int = 0) -> List[Dict[str, Any]]:
        """Retrieve all audit records from the database.

        Parameters
        ----------
        limit : int, optional
            Maximum number of records to return. If None, returns all.
        offset : int, optional
            Number of records to skip from the beginning (default: 0).

        Returns
        -------
        list of dict
            List of audit records in reverse chronological order (newest first).
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM audits ORDER BY registered_at_utc DESC"
        params: tuple[Any, ...] = ()

        if offset > 0:
            query += " OFFSET ?"
            params = (offset,)

        if limit is not None:
            query += " LIMIT ?"
            params = params + (limit,) if params else (limit,)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        # Convert Row objects to dictionaries with parsed manifest
        result = []
        for row in rows:
            record = dict(row)
            # Parse manifest_json back to dict if needed for downstream processing
            if "manifest_json" in record and isinstance(record["manifest_json"], str):
                try:
                    record["manifest"] = json.loads(record["manifest_json"])
                except json.JSONDecodeError:
                    record["manifest"] = {}
            result.append(record)

        return result

    def fetch_audit_by_id(self, audit_id: int) -> Dict[str, Any] | None:
        """Retrieve a single audit record by ID.

        Parameters
        ----------
        audit_id : int
            The rowid of the audit to retrieve.

        Returns
        -------
        dict or None
            The audit record, or None if not found.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM audits WHERE id = ?", (audit_id,))
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return None

        record = dict(row)
        if "manifest_json" in record and isinstance(record["manifest_json"], str):
            try:
                record["manifest"] = json.loads(record["manifest_json"])
            except json.JSONDecodeError:
                record["manifest"] = {}
        return record

    def fetch_audits_by_risk_level(self, risk_level: str) -> List[Dict[str, Any]]:
        """Retrieve audits filtered by risk level (HIGH, MEDIUM, LOW).

        Parameters
        ----------
        risk_level : str
            One of 'HIGH', 'MEDIUM', or 'LOW'.

        Returns
        -------
        list of dict
            Matching audit records in reverse chronological order.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM audits WHERE risk_level = ? ORDER BY registered_at_utc DESC",
            (risk_level.upper(),),
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            record = dict(row)
            if "manifest_json" in record and isinstance(record["manifest_json"], str):
                try:
                    record["manifest"] = json.loads(record["manifest_json"])
                except json.JSONDecodeError:
                    record["manifest"] = {}
            result.append(record)

        return result

    def fetch_audits_by_country(self, country: str) -> List[Dict[str, Any]]:
        """Retrieve audits filtered by country/jurisdiction.

        Parameters
        ----------
        country : str
            Country or jurisdiction name to filter by.

        Returns
        -------
        list of dict
            Matching audit records in reverse chronological order.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM audits WHERE country = ? ORDER BY registered_at_utc DESC",
            (country,),
        )
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            record = dict(row)
            if "manifest_json" in record and isinstance(record["manifest_json"], str):
                try:
                    record["manifest"] = json.loads(record["manifest_json"])
                except json.JSONDecodeError:
                    record["manifest"] = {}
            result.append(record)

        return result

    def get_audit_count(self) -> int:
        """Return the total number of audits in the database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM audits")
        result = cursor.fetchone()
        conn.close()

        return result["count"] if result else 0

    def get_risk_summary(self) -> Dict[str, int]:
        """Return a summary of audits by risk level.

        Returns
        -------
        dict
            Dictionary with keys 'HIGH', 'MEDIUM', 'LOW' and counts as values.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT risk_level, COUNT(*) as count
            FROM audits
            GROUP BY risk_level
            """
        )
        rows = cursor.fetchall()
        conn.close()

        summary = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for row in rows:
            risk_level = row["risk_level"].upper()
            if risk_level in summary:
                summary[risk_level] = row["count"]

        return summary
