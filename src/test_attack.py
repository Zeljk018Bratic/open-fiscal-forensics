import math
from forensic_core import ForensicCore

def pokreni_simulaciju_napada():
    core = ForensicCore()
    
    # 1. SCENARIO: Potpuno prirodan budžet (Kontrolna grupa)
    # Generišemo brojeve koji prirodno prate Benfordov zakon
    prirodni_podaci = [10** (1 + 2 * (i / 500)) for i in range(500)]
    rezultat_normalno = core.analyze(prirodni_podaci, label="Prirodan Budzet (OK)")
    
    # 2. SCENARIO: Veštačko zaokruživanje / Sakupljanje crnog fonda
    # Napadač namerno kreira 300 ugovora koji počinju cifrom 5 (npr. fiktivne isplate od 520€, 550€)
    napumpani_podaci = prirodni_podaci.copy()
    for _ in range(150):
        napumpani_podaci.append(540.00)
    rezultat_napad_cifra = core.analyze(napumpani_podaci, label="Napad: Benford Fraud (Cifra 5)")
    
    # 3. SCENARIO: Ispiranje novca kroz identične šablone
    # Napadač kopira potpuno istu cifru stotinama puta (drastičan pad entropije)
    repetitivni_podaci = [450.00] * 400
    rezultat_napad_entropija = core.analyze(repetitivni_podaci, label="Napad: Repetitivni Sablon (Entropija)")

    # Stampanje rezultata kroz tvoj ugradjeni print_report
    core.print_report(rezultat_normalno)
    core.print_report(rezultat_napad_cifra)
    core.print_report(rezultat_napad_entropija)

if __name__ == "__main__":
    pokreni_simulaciju_napada()
