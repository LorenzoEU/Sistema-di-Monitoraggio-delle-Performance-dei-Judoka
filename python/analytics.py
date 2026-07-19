import pandas as pd

def calcola_zscore_readiness(df_salti):
    """Ritorna Z-Score, media mobile e ultimo salto"""
    df = df_salti.copy()
    df['Max_CMJ'] = df[['cmj_1', 'cmj_2']].max(axis=1)
    df['CMJ_Roll_Mean'] = df['Max_CMJ'].shift(1).rolling(window=10, min_periods=3).mean()
    df['CMJ_Roll_Std'] = df['Max_CMJ'].shift(1).rolling(window=10, min_periods=3).std()
    df['Z_Score'] = ((df['Max_CMJ'] - df['CMJ_Roll_Mean']) / df['CMJ_Roll_Std']).round(2)
    
    ultimo_z = df['Z_Score'].iloc[-1]
    ultimo_cmj = df['Max_CMJ'].iloc[-1]
    media_mobile = df['CMJ_Roll_Mean'].iloc[-1]
    
    return ultimo_z, ultimo_cmj, media_mobile

def calcola_efficienza_ssc(df_salti):
    df = df_salti.copy()
    df['Mean_SJ'] = df[['sj_1', 'sj_2']].mean(axis=1)
    df['Mean_CMJ'] = df[['cmj_1', 'cmj_2']].mean(axis=1)
    df['Efficienza_SSC'] = (df['Mean_CMJ'] / df['Mean_SJ']).round(3)
    return df

def calcola_potenza_sayers(altezza_cm, peso_kg):
    potenza_assoluta = 60.7 * altezza_cm + 45.3 * peso_kg - 2055
    potenza_relativa = round(potenza_assoluta / peso_kg, 1)
    return round(potenza_assoluta, 0), potenza_relativa

def calcola_metriche_sjtf(df_comp):
    df = df_comp.copy()
    somma_hr = df['hr_inizio_sjtf'] + df['hr_meta_sjtf'] + df['hr_fine_sjtf'] + df['hr_1min_post_sjtf']
    somma_proiezioni = df['sjtf_b15_1'] + df['sjtf_b30_1'] + df['sjtf_b30_2'] + df['sjtf_b15_2']
    df['SJTF'] = (somma_hr / somma_proiezioni).round(2)
    df['Drop_Off_Perc'] = (((df['sjtf_b15_1'] - df['sjtf_b15_2']) / df['sjtf_b15_1']) * 100).round(1)
    return df

