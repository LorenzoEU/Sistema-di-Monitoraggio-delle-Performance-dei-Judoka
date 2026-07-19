import sqlite3
import pandas as pd
from datetime import datetime
import json
import requests
from dotenv import load_dotenv
import os

DB_NAME = "judo_metrics.db"

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def get_connection():
    """Ritorna una connessione al DB con WAL"""
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def get_atleti_list():
    """Ritorna un DataFrame con ID e Nome Completo degli atleti."""
    db_conn = get_connection()
    query = "SELECT id_atleta, nome, cognome, peso_kg FROM Atleti ORDER BY cognome, nome"
    df = pd.read_sql_query(query, db_conn)
    db_conn.close()
    df['nominativo'] = df['cognome'] + " " + df['nome']
    return df

def esiste_id_atleta(id_atleta):
    """Verifica se un PIN/ID è già stato assegnato nel database locale."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM Atleti WHERE id_atleta = ?", (str(id_atleta),))
    esiste = cursor.fetchone() is not None
    conn.close()
    return esiste

def inserisci_atleta(id_atleta, nome, cognome, data_nascita, altezza_cm, peso_kg):
    """Inserisce un nuovo atleta nel database assegnandogli un PIN manuale."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Atleti (id_atleta, nome, cognome, data_nascita, altezza_cm, peso_kg)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (id_atleta, nome, cognome, data_nascita, altezza_cm, peso_kg))
    conn.commit()
    conn.close()

def aggiorna_peso(id_atleta, nuovo_peso):
    """Aggiorna il peso corporeo dell'atleta nell'anagrafica."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE Atleti SET peso_kg = ? WHERE id_atleta = ?", (float(nuovo_peso), str(id_atleta)))
    conn.commit()
    conn.close()

def get_ultimo_storico_raw(id_atleta):
    """Estrae unicamente i dati SQL grezzi per lo storico."""
    db_conn = get_connection()
    q_salti = "SELECT sj_1, sj_2, cmj_1, cmj_2, timestamp FROM Registro_Salti WHERE id_atleta = ? ORDER BY timestamp DESC LIMIT 2"
    df_salti = pd.read_sql_query(q_salti, db_conn, params=(str(id_atleta),))
    
    q_completo = "SELECT * FROM Registro_Completo WHERE id_atleta = ? ORDER BY timestamp DESC LIMIT 2"
    df_comp = pd.read_sql_query(q_completo, db_conn, params=(str(id_atleta),))
    
    db_conn.close()
    return df_salti, df_comp

def inserisci_salti(id_atleta, sj1, sj2, cmj1, cmj2, peso_al_test):
    """Inserisce una nuova sessione di salti."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Registro_Salti (id_atleta, sj_1, sj_2, cmj_1, cmj_2, peso_al_test)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (id_atleta, sj1, sj2, cmj1, cmj2, peso_al_test))
    conn.commit()
    conn.close()

def inserisci_completo(id_atleta, data_dict):
    """Inserisce un nuovo test completo passandogli un dizionario strutturato."""
    conn = get_connection()
    cursor = conn.cursor()
    
    campi = [
        'id_atleta', 'vp_t1', 'vp_t2', 'vp_t3', 
        'hr_inizio_tabata', 'hr_fine_tabata', 'hr_tabata_r1', 'hr_tabata_r2', 'hr_tabata_r3',
        'sjtf_b15_1', 'sjtf_b30_1', 'sjtf_b30_2', 'sjtf_b15_2',
        'hr_inizio_sjtf', 'hr_meta_sjtf', 'hr_fine_sjtf', 'hr_1min_post_sjtf', "peso_al_test"
    ]
    
    valori = [id_atleta] + [data_dict[c] for c in campi[1:]]
    placeholders = ", ".join(["?"] * len(campi))
    query = f"INSERT INTO Registro_Completo ({', '.join(campi)}) VALUES ({placeholders})"
    cursor.execute(query, valori)
    conn.commit()
    conn.close()



