#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

# Popis svih ključnih modula za strogi nadzor integriteta jezgre
CORE_FILES = [
    "app.py",
    "transparency_reconciler.py",
    "forensic_core.py",
    "auto_adapter.py",
    "database_registry.py",
    "cross_border_integrity.py",
    "p2p_network_mesh.py",
    "pdf_generator.py",
    "ConsensusLedger.sol"
]

INTEGRITY_DB = "core_integrity_manifest.json"

def calculate_sha256(file_path: str) -> str:
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        return "MISSING"

def run_integrity_audit():
    print("[INTEGRITY] Pokretanje revizije integriteta OFFF modula...")
    
    # Ako manifest ne postoji, generiraj ga (prvo pokretanje / ugradnja)
    manifest_path = Path(INTEGRITY_DB)
    if not manifest_path.exists():
        current_manifest = {f: calculate_sha256(f) for f in CORE_FILES if calculate_sha256(f) != "MISSING"}
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(current_manifest, f, indent=2, sort_keys=True)
        print(f"[SUCCESS] Kreiran novi integritetni manifest: {INTEGRITY_DB}")
        return True

    with open(manifest_path, "r", encoding="utf-8") as f:
        stored_manifest = json.load(f)

    failures = 0
    for file_name in CORE_FILES:
        current_hash = calculate_sha256(file_name)
        stored_hash = stored_manifest.get(file_name)

        if current_hash == "MISSING":
            print(f"🚨 [WARNING] Datoteka {file_name} nedostaje u lokalnom okruženju.")
            continue

        if not stored_hash:
            print(f"➕ [NEW FILE] Detektiran novi modul bez povijesnog otiska: {file_name}")
            continue

        if current_hash != stored_hash:
            print(f"❌ [CRITICAL PROBOJ] Integritet ugrožen: {file_name}")
            print(f"   -> Očekivan hash: {stored_hash}")
            print(f"   -> Trenutni hash: {current_hash}")
            failures += 1
        else:
            print(f"✓ [OK] {file_name} prošao verifikaciju.")

    if failures > 0:
        print(f"\n🚨 [ALARM] Detektirano je {failures} neovlaštenih izmjena u jezgru koda!")
        return False
    
    print("\n✓ [SUCCESS] Svi osnovni moduli su kriptografski čisti i autentični.")
    return True

if __name__ == "__main__":
    if not run_integrity_audit():
        sys.exit(1)
