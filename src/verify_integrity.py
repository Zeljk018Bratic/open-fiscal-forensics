#!/usr/bin/env python3
import hashlib
import json
import sys
from pathlib import Path

# Definiranje osnovnih mapa kako bi skripta radila bez obzira odakle se pokreće
BASE_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = BASE_DIR / "src"
CONTRACTS_DIR = BASE_DIR / "contracts"

# Popis svih ključnih modula s njihovim novim, točnim relativnim putanjama
CORE_FILES = [
    SRC_DIR / "app.py",
    SRC_DIR / "transparency_reconciler.py",
    SRC_DIR / "forensic_core.py",
    SRC_DIR / "auto_adapter.py",
    SRC_DIR / "database_registry.py",
    SRC_DIR / "cross_border_integrity.py",
    SRC_DIR / "p2p_network_mesh.py",
    SRC_DIR / "pdf_generator.py",
    CONTRACTS_DIR / "ConsensusLedger.sol"
]

# Nova točna lokacija kriptografskog manifesta unutar offf_output foldera
INTEGRITY_DB = BASE_DIR / "offf_output" / "signatures.js"

def calculate_sha256(file_path: Path) -> str:
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
    if not INTEGRITY_DB.exists():
        # Osiguraj da mapa offf_output postoji
        INTEGRITY_DB.parent.mkdir(parents=True, exist_ok=True)
        
        current_manifest = {file_path.name: calculate_sha256(file_path) for file_path in CORE_FILES if calculate_sha256(file_path) != "MISSING"}
        with open(INTEGRITY_DB, "w", encoding="utf-8") as f:
            json.dump(current_manifest, f, indent=2, sort_keys=True)
        print(f"[SUCCESS] Kreiran novi integritetni manifest: {INTEGRITY_DB.name}")
        return True

    with open(INTEGRITY_DB, "r", encoding="utf-8") as f:
        stored_manifest = json.load(f)

    failures = 0
    for file_path in CORE_FILES:
        file_name = file_path.name
        current_hash = calculate_sha256(file_path)
        stored_hash = stored_manifest.get(file_name)

        if current_hash == "MISSING":
            print(f"🚨 [WARNING] Datoteka {file_name} nedostaje na lokaciji: {file_path}")
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
