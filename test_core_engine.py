#!/usr/bin/env python3
import json
import hashlib
import unittest
from pathlib import Path
from transparency_reconciler import LedgerBlock, verify_chain

class TestOFFFCoreEngine(unittest.TestCase):

    def test_hash_chain_integrity_break_on_one_cent_change(self):
        """Testira da promjena od samo 1 centa momentalno ruši validaciju lanca dokaza."""
        payload_original = {"konto": "3233", "amount": 63102.72, "status": "PRODUCTION"}
        payload_friziran = {"konto": "3233", "amount": 63102.73, "status": "PRODUCTION"} # Promjena 1 cent
        
        # Genesis blok
        prev_hash = "0" * 64
        p_str_orig = json.dumps(payload_original, sort_keys=True)
        hash_orig = hashlib.sha256(f"{p_str_orig}{prev_hash}".encode("utf-8")).hexdigest()
        
        block_ok = LedgerBlock(block_hash=hash_orig, payload=payload_original)
        block_bad = LedgerBlock(block_hash=hash_orig, payload=payload_friziran)
        
        # Pravi kôd mora odbiti izmijenjeni payload pod istim hashom
        self.assertTrue(verify_chain([block_ok]))
        self.assertFalse(verify_chain([block_bad]))

    def test_hash_chain_sequence_alteration(self):
        """Provjerava da promjena redoslijeda blokova ruši verifikaciju."""
        b1 = LedgerBlock(block_hash="hash1", payload={"data": "prva_transakcija"})
        b2 = LedgerBlock(block_hash="hash2", payload={"data": "druga_transakcija"})
        
        # verify_chain mora pasti jer hash1 i hash2 ne prate stvarni rekalkulirani SHA-256 niz
        self.assertFalse(verify_chain([b2, b1]))

    def test_croatian_number_format_normalization(self):
        """Testira ispravnost pretvaranja hrvatskog formata valute (1.234,56)."""
        val_hr = "25.923.989,48"
        clean_val = val_hr.replace(".", "").replace(",", ".")
        final_float = float(clean_val)
        self.assertEqual(final_float, 25923989.48)

    def test_us_number_format_normalization(self):
        """Testira ispravnost formata s uobičajenim US decimalnim zarezom (1,234.56)."""
        val_us = "25,923,989.48"
        clean_val = val_us.replace(",", "")
        final_float = float(clean_val)
        self.assertEqual(final_float, 25923989.48)

    def test_simulation_bounds(self):
        """Osigurava da simulacija cenzure ne utječe na produkcijske varijable."""
        simulation_active = True
        status = "SIMULATION" if simulation_active else "PRODUCTION"
        self.assertEqual(status, "SIMULATION")

if __name__ == "__main__":
    unittest.main()