def get_analytics_trend(id_atleta):
    conn = get_connection()
    df_salti = pd.read_sql_query("SELECT * FROM Registro_Salti WHERE id_atleta = ?", conn, params=(str(id_atleta),))
    df_comp = pd.read_sql_query("SELECT * FROM Registro_Completo WHERE id_atleta = ?", conn, params=(str(id_atleta),))
    conn.close()
    return df_salti, df_comp


def get_group_benchmark_raw():
    """Esegue solo le join SQL e restituisce il dataframe fuso grezzo."""
    conn = get_connection()
    q_s = """
    SELECT s.id_atleta, s.peso_al_test, s.sj_1, s.sj_2, s.cmj_1, s.cmj_2
    FROM Registro_Salti s
    JOIN (
        SELECT id_atleta, MAX(timestamp) AS max_ts FROM Registro_Salti GROUP BY id_atleta
    ) ultimo ON s.id_atleta = ultimo.id_atleta AND s.timestamp = ultimo.max_ts;
    """
    q_c = """
    SELECT rc.id_atleta, rc.vp_t1, rc.vp_t2, rc.vp_t3, rc.hr_inizio_tabata, rc.hr_fine_tabata, rc.hr_tabata_r1, rc.sjtf_b15_1, rc.sjtf_b30_1, rc.sjtf_b30_2, rc.sjtf_b15_2, rc.hr_inizio_sjtf, rc.hr_meta_sjtf, rc.hr_fine_sjtf, rc.hr_1min_post_sjtf, rc.peso_al_test
    FROM Registro_Completo rc
    JOIN (
        SELECT id_atleta, MAX(timestamp) AS max_ts FROM Registro_Completo GROUP BY id_atleta
    ) ultimo ON rc.id_atleta = ultimo.id_atleta AND rc.timestamp = ultimo.max_ts;
    """
    df_s = pd.read_sql_query(q_s, conn)
    df_c = pd.read_sql_query(q_c, conn)
    df_a = pd.read_sql_query("SELECT id_atleta, nome, cognome FROM Atleti", conn)
    conn.close()

    df = pd.merge(df_a, df_s, on='id_atleta', how='left')
    df = pd.merge(df, df_c, on='id_atleta', how='left', suffixes=('_salti', '_completo'))
    return df


