📄 1. README.md (novi, čisti)
markdown
# Open Fiscal Forensics Framework (OFFF)

Local-first, open-source platforma za determinističku reviziju javnog proračuna, automatsku detekciju anomalija i screening rizika temeljen na podacima.

Analizom strukturiranih državnih financijskih podataka protiv nepromjenjivih statističkih konstanti (Benfordov zakon i Shannonova entropija), framework izdvaja metapodatkovne razlike i algoritamske obrasce koji služe kao statistički indikatori potencijalnih nepravilnosti, poput ručnih prilagodbi u knjigama ili umjetnog zaokruživanja brojeva. Ovi matematički indikatori djeluju kao mehanizam za trijažu i označavanje visokorizičnih anomalija, služeći kao signal za ciljanu ljudsku ekspertizu i formalne forenzičke revizije, a ne kao konačni dokaz sistemske namještaljke.

## 📊 Osnovna analitička metodologija

Framework balansira analitičku automatizaciju kroz dvoslojni matematički screening pipeline:

1. **Logaritamsko odstupanje frekvencije:** Procjenjuje sukladnost prve znamenke putem Chi-Square ($X^2$) testa dobrobiti prilagodbe.
2. **Mjerenje gustoće informacija:** Izračunava numeričku slučajnost koristeći Shannon Entropy matrice za detekciju sintetičkog linearnog generiranja zapisa.

## 🔧 Tehnički nacrt: Pravilo #3 (Blockchain proračun)

Tehnička jezgra ovog repozitorija pruža alternativnu arhitekturu za državne financijske operacije. Prebacivanjem fiskalnog upravljanja na javni ledger kontroliran automatiziranim pametnim ugovorima, sustav u potpunosti uklanja administrativnu ljudsku pogrešku i korupciju.

### 🛡️ Model upravljanja pametnim ugovorima

