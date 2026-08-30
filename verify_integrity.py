import hashlib
import os

class CodeIntegrityChecker:
    def __init__(self):
        # Spisak ključnih datoteka koje štitimo
        self.tracked_files = ["forensic_core.py", "csv_budget_visualizer.py"]
        # Fajl u kojem čuvamo bezbedne otiske
        self.signature_file = "signatures.db"

    def calculate_sha256(self, filepath):
        """Računa nepromenljivi kriptografski otisak datoteke."""
        sha256_hash = hashlib.sha256()
        with open(filepath, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def lock_current_version(self):
        """Snima trenutno stanje i zaključava otiske ispravnog koda."""
        print("🔒 [Integrity] Generišem bezbednosne pečate za čistu verziju...")
        signatures = {}
        
        for file in self.tracked_files:
            if os.path.exists(file):
                file_hash = self.calculate_sha256(file)
                signatures[file] = file_hash
                print(f"   ✓ {file} -> {file_hash[:16]}...")
            else:
                print(f"   ⚠️ Upozorenje: Datoteka {file} nije pronađena za pečaćenje.")

        with open(self.signature_file, "w", encoding="utf-8") as f:
            json_data = {
                "version": "1.0.0-STABLE",
                "timestamp": os.path.getmtime(self.tracked_files[0]) if os.path.exists(self.tracked_files[0]) else 0,
                "hashes": signatures
            }
            import json
            json.dump(json_data, f, indent=4)
        print("💾 Bezbednosna baza 'signatures.db' uspešno kreirana i zaključana.")

    def verify_system(self):
        """Proverava da li je neko tajno modifikovao fajlove."""
        print("🛡️ [Integrity] Pokrećem skeniranje i verifikaciju koda...")
        import json
        
        if not os.path.exists(self.signature_file):
            print("❌ Greška: Baza otisaka (signatures.db) ne postoji! Prvo pokrenite zaključavanje.")
            return False

        with open(self.signature_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
            saved_hashes = saved_data.get("hashes", {})

        corruption_detected = False

        for file in self.tracked_files:
            if not os.path.exists(file):
                print(f" 🚨 ALARM: Datoteka {file} NEDOSTAJE ili je obrisana!")
                corruption_detected = True
                continue

            current_hash = self.calculate_sha256(file)
            expected_hash = saved_hashes.get(file)

            if current_hash == expected_hash:
                print(f"   🟢 {file}: INTEGRITET POTVRĐEN (Kod je čist i originalan).")
            else:
                print(f"   🚨 ALARM: {file} JE MODIFIKOVAN ILI KORUMPIRAN!")
                print(f"      Očekivano: {expected_hash[:16]}...")
                print(f"      Trenutno:  {current_hash[:16]}...")
                corruption_detected = True

        if corruption_detected:
            print("\n❌ VERIFIKACIJA NEUSPESNA: Sistem je ugrožen ili izmenjen!")
            return False
        else:
            print("\n✅ VERIFIKACIJA USPESNA: Svi moduli su 100% bezbedni i originalni.")
            return True

if __name__ == "__main__":
    checker = CodeIntegrityChecker()
    
    # Ako signatures.db ne postoji, prvo je pravimo (zaključavamo sistem)
    if not os.path.exists("signatures.db"):
        checker.lock_current_version()
        print("-" * 56)
    
    # Pokrećemo bezbednosnu proveru
    checker.verify_system()
