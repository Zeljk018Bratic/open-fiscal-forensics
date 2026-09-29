// #BajteBrothers Transparency & Privacy Protocol
class PrivacyConsentManager {
    constructor() {
        this.hasConsent = false;
    }

    // Prikazuje profesionalni i jasni banner korisniku
    renderPrivacyBanner() {
        const banner = document.createElement('div');
        banner.id = 'bajtebrothers-privacy-banner';
        banner.style = `
            position: fixed; bottom: 20px; right: 20px; max-width: 400px;
            background-color: #111; border: 2px solid #ff0055; color: #00ff66;
            font-family: 'Courier New', monospace; padding: 20px; z-index: 9999;
            box-shadow: 0 0 20px rgba(255, 0, 85, 0.3); border-radius: 5px;
        `;

        banner.innerHTML = `
            <h3 style="color: #ff0055; margin-top: 0;">🛡️ PRIVACY & LIVE-AUDIT DATA PROTOCOL</h3>
            <p style="font-size: 12px; color: #fff;">
                Da biste aktivirali Live-Fact-Check za trenutnu emisiju, sistem zahteva pristup audio-strimingu (Web Audio API).
            </p>
            <ul style="font-size: 11px; color: #00ff66; padding-left: 20px;">
                <li>🔒 <strong>100% Lokalno:</strong> Zvuk se obrađuje isključivo unutar vašeg pretraživača.</li>
                <li>❌ <strong>Nema Snimanja:</strong> Nikakav audio podatak se ne čuva niti šalje na eksterne servere.</li>
                <li>👁️ <strong>Potpuna Kontrola:</strong> Pristup se gasi automatski čim se emisija završi ili zatvorite tab.</li>
            </ul>
            <div style="margin-top: 15px; display: flex; justify-content: space-between;">
                <button id="btn-decline" style="background: #333; color: #fff; border: none; padding: 5px 10px; cursor: pointer;">ODBIJ</button>
                <button id="btn-accept" style="background: #00ff66; color: #000; border: none; padding: 5px 15px; cursor: pointer; font-weight: bold;">PRIHVATI & POKRENI</button>
            </div>
        `;

        document.body.appendChild(banner);
        this.setupConsentListeners();
    }

    setupConsentListeners() {
        document.getElementById('btn-accept').addEventListener('click', () => {
            this.hasConsent = true;
            document.getElementById('bajtebrothers-privacy-banner').remove();
            console.log("🟢 [Privacy] Korisnik je eksplicitno odobrio lokalnu audio analizu.");
            
            // Tek nakon klika i pristanka, aktivira se funkcija za pokretanje radara
            if (typeof LiveRadar !== 'undefined') {
                LiveRadar.startTracking(); 
            }
        });

        document.getElementById('btn-decline').addEventListener('click', () => {
            this.hasConsent = false;
            document.getElementById('bajtebrothers-privacy-banner').remove();
            console.log("❌ [Privacy] Korisnik je odbio pristup. Live-Fact-Check je blokiran.");
        });
    }
}

// Inicijalizacija pri učitavanju stranice
window.addEventListener('DOMContentLoaded', () => {
    const Privacy = new PrivacyConsentManager();
    // Pokazuje se kada korisnik želi da se uključi u "kapiranje" emisije
    Privacy.renderPrivacyBanner();
});