def sync_from_supabase():
    """Scarica dal cloud, inietta in locale e svuota il cloud."""
    conn = get_connection()
    cursor = conn.cursor()
    elementi_sincronizzati = 0
    errori_log = []
    
    try:
        #Sincronizzazione SALTI
        res_salti = requests.get(f"{SUPABASE_URL}/rest/v1/buffer_salti?select=*", headers=HEADERS)
        if res_salti.status_code == 200:
            dati_salti = res_salti.json()
            id_salti_da_cancellare = []
            for row in dati_salti:
                da_cancellare = False
                try: 
                    clean_ts = row['timestamp'].replace('T', ' ').split('+')[0].split('.')[0]
                    
                    cursor.execute("""
                        INSERT INTO Registro_Salti (id_atleta, timestamp, sj_1, sj_2, cmj_1, cmj_2, peso_al_test)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (str(row['id_atleta']), clean_ts, row['sj_1'], row['sj_2'], row['cmj_1'], row['cmj_2'], float(row['peso_al_test'])))
                    
                    elementi_sincronizzati += 1
                    da_cancellare = True

                except sqlite3.IntegrityError:
                    #Il PIN non esiste. Salva nella tabella locale per i pin sbagliati
                    payload_str = json.dumps(row)
                    cursor.execute("INSERT INTO Dati_Pin_Sbagliato (tipo_test, payload_json) VALUES (?, ?)", ("salti", payload_str))
                    errori_log.append(f"[SALTI] PIN {row['id_atleta']} inesistente. Record scaricato in Tabella No Pin.")
                    da_cancellare = True

                except Exception as e:
                    errori_log.append(f"[SALTI] Errore riga {row['id']}: {str(e)}")
                    #NON cancella il dato per permettere il debug
                if da_cancellare:
                    id_salti_da_cancellare.append(row['id'])

            if id_salti_da_cancellare:
                chunk_size = 50
                for i in range(0, len(id_salti_da_cancellare), chunk_size):
                    chunk = id_salti_da_cancellare[i:i + chunk_size]
                    string_ids = ",".join(map(str, chunk))
                    del_res = requests.delete(f"{SUPABASE_URL}/rest/v1/buffer_completo?id=in.({string_ids})", headers=HEADERS)
                    
                    if del_res.status_code not in [200, 204]:
                        errori_log.append(f"[COMPLETO] Errore cancellazione batch: {del_res.text}")
                        conn.rollback()
                        return 0
            conn.commit()

        #Sincronizzazione COMPLETO
        res_comp = requests.get(f"{SUPABASE_URL}/rest/v1/buffer_completo?select=*", headers=HEADERS)
        if res_comp.status_code == 200:
            dati_comp = res_comp.json()
            id_comp_da_cancellare = []
            for row in dati_comp:
                da_cancellare = False
                try:
                    clean_ts = row['timestamp'].replace('T', ' ').split('+')[0].split('.')[0]
                    
                    cursor.execute("""
                        INSERT INTO Registro_Completo (
                            id_atleta, timestamp, vp_t1, vp_t2, vp_t3, 
                            hr_inizio_tabata, hr_fine_tabata, hr_tabata_r1, hr_tabata_r2, hr_tabata_r3,
                            sjtf_b15_1, sjtf_b30_1, sjtf_b30_2, sjtf_b15_2,
                            hr_inizio_sjtf, hr_meta_sjtf, hr_fine_sjtf, hr_1min_post_sjtf, peso_al_test
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(row['id_atleta']), clean_ts, row['vp_t1'], row['vp_t2'], row['vp_t3'],
                        row['hr_inizio_tabata'], row['hr_fine_tabata'], row['hr_tabata_r1'], row['hr_tabata_r2'], row['hr_tabata_r3'],
                        row['sjtf_b15_1'], row['sjtf_b30_1'], row['sjtf_b30_2'], row['sjtf_b15_2'],
                        row['hr_inizio_sjtf'], row['hr_meta_sjtf'], row['hr_fine_sjtf'], row['hr_1min_post_sjtf'], float(row['peso_al_test'])
                    ))
                    
                    elementi_sincronizzati += 1
                    da_cancellare = True

                except sqlite3.IntegrityError:
                    #Il PIN non esiste. Salva nella tabella locale per i pin sbagliati
                    payload_str = json.dumps(row)
                    cursor.execute("INSERT INTO Dati_Pin_Sbagliato (tipo_test, payload_json) VALUES (?, ?)", ("completo", payload_str))
                    errori_log.append(f"[COMPLETO] PIN {row['id_atleta']} inesistente. Record scaricato in Tabella No_Pin.")
                    da_cancellare = True
                except Exception as e:
                    errori_log.append(f"[COMPLETO] Errore riga {row['id']}: {str(e)}")
                    #NON cancella il dato per permettere il debug
                if da_cancellare:
                    id_comp_da_cancellare.append(row['id'])

            if id_comp_da_cancellare:
                chunk_size = 50
                for i in range(0, len(id_comp_da_cancellare), chunk_size):
                    chunk = id_comp_da_cancellare[i:i + chunk_size]
                    string_ids = ",".join(map(str, chunk))
                    del_res = requests.delete(f"{SUPABASE_URL}/rest/v1/buffer_completo?id=in.({string_ids})", headers=HEADERS)
                    
                    if del_res.status_code not in [200, 204]:
                        errori_log.append(f"[COMPLETO] Errore cancellazione batch: {del_res.text}")
                        conn.rollback()
                        return 0
            conn.commit()
        
    except Exception as e:
        errori_log.append(f"Eccezione Python: {str(e)}")
    finally:
        conn.close()
    if errori_log:
        print("\n".join(errori_log))
        
    return elementi_sincronizzati