```text
       [ Javni prihod ] -> ( Porezi, naknade, javni prihodi )
                                  │
                                  ▼
                     ┌─────────────────────────┐
                     │  SMART CONTRACT ENGINE  │
                     └─────────────────────────┘
                                  │
         ┌────────────────────────┴────────────────────────┐
         ▼                                                 ▼
[ Provjera revizije: Otvoreni natječaj? ]        [ Provjera tržišne cijene ]
         │                                                 │
         ├─► DA: Izvrši transfer                           ├─► PODUDARANJE: Sigurna transakcija
         │                                                 │
         └─► NE: BLOKIRAJ TRANSAKCIJU                      └─► NEPODUDARANJE: OZNAČI ANOMALIJU
📋 Ključne mehanike protokola:
Transparentnost javnog ledgera: Svaki put državnog prihoda, naplate poreza i administrativne naknade vezan je uz univerzalno provjerljive javne adrese.

Uvjetno isplaćivanje: Sredstva su programski zaključana. Ako transakcija nema preciznu specifikaciju ili ne prođe provjeru javnog natječaja, ugovor koji izvršava transfer baca grešku i prekida se.

Automatska detekcija anomalija: Ako cijena nabave značajno odstupa od provjerenih tržišnih cijena, transakcija se automatski označava i zaustavlja na lancu.

Eliminacija deficita: Vidljivost omjera potrošnje i prihoda u stvarnom vremenu zaustavlja nevidljive rupe u bilanci.

💻 Referentna implementacija: TransparencyBudget.sol
Ispod je konceptualna implementacija pametnog ugovora koja validira Pravilo #3:

solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract TransparencyBudget {
    address public auditor;
    
    struct Transaction {
        address recipient;
        uint256 amount;
        string specification;
        bool hasPublicTender;
        uint256 marketPriceLimit;
        bool isFlagged;
        bool executed;
    }
    
    mapping(uint256 => Transaction) public registry;
    uint256 public txCount;

    event TransactionProposed(uint256 txId, address recipient, uint256 amount);
    event TransactionExecuted(uint256 txId, address recipient, uint256 amount);
    event AnomalyFlagged(uint256 txId, string reason);

    modifier onlyAuditor() {
        require(msg.sender == auditor, "Unauthorized access.");
        _;
    }

    constructor() {
        auditor = msg.sender;
    }

    function proposeTransaction(
        address _recipient, 
        uint256 _amount, 
        string memory _specification, 
        bool _hasPublicTender,
        uint256 _marketPriceLimit
    ) external onlyAuditor {
        txCount++;
        
        bool flag = false;
        if (_amount > _marketPriceLimit) {
            flag = true;
            emit AnomalyFlagged(txCount, "Price exceeds verified open-market rates.");
        }

        registry[txCount] = Transaction({
            recipient: _recipient,
            amount: _amount,
            specification: _specification,
            hasPublicTender: _hasPublicTender,
            marketPriceLimit: _marketPriceLimit,
            isFlagged: flag,
            executed: false
        });

        emit TransactionProposed(txCount, _recipient, _amount);
    }

    function executeTransaction(uint256 _txId) external {
        Transaction storage txn = registry[_txId];
        
        require(!txn.executed, "Transaction already processed.");
        require(txn.hasPublicTender, "BLOCKED: No open public tender verified.");
        require(!txn.isFlagged, "BLOCKED: Unresolved pricing anomaly detected.");
        require(bytes(txn.specification).length > 0, "BLOCKED: Specification missing.");

        txn.executed = true;
        payable(txn.recipient).transfer(txn.amount);
        
        emit TransactionExecuted(_txId, txn.recipient, txn.amount);
    }

    receive() external payable {}
}
🔬 Forenzički lanac 361
Ovaj repozitorij održava dokumentacijske tragove koji prate povijesne veze unutar globalnih elitnih mreža:

Korporativne transformacije: Kronološko mapiranje od povijesnih entiteta (npr. Tutogen) do strukturnih spajanja (RTI, 2008).

Revizije pozadinskih kanala: Analiza korporativnih ljuski i financijskih mehanizama (npr. Maxim Group "361 backdoor" upozorenja).

Mrežne veze: Dokumentirane komunikacije koje povezuju mreže visokoprofilirane imovine (npr. Epstein mrežni vektori / Steven Victor interni tragovi).

Revizije nabave: Praćenje institucionalnog ratnog profiterstva kroz Europski registar transparentnosti i subvencije za vojne rashode.

🔗 Indeks datoteka repozitorija i živa dokumentacija
Istražite komponente ovog frameworka izravno:

📜 index.html (Live Page) – Glavno višejezično arhitektonsko i sučeljno čvorište.

⚡ index-manifest.html (Live Page) – Freedom Manifest: 4 univerzalna pravila i Merit-Order analiza (€1.485T revizija).

🧪 sound_of_freedom_awareness.html (Live Page) – Globalni portal za praćenje nestale djece i međunarodnu svijest.

⛓️ 361-lanac.html (Live Page) – Detaljni forenzički lanac dokaza (Tutogen, RTI, Maxim Group, Epstein mrežni podaci).

🗺️ blockchain-361-vodic.html (Live Page) – Strukturni tehnički vodič za decentraliziranu proračunsku arhitekturu.

🛡️ Anonimni protokol za zviždače (Anti-Censorship Node)
Za zaštitu istražitelja i insajdera koji prijavljuju nedozvoljene mreže, sistemsku korupciju ili manipulaciju tržištem energije, framework uključuje potpuno funkcionalan, zero-knowledge klijentski enkripcijski i decentralizirani dispečerski engine integriran izravno u 361-lanac.html.

text
 [ Zviždač / Građanin ] 
            │
            ▼
┌───────────────────────────────────────┐
│ Browser lokalno šifrira datoteku      │ -> Koristeći #BajteBrothers javni PGP ključ
└───────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────┐
│ Upload šifriranog payloada na IPFS    │ -> Decentralizirano, otporno na cenzuru
└───────────────────────────────────────┘
            │
            ▼
 [ Generiranje IPFS Hasha (CID) ]       -> Nepromjenjivi hash usidren u Blockchain ledger proračuna
⚙️ Produkcijska infrastruktura
Zero-Knowledge arhitektura: Datoteke se sigurno šifriraju putem OpenPGP unutar informatičkog browser sandbox okruženja koristeći OpenPGP.js (v5.11.1). Nikakvi nešifrirani podaci ili cleartext infrastruktura nikada nisu izloženi mrežnoj jezgri.

Live Web3 routing: Potpuno integriran s decentraliziranim Crust Network IPFS API (https://crustwebsites.net) za permissionless, nepromjenjive i cenzuri otporne uploadove, čineći strukturne uklanjanja ili birokratsko potiskivanje nemogućim.

Globalni pristup i validacija: Emitirani payloadi generiraju nepromjenjivi Content Identifier (CID). Ova trajna kriptografska vremenska oznaka može se registrirati unutar našeg Solidity proračunskog ledger ekosustava i trenutno dohvatiti kroz bilo koji javni IPFS čvor diljem svijeta (npr. ipfs.io ili gateway.ipfs.io).

📦 Format mrežnih podataka
Kada se dokument pošalje, engine automatizira sljedeću sigurnu arhitekturu payloada:

text
[ Sirovi dokument ] ──► ( Lokalni browser sandbox ) ──► [ OpenPGP šifrirani blob ]
                                                           │
                                                           ▼
[ Javna IPFS mreža ] ◄── ( Live HTTPS POST ) ◄── [ Multi-part form data (.pgp) ]
           │
           ▼
[ Generiran trajni IPFS CID hash ]
👥 Kako sudjelovati
Potičemo neovisne developere, financijske revizore i zagovornike slobode da pregledaju naše decentralizirane nacrte:

Revizija podataka: Pregledajte naše izvorne dokumentacijske tragove u index datotekama.

Deploy & Test: Pregledajte pravila implementacije TransparencyBudget.

Širenje svijesti: Uključite se u službene rasprave zajednice putem našeg YouTube Community Post.

Pridružite se pokretu. Nema više skrivenih rupa.

🔬 Open-Source Forenzička analitička jezgra
Ovaj repozitorij sada uključuje funkcionalnu Python jezgru za integritet podataka i decentralizirani Solidity ledger za programsku evaluaciju skupova podataka.

📊 Statistički screening anomalija (forensic_core.py)
Za identifikaciju strukturnih odstupanja podataka i matematičkih devijacija, Python jezgra koristi dvoslojni statistički screening proces:

Benfordov zakon (Anomalije prve znamenke): Izvodi Chi-Square test dobrobiti prilagodbe na distribuciji vodećih znamenki u financijskim podacima. Značajna odstupanja od logaritamske osnovne linije služe kao statistički indikatori anomalnih distribucija, a ne kao konačni dokaz krivotvorenja ledgera.

Shannonova entropija (Slučajnost znamenki): Mjeri gustoću informacija i uniformnost numeričkih znakova kako bi označila umjetno generirane obrasce ili neobičnu strukturnu uniformnost. Ove oznake služe kao mehanizam trijaže za usmjeravanje dubljeg ljudskog računovodstvenog pregleda.

⛓️ Multi-Signature glasovanje validacija (ConsensusLedger.sol)
Za eliminaciju Single Point of Failure (SPOF) koji se nalazi u centraliziranim administrativnim ulogama, model upravljanja koristi decentraliziranu validacijsku arhitekturu.

Financijski unosi i ID-ovi javne nabave mogu proći multi-sig verifikacijski proces kojim upravljaju mrežni peerovi prije sinkronizacije ledgera. Ove blockchain konsenzus provjere verificiraju usklađenost protokola i poravnanje metapodataka, osiguravajući konzistentnost stanja podataka dok ljudski revizori obavljaju suštinsku provjeru istine.

Pozivamo peer-reviewere, podatkovne novinare i OSINT developere da revidiraju, prošire i benchmarkiraju ove osnovne matematičke screening module na javnim proračunskim podacima.

🚀 Live interaktivni dashboard i validacija u stvarnom svijetu (MVP Launch)
Framework je evoluirao od lokalne command-line skripte do potpuno funkcionalnog, desktop-first web aplikacijskog sučelja izgrađenog s Streamlit (app.py). Spaja jaz između sirovih ledger baza podataka i javne čitljivosti.

🛡️ Privacy-First izvršavanje (privacy_banner.js)
Kako bi se osigurala apsolutna usklađenost s globalnim digitalnim pravima, sučelje implementira strogi Privacy-by-Design konsenzus banner. Svaki automatizirani speech-to-text live-audit radi 100% lokalno unutar korisnikovog browser sandbox okruženja. Nikakvi audio streamovi se ne snimaju, cachiraju ili prenose na vanjske server matrice.

📊 Empirijska studija slučaja: Grad Labin 2025 Ledger Audit
Analitički pipeline uspješno je benchmarkiran i validiran korištenjem autentičnih federalnih rashodovnih sredstava iz službenog open-data registra Grada Labina (Hrvatska) za 2025. godinu.

Automatizirana obrada (auto_adapter.py): Engine je dinamički skenirao stranu spreadsheet matricu, izolirao financijski stupac na indeksu 1 i preusmjerio vrijednosti transakcija izravno u core analizator bez ljudske intervencije.

Forenzički analitički izlaz (forensic_audit_report.pdf):

Benford's Law Chi² rezultat: 0.0134 (Kritični prag: 15.507) -> PROŠAO ✓

Shannon Entropy vrijednost: 3.2868 bita (Prirodni minimum: >= 3.0) -> PROŠAO ✓

Procjena rizika: NISKI RIZIK — Distribucije vodećih i unutarnjih znamenki prate logaritamske prirodne obrasce, što ukazuje na statističko poravnanje s Benfordovim zakonom i očekivanim metrikama gustoće informacija. Ovo služi kao ključni indikator integriteta screeninga koji označava konzistentnost formatiranja podataka, iako ostaje statistička evaluacija i ne zamjenjuje suštinske institucionalne revizije ili ljudsku provjeru istine.

⚙️ Kako deployati i testirati lokalno
Za pokretanje interaktivnog dashboard sandbox okruženja na vašoj radnoj stanici, klonirajte repozitorij, navigirajte do izvornog direktorija i deployajte aplikacijski sloj:

powershell
# 1. Instalirajte verificirane, safe-mode izvršne biblioteke
pip install streamlit matplotlib reportlab

# 2. Pokrenite interaktivni Citizen Platform Central Control
streamlit run app.py
🗺️ Evolucija projekta i strateški roadmap
Za istraživanje dugoročne decentralizirane vizije, permissionless peer mreža i nadolazećih里程碑 historizacije baze podataka, pregledajte naš službeni core arhitektonski nacrt:

🔗 Pročitajte cijeli tehnički roadmap (ROADMAP.md)

Status izdanja
v1.0.0-MVP — Initial Open-Source Civic Audit Core
S ponosom objavljujemo da je #BajteBrothers Citizen Budget Intelligence Platform uspješno završio svoj početni validacijski ciklus.

Projekt sada uključuje determinističku forenzičku jezgru temeljenu na Benfordovom zakonu i Shannonovoj entropiji, zajedno s automatskom detekcijom financijskih stupaca, Streamlit dashboardom i PDF izvještavanjem spremnim za objavu. Uklanjanjem vanjskih monolitnih ovisnosti, analitička arhitektura je otporna, transparentna i potpuno reproducibilna.

Uspješno izvršavanje bez grešaka nad kompletnim fiskalnim ledgerom Grada Labina (Hrvatska) za 2025. godinu pokazuje da transparentni civic audit workflowi ne zahtijevaju centralizirane čuvare. Zahtijevaju rigoroznu logiku, javnu sljedivost i matematički konzistentne dokaze.

Ovo izdanje uključuje puni MVP temelj:

forensic_core.py
auto_adapter.py
app.py
pdf_generator.py
.gitignore
LICENSE
ROADMAP.md
Projekt je sada formalno open source pod MIT licencom, s dokumentiranim roadmapom za budući rad na registru i peer-to-peer validaciji.

Ovime završava trenutni razvojni ciklus. Kod sada pripada javnosti.

Napomena o izdanju / tekst za objavu

Sound of Freedom — MVP Polish Pass
Ovo izdanje finalizira forenzički audit MVP za civic budget review i jača kredibilitet, reproducibilnost i javnu transparentnost platforme.

Što se promijenilo
finaliziran je jezik i poruke dashboarda za formalnu, audit-grade prezentaciju
standardiziran je javni vokabular na konzistentan, profesionalan engleski
sinkronizirani provenance metapodaci kroz UI, report flow i JSON manifest export
poboljšana struktura audit outputa s eksplicitnim praćenjem file hasha i determinističkim manifest metapodacima
zadržan local-first workflow uz očuvanje lagane i dependency-safe implementacije
rafiniran sloj objašnjenja rizika kako bi se razlikovali statistički indikatori od zahtjeva za ljudskim pregledom
osigurano da arhivirani export paket ostane sljediv i spreman za javni pregled
Uključeno u ovu verziju
CSV upload workflow
AutoAdapter-based detekcija amount-stupca
forenzičko bodovanje i indikatori integriteta
generiranje grafikona za vizualizaciju rizika
PDF forenzički certifikat export
strukturirani JSON audit manifest export
provenance metadata capture za izvor, jurisdikciju, godinu, uploadera i file hash
Status
Ovo je polished MVP checkpoint za public-budget transparency workflowse i pozicioniran je kao spremna foundation za kontinuirani civic audit i forenzički razvoj.

Finalna commit poruka
feat: finalize MVP polish pass for civic audit dashboard

standardize dashboard wording to formal audit-grade English
synchronize provenance metadata between UI and manifest export
display full SHA-256 hash for uploaded dataset traceability
refine risk explanations and integrity messaging
optimized local-first workflow with structured dataframe processing
finalize export metadata structure and public audit report polish

Kopaj duboko. 🤖🍏🍉🍒💪🏁🏆🎉🚀

text

---
