import sqlite3
import os

DB_NAME = "judo_metrics.db"

def init_db():
    #Crea e Connette DB
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    #Abilitazione modalità Write-Ahead Logging -> Applica aggiunta/modifica a un Log persistente prima di cambiare DB principale.
    #Permette quindi atomicità e durabilità in framework ACID (alta resistenza a failure).
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    #Crea Tabella Atleti
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Atleti (
        id_atleta TEXT PRIMARY KEY,
        nome TEXT NOT NULL,
        cognome TEXT NOT NULL,
        data_nascita DATE NOT NULL,
        altezza_cm REAL NOT NULL,
        peso_kg REAL NOT NULL
    )"""
    )

    #Tabella Registro_Salti (Countermovement e Squat Jump)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Registro_Salti (
        id_salto INTEGER PRIMARY KEY AUTOINCREMENT,
        id_atleta TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        sj_1 REAL, 
        sj_2 REAL, 
        cmj_1 REAL, 
        cmj_2 REAL, 
        peso_al_test REAL,
        FOREIGN KEY (id_atleta) REFERENCES Atleti(id_atleta)
    )"""
    )

    #Tabella Registro_Completo (Proiezione_Rapita - vp x 3,  )
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Registro_Completo (
        id_test INTEGER PRIMARY KEY AUTOINCREMENT,
        id_atleta TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        vp_t1 INTEGER, 
        vp_t2 INTEGER,
        vp_t3 INTEGER,
        hr_inizio_tabata INTEGER,           
        hr_fine_tabata INTEGER,
        hr_tabata_r1 INTEGER, 
        hr_tabata_r2 INTEGER, 
        hr_tabata_r3 INTEGER,
        sjtf_b15_1 INTEGER,
        sjtf_b30_1 INTEGER,
        sjtf_b30_2 INTEGER,
        sjtf_b15_2 INTEGER,
        hr_inizio_sjtf INTEGER,
        hr_meta_sjtf INTEGER,
        hr_fine_sjtf INTEGER,
        hr_1min_post_sjtf INTEGER,
        peso_al_test REAL,
        FOREIGN KEY (id_atleta) REFERENCES Atleti(id_atleta)
    )"""
    )

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Dati_Pin_Sbagliato (
    id_osservazione INTEGER PRIMARY KEY AUTOINCREMENT,
    tipo_test TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    data_ricezione DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    
    conn.commit()
    conn.close()
    print("Finito")





if __name__ == "__main__":
    init_db()