def elabora_storico(df_salti, df_comp):
    res = {'salti': None, 'completo': None}
    
    if not df_salti.empty:
        r_0 = df_salti.iloc[0]
        sj_0 = max(r_0['sj_1'], r_0['sj_2'])
        cmj_0 = max(r_0['cmj_1'], r_0['cmj_2'])
        ssc_0 = cmj_0 / sj_0 if sj_0 > 0 else 0
        
        delta_ssc = None
        if len(df_salti) > 1:
            r_1 = df_salti.iloc[1]
            sj_1 = max(r_1['sj_1'], r_1['sj_2'])
            cmj_1 = max(r_1['cmj_1'], r_1['cmj_2'])
            ssc_1 = cmj_1 / sj_1 if sj_1 > 0 else 0
            delta_ssc = ssc_0 - ssc_1

        res['salti'] = {
            'Indice_Efficienza_SSC': round(ssc_0, 3),
            'delta_ssc': round(delta_ssc, 3) if delta_ssc is not None else None,
            'date': r_0['timestamp']
        }

    if not df_comp.empty:
        r_0 = df_comp.iloc[0]
        sjtf_0 = (r_0['hr_inizio_sjtf'] + r_0['hr_meta_sjtf'] + r_0['hr_fine_sjtf'] + r_0['hr_1min_post_sjtf']) / (r_0['sjtf_b15_1'] + r_0['sjtf_b30_1'] + r_0['sjtf_b30_2'] + r_0['sjtf_b15_2'])
        rec_perc_0 = ((r_0["hr_fine_tabata"] - r_0["hr_tabata_r1"]) / r_0["hr_fine_tabata"]) * 100 if r_0["hr_fine_tabata"] > 0 else 0
        vp_0 = (r_0['vp_t1'] + r_0['vp_t2'] + r_0['vp_t3']) / 3

        delta_vp = delta_sjtf = delta_rec = None
        
        if len(df_comp) > 1:
            r_1 = df_comp.iloc[1]
            sjtf_1 = (r_1['hr_inizio_sjtf'] + r_1['hr_meta_sjtf'] + r_1['hr_fine_sjtf'] + r_1['hr_1min_post_sjtf']) / (r_1['sjtf_b15_1'] + r_1['sjtf_b30_1'] + r_1['sjtf_b30_2'] + r_1['sjtf_b15_2'])
            rec_perc_1 = ((r_1["hr_fine_tabata"] - r_1["hr_tabata_r1"]) / r_1["hr_fine_tabata"]) * 100 if r_1["hr_fine_tabata"] > 0 else 0
            vp_1 = (r_1['vp_t1'] + r_1['vp_t2'] + r_1['vp_t3']) / 3

            delta_vp = vp_0 - vp_1
            delta_sjtf = sjtf_0 - sjtf_1
            delta_rec = rec_perc_0 - rec_perc_1
            
        res['completo'] = {
            'hr_recupero_tabata_perc': round(rec_perc_0, 1),
            'delta_rec': round(delta_rec, 1) if delta_rec is not None else None,
            'sjtf': round(sjtf_0, 2),
            'delta_sjtf': round(delta_sjtf, 2) if delta_sjtf is not None else None,
            'velocita_proiezione': round(vp_0, 2),
            'delta_vp': round(delta_vp, 2) if delta_vp is not None else None,
            'date': r_0['timestamp']
        }
    return res


def genera_tabella_benchmark(df):
    if df.empty:
        return pd.DataFrame()

    df['Nominativo'] = df['cognome'] + " " + df['nome']
    df['Max_SJ'] = df[['sj_1', 'sj_2']].max(axis=1)
    df['Max_CMJ'] = df[['cmj_1', 'cmj_2']].max(axis=1)
    df['Indice_Efficienza_SSC'] = (df['Max_CMJ'] / df['Max_SJ']).round(3)
    
    df['Delta HR (Tabata)'] = (df['hr_fine_tabata'] - df['hr_inizio_tabata'])
    df['Recovery HR 1m (Tabata) %'] = (((df['hr_fine_tabata'] - df['hr_tabata_r1']) / df['hr_fine_tabata']) * 100).round(1)
    
    somma_hr = df['hr_inizio_sjtf'] + df['hr_meta_sjtf'] + df['hr_fine_sjtf'] + df['hr_1min_post_sjtf']
    somma_proiezioni = df['sjtf_b15_1'] + df['sjtf_b30_1'] + df['sjtf_b30_2'] + df['sjtf_b15_2']
    df['SJTF'] = (somma_hr / somma_proiezioni).round(2)
    
    df['Velocita Media Proiezioni'] = df[['vp_t1', 'vp_t2', 'vp_t3']].mean(axis=1).round(1)

    peso_atleta_salti = df['peso_al_test_salti']
    df['Picco Watt SquatJump'] = (60.7 * df['Max_SJ'] + 45.3 * peso_atleta_salti - 2055).round(0)
    df['W/Kg SquatJump'] = (df['Picco Watt SquatJump'] / peso_atleta_salti).round(1)

    df['Picco Watt CMJ'] = (60.7 * df['Max_CMJ'] + 45.3 * peso_atleta_salti - 2055).round(0)
    df['W/Kg CMJ'] = (df['Picco Watt CMJ'] / peso_atleta_salti).round(1)

    return df[[
        'Nominativo', 'Indice_Efficienza_SSC', 'Velocita Media Proiezioni', 'hr_fine_tabata', 
        'Delta HR (Tabata)', 'Recovery HR 1m (Tabata) %', 'SJTF',
        'sjtf_b15_1', 'sjtf_b30_1', 'sjtf_b30_2', 'sjtf_b15_2',
        'Picco Watt SquatJump', 'Picco Watt CMJ',
        'W/Kg SquatJump', 'W/Kg CMJ'
    ]]
