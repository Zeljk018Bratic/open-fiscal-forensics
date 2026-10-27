import pandas as pd
from datetime import timedelta

def detect_salami_slicing(df, threshold_eur=26540.0, window_days=30):
    """
    Detektira 'Salami Slicing' (cijepanje nabave) kako bi se izbjegli natječaji.
    
    Parametri:
    - df: Pandas DataFrame s kolonama 'OIB', 'Datum' (YYYY-MM-DD), 'Iznos' (float)
    - threshold_eur: Zakonski limit za javnu nabavu (npr. 26540 eura)
    - window_days: Vremenski prozor u danima (npr. 30 dana)
    """
    
    # Osiguravamo da su datumi u pravom formatu
    df['Datum'] = pd.to_datetime(df['Datum'])
    df = df.sort_values(by=['OIB', 'Datum'])
    
    alerts = []
    
    # Grupiramo po dobavljaču (OIB)
    for oib, group in df.groupby('OIB'):
        group = group.reset_index(drop=True)
        
        for i in range(len(group)):
            # Uzimamo trenutni ugovor
            current_tx = group.iloc[i]
            current_date = current_tx['Datum']
            current_amount = current_tx['Iznos']
            
            # Ako je pojedinačni ugovor već prešao limit, to nije salami slicing, 
            # to je regularni natječaj (ili prekršaj ako nije bilo natječaja)
            if current_amount >= threshold_eur:
                continue
                
            # Gledamo unaprijed kroz prozor od X dana
            window_end = current_date + timedelta(days=window_days)
            window_txs = group[(group['Datum'] >= current_date) & (group['Datum'] <= window_end)]
            
            if len(window_txs) > 1:
                total_sum = window_txs['Iznos'].sum()
                
                # Ako je zbroj unutar prozora prešao limit, a pojedinačno nisu -> SALAMI SLICING!
                if total_sum >= threshold_eur:
                    alerts.append({
                        'OIB': oib,
                        'Dobavljac': window_txs['Dobavljac'].iloc[0] if 'Dobavljac' in window_txs.columns else 'Nepoznato',
                        'Broj_ugovora': len(window_txs),
                        'Pocetni_datum': current_date.strftime('%Y-%m-%d'),
                        'Zavrsni_datum': window_end.strftime('%Y-%m-%d'),
                        'Zbroj_iznosa': total_sum,
                        'Prekoracenje_limita_%': ((total_sum / threshold_eur) - 1) * 100
                    })
                    
    # Čistimo duplikate (isti OIB i isti period)
    if alerts:
        alerts_df = pd.DataFrame(alerts).drop_duplicates(subset=['OIB', 'Pocetni_datum', 'Zavrsni_datum'])
        return alerts_df.sort_values(by='Prekoracenje_limita_%', ascending=False)
    else:
        return pd.DataFrame()

# --- PRIMJER KORIŠTENJA ---
if __name__ == "__main__":
    # Testni podaci (simulacija)
    test_data = {
        'OIB': ['12345678901', '12345678901', '12345678901', '98765432109'],
        'Dobavljac': ['Firma A', 'Firma A', 'Firma A', 'Firma B'],
        'Datum': ['2025-01-10', '2025-01-25', '2025-02-15', '2025-03-01'],
        'Iznos': [25000.0, 24000.0, 15000.0, 50000.0]
    }
    
    df = pd.DataFrame(test_data)
    print("Testiramo detekciju...")
    izvjestaj = detect_salami_slicing(df, threshold_eur=26540.0, window_days=30)
    
    if not izvjestaj.empty:
        print("\n🚨 PRONAĐEN SALAMI SLICING! 🚨")
        print(izvjestaj.to_string(index=False))
    else:
        print("Nema anomalija.")
