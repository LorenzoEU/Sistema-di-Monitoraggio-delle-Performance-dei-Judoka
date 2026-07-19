import streamlit as st
import db_engine as db
from datetime import date
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from plotly.subplots import make_subplots
import os
import platform
import requests
import json
import time
import pandas as pd
import analytics

#USING SUPABASE DB AS TEMPORARY BUFFER + STREAMLIT

st.set_page_config(page_title="Judo Metrics", layout="wide")

def main():
    st.title("Fitness Tracker Judo")

    df_atleti = db.get_atleti_list()
    with st.sidebar:
        menu = option_menu(
            menu_title="Menù",
            options=["Gestione Atleti", "Inserimento Dati", "Dashboard Analytics", "Sincronizzazione Dati"],
            icons = ["person-circle", "database-add", "activity", "cloud-upload"],
            default_index=0
            )

    if menu == "Gestione Atleti":
        render_gestione_atleti()
    
    elif menu == "Inserimento Dati":
        if df_atleti.empty:
            st.error("Errore di Dipendenza. Nessun atleta presente in database.")
        else:
            render_data_entry(df_atleti)
            
    elif menu == "Dashboard Analytics":
        if df_atleti.empty:
            st.error("Errore di Dipendenza: Nessun dato presente in database.")
        else: 
            render_dashboard(df_atleti)
    elif menu == "Sincronizzazione Dati":
        with st.spinner("Scaricamento e pulizia cloud"):
                    n_sync = db.sync_from_supabase()
                    st.info("Fine")

def render_gestione_atleti():
    st.header("Aggiunta atleta")
    col1, col2 = st.columns(2)
    nome = col1.text_input("Nome")
    cognome = col1.text_input("Cognome")
    data_nascita = col1.date_input("Data di Nascita", min_value=date(1950, 1, 1), max_value=date.today(), format="DD/MM/YYYY")
    pin = col2.text_input("PIN Atleta (4 cifre)")
    altezza = col2.number_input("Altezza (cm)", step=0.5, value=170.0)
    peso = col2.number_input("Peso (kg)", step=0.1, value=70.0)

    if st.button("Registra Atleta", type="primary", width="stretch"):
        if nome.strip() == "" or cognome.strip() == "":
            st.warning("Nome e Cognome sono campi obbligatori.")
        elif pin == "0000":
            st.error("Il PIN 0000 non può essere utilizzato.")
        elif db.esiste_id_atleta(pin):
            st.error(f"Il PIN {pin} è già associato a un atleta esistente. Scegli un codice diverso.")
        else:
            db.inserisci_atleta(pin, nome, cognome, data_nascita, altezza, peso)
            st.toast(f"Atleta registrato con successo. PIN assegnato: {pin}.", icon="✅", duration="short")
            st.rerun()


def render_data_entry(df_atleti):
    st.header("Inserimento Dati")
    
    #Selezione Atleta
    lista_id = df_atleti['id_atleta'].tolist()
    id_selezionato = st.selectbox(
        "Seleziona Atleta", 
        options=lista_id, 
        format_func=lambda x: df_atleti[df_atleti['id_atleta'] == x]['nominativo'].values[0]
    )
    peso_attuale = float(df_atleti[df_atleti['id_atleta'] == id_selezionato]['peso_kg'].values[0])
    with st.expander("Aggiorna Peso Corporeo in Anagrafica", expanded=False):
        c_peso1, c_peso2 = st.columns([2, 1])
        peso_odierno = c_peso1.number_input("Nuovo Peso", value=peso_attuale, step=0.1)
        if peso_odierno != peso_attuale:
            if c_peso2.button("Salva Nuovo Peso", width="stretch"):
                db.aggiorna_peso(id_selezionato, peso_odierno)
                st.success("Anagrafica aggiornata con successo!")
                st.rerun()

    #Box Informativo (Storico)
    df_salti, df_comp = db.get_ultimo_storico_raw(id_selezionato)
    storico = analytics.elabora_storico(df_salti, df_comp)
    
    with st.expander("Storico Atleta + Rapporto Attuale-Precedente", expanded=True):
        if storico['salti'] or storico['completo']:
            m1, m2, m3, m4 = st.columns(4)
            if storico['salti']:
                s = storico['salti']
                m1.metric(label=f"Efficienza SSC ({s['date'][:10]})", 
                          value=s['Indice_Efficienza_SSC'], 
                          delta=s['delta_ssc'], 
                          delta_color="normal")
            if storico['completo']:
                c = storico['completo']
                m2.metric(label="Velocità Media Proiezione", 
                          value=f"{c['velocita_proiezione']}ms", 
                          delta=f"{c['delta_vp']}%" if c['delta_vp'] is not None else None, 
                          delta_color="normal")
                m3.metric(label="Recupero HR Tabata", 
                          value=f"{c['hr_recupero_tabata_perc']}%", 
                          delta=f"{c['delta_rec']}%" if c['delta_rec'] is not None else None, 
                          delta_color="normal")
                m4.metric(label="SJTF Index", 
                            value=c['sjtf'], 
                            delta=c['delta_sjtf'], 
                            delta_color="inverse")

    st.divider()

    tipo_test = st.radio(
        "Seleziona Sessione da Registrare:", 
        ["Registra Salti (SNC)", "Registra Test Completo"], 
        horizontal=True)
    
    #Modulo Inserimento Dati
    if tipo_test == "Registra Salti (SNC)":
        with st.form("form_salti", clear_on_submit=True):
            peso_al_test = st.number_input("Peso dell'atleta per questo test (kg)", value=peso_attuale, step=0.1)
            st.subheader("Squat Jump (SJ)")
            col1, col2 = st.columns(2)
            sj1 = col1.number_input("SJ 1 (cm)", value=40.0, step=0.5, format="%.1f")
            sj2 = col2.number_input("SJ 2 (cm)", value=40.0, step=0.5, format="%.1f")
            
            st.subheader("Countermovement Jump (CMJ)")
            col1, col2 = st.columns(2)
            cmj1 = col1.number_input("CMJ 1 (cm)", value=40.0, step=0.5, format="%.1f")
            cmj2 = col2.number_input("CMJ 2 (cm)", value=40.0, step=0.5, format="%.1f")
            if st.form_submit_button("Salva Salti", width="stretch"):
                db.inserisci_salti(id_selezionato, sj1, sj2, cmj1, cmj2, peso_al_test)
                st.success("Dati Salvati Correttamente", icon="✅")
                
    if tipo_test == "Registra Test Completo":
        peso_al_test = st.number_input("Peso dell'atleta per questo test (kg)", value=peso_attuale, step=0.1)
        with st.form("form_completo", clear_on_submit=True):
            st.subheader("1. Proiezioni in Rapidità (Velocità - ms)")
            c1, c2, c3 = st.columns(3)
            vp_t1 = c1.number_input("T1", value=1000, step=10)
            vp_t2 = c2.number_input("T2", value=1000, step=10)
            vp_t3 = c3.number_input("T3", value=1000, step=10)
            
            st.subheader("2. Tabata (Capacità Lavorativa Generale & HR Recovery)")
            c4, c5 = st.columns(2)
            hr_inizio_tabata = c4.number_input("HR Inizio Tabata", value=150, step=1)
            hr_fine_tabata = c5.number_input("HR Fine Tabata", value=150, step=1)
            
            c6, c7, c8 = st.columns(3)
            hr_tabata_r1 = c6.number_input("HR R1 (1m)", value=150, step=1)
            hr_tabata_r2 = c7.number_input("HR R2 (2m)", value=150, step=1)
            hr_tabata_r3 = c8.number_input("HR R3 (3m)", value=150, step=1)
            
            st.subheader("3. SJTF (Proiezioni & HR)")
            c9, c10, c11, c12 = st.columns(4)
            sjtf_b15_1 = c9.number_input("Proiezioni Blocco 1", value=5, step=1)
            sjtf_b30_1 = c10.number_input("Proiezioni Blocco 2 (Metà)", value=10, step=1)
            sjtf_b30_2 = c11.number_input("Proiezioni Blocco 3", value=10, step=1)
            sjtf_b15_2 = c12.number_input("Proiezioni Blocco 4", value=5, step=1)
            
            c13, c14, c15, c16 = st.columns(4)
            hr_inizio_sjtf = c13.number_input("HR Inizio SJTF", value=100, step=1)
            hr_meta_sjtf = c14.number_input("HR Metà SJTF", value=160, step=1)
            hr_fine_sjtf = c15.number_input("HR Fine SJTF", value=180, step=1)
            hr_1min_post_sjtf = c16.number_input("HR 1m", value=150, step=1)
            submit_btn = st.form_submit_button("Salva Test Completo", width="stretch")
            if submit_btn:
                data_dict = {
                    'vp_t1': vp_t1, 'vp_t2': vp_t2, 'vp_t3': vp_t3,
                    'hr_inizio_tabata': hr_inizio_tabata, 'hr_fine_tabata': hr_fine_tabata,
                    'hr_tabata_r1': hr_tabata_r1, 'hr_tabata_r2': hr_tabata_r2, 'hr_tabata_r3': hr_tabata_r3,
                    'sjtf_b15_1': sjtf_b15_1, 'sjtf_b30_1': sjtf_b30_1, 'sjtf_b30_2': sjtf_b30_2, 'sjtf_b15_2': sjtf_b15_2,
                    'hr_inizio_sjtf': hr_inizio_sjtf, 'hr_meta_sjtf': hr_meta_sjtf, 'hr_fine_sjtf': hr_fine_sjtf, 'hr_1min_post_sjtf': hr_1min_post_sjtf, 'peso_al_test': peso_al_test
                }
                db.inserisci_completo(id_selezionato, data_dict)
                st.success("Dati Salvati Correttamente", icon="✅")




def render_dashboard(df_atleti):
    st.header("Dashboard Analytics")

    tab1, tab2 = st.tabs(["Analisi Individuale Storica", "Benchmark di Gruppo"])

    #Trend SSC
    with tab1:
        lista_id = df_atleti['id_atleta'].tolist()
        id_sel = st.selectbox(
            "Seleziona Atleta da analizzare", 
            options=lista_id, 
            format_func=lambda x: df_atleti[df_atleti['id_atleta'] == x]['nominativo'].values[0]
        )
        
        df_salti, df_comp = db.get_analytics_trend(id_sel)
        
        st.markdown("### Prontezza SNC (Anomalie CMJ)")
        
        if not df_salti.empty and len(df_salti) >= 4:
            df_salti['Data'] = df_salti['timestamp'].astype(str).str[:10]
            ultimo_z, ultimo_cmj, media_mobile = analytics.calcola_zscore_readiness(df_salti)

            col_z1, col_z2 = st.columns([1, 2])
            
            with col_z1:
                #Logica basata sui deviazioni standard
                if ultimo_z >= 1.0:
                    stato, colore, icona = "Picco di Forma", "normal", "🟢"
                elif -1.0 < ultimo_z < 1.0:
                    stato, colore, icona = "Norma (Baseline)", "off", "🟡"
                elif -1.5 <= ultimo_z <= -1.0:
                    stato, colore, icona = "Affaticamento", "inverse", "🟠"
                else:
                    stato, colore, icona = "Possibile Sovrallenamento", "inverse", "🔴"
                st.metric(
                    label=f"Stato: {icona} {stato}",
                    value=f"H ultimo: {ultimo_cmj:.1f} cm",
                    delta=f"Z-Score: {ultimo_z:.2f}",
                    delta_color=colore
                )
                st.caption(f"Media mobile: {media_mobile:.2f} cm")
                
            with col_z2:
                #Rappresentazione a Tachimetro
                fig_z = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = ultimo_z,
                    domain = {'x': [0, 1], 'y': [0, 1]},
                    gauge = {
                        'axis': {'range': [-3, 3], 'tickwidth': 1, 'tickcolor': "darkblue"},
                        'bar': {'color': "black"},
                        'steps': [
                            {'range': [-3, -1.5], 'color': "#ff4b4b"}, 
                            {'range': [-1.5, -1.0], 'color': "#ffa500"}, 
                            {'range': [-1.0, 1.0], 'color': "#f0f2f6"},
                            {'range': [1.0, 3], 'color': "#21c354"}
                        ],
                        'threshold': {
                            'line': {'color': "black", 'width': 4},
                            'thickness': 0.75,
                            'value': ultimo_z
                        }
                    }
                ))
                fig_z.update_layout(height=200, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_z, width="stretch")
        else:
            st.info("Dati insufficienti per il calcolo della Readiness. Effettuare almeno 4 rilevazioni.")
            
        st.divider()

        df_salti = df_salti.tail(5).copy()
        df_comp = df_comp.tail(5).copy()
        
        if not df_salti.empty and 'Data' not in df_salti.columns:
            df_salti['Data'] = df_salti['timestamp'].astype(str).str[:10]
        if not df_comp.empty:
            df_comp['Data'] = df_comp['timestamp'].astype(str).str[:10]
        
        st.markdown("## Efficienza Sistema Nervoso Centrale & Rapidità")
        r1_col1, r1_col2, r1_col3 = st.columns(3)
        
        #Trend SSC
        with r1_col1:
            st.subheader("Indice Efficienza SSC")
            if not df_salti.empty:
                df_salti['Max_SJ'] = df_salti[['sj_1', 'sj_2']].max(axis=1)
                df_salti['Max_CMJ'] = df_salti[['cmj_1', 'cmj_2']].max(axis=1)
                df_salti['Indice Efficienza SSC'] = (df_salti['Max_CMJ'] / df_salti['Max_SJ']).round(3)
                
                fig_eur = px.line(df_salti, x='Data', y='Indice Efficienza SSC', markers=True)
                fig_eur.add_hline(y=1.05, line_dash="dash", line_color="red")
                fig_eur.add_hline(y=1.15, line_dash="dash", line_color="red")
                fig_eur.add_hrect(y0=1.05, y1=1.15, fillcolor="green",opacity=0.15)
                fig_eur.add_hrect(y0=1.00, y1=1.05, fillcolor="red",opacity=0.15)
                fig_eur.add_hrect(y0=1.15, y1=1.20, fillcolor="red",opacity=0.15)
                fig_eur.update_xaxes(type='category')
                st.plotly_chart(fig_eur, width="stretch")
            else:
                st.info("Dati mancanti.")

        #Trend Altezze Salti
        with r1_col2:
            st.subheader("Analisi Salti: Altezze e Potenze Massime")
            if not df_salti.empty and 'peso_al_test' in df_salti.columns:
                #alcolo altezze massime per ogni singola sessione
                df_salti['Max_CMJ'] = df_salti[['cmj_1', 'cmj_2']].max(axis=1)
                df_salti['Max_SJ'] = df_salti[['sj_1', 'sj_2']].max(axis=1)
                
                #Calcolo Potenze di Picco (Formula Sayers)
                df_salti = analytics.calcola_efficienza_ssc(df_salti)
                df_salti[['Peak_Power_CMJ', 'W_kg_CMJ']] = df_salti.apply(lambda row: analytics.calcola_potenza_sayers(row['Max_CMJ'], row['peso_al_test']), axis=1, result_type='expand')
                df_salti[['Peak_Power_SJ', 'W_kg_SJ']] = df_salti.apply(lambda row: analytics.calcola_potenza_sayers(row['Max_SJ'], row['peso_al_test']), axis=1, result_type='expand')

                fig = make_subplots(specs=[[{"secondary_y": True}]])

                #ASSE SINISTRO (cm)
                fig.add_trace(go.Scatter(x=df_salti['Data'], 
                                        y=df_salti['Max_CMJ'], 
                                        name="Max CMJ (cm)",
                                        mode='lines+markers',
                                        line=dict(color='blue', width=2)),
                                        secondary_y=False)
                
                fig.add_trace(go.Scatter(x=df_salti['Data'], 
                                         y=df_salti['Max_SJ'], 
                                        name="Max SJ (cm)",
                                        mode='lines+markers',
                                        line=dict(color='cyan', width=2)),
                                        secondary_y=False)

                #ASSE DESTRO (W/Kg)
                fig.add_trace(go.Scatter(x=df_salti['Data'], 
                                        y=df_salti['W_kg_CMJ'],
                                        name="Potenza CMJ (W/kg)",
                                        mode='lines+markers',
                                        line=dict(color='red', width=2, dash='dot')),
                                        secondary_y=True)
                
                fig.add_trace(go.Scatter(x=df_salti['Data'], 
                                        y=df_salti['W_kg_SJ'], 
                                        name="Potenza SJ (W/kg)",
                                        mode='lines+markers',
                                        line=dict(color='orange', width=2, dash='dot')),
                                        secondary_y=True)

                fig.update_layout(
                    title_text="Evoluzione Performance Neuromuscolare (CMJ vs SJ)",
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom",y=1.02,xanchor="right",x=1),
                    margin=dict(l=10, r=10, t=60, b=10))

                fig.update_xaxes(type='category')
                fig.update_yaxes(title_text="Altezza Salto (cm)", color="blue", secondary_y=False)
                fig.update_yaxes(title_text="Potenza Relativa (W/kg)", color="red", secondary_y=True)

                st.plotly_chart(fig, width="stretch")
            else:
                st.info("Dati mancanti o anomalia peso.")


        #Trend Velocità Proiezioni
        with r1_col3:
            st.subheader("Velocità Media Proiezioni (ms)")
            if not df_comp.empty:
                df_comp['Velocità Media'] = df_comp[['vp_t1', 'vp_t2', 'vp_t3']].mean(axis=1).round(1)
                pb_vp = df_comp['Velocità Media'].min()
                fig_vp = px.line(df_comp, x='Data', y='Velocità Media', markers=True)
                fig_vp.add_hline(y=pb_vp, line_dash="dash", line_color="gold", annotation_text=f"Personal Best: {pb_vp}ms")
                fig_vp.update_xaxes(type='category')
                fig_vp.update_yaxes(autorange="reversed") #Tempi minori indicano maggiore velocità
                st.plotly_chart(fig_vp, width="stretch")
            else:
                st.info("Dati mancanti.")      

        st.divider()
        st.markdown("## Profilo Cardiovascolare e Resistenza Tecnica")
        r2_col1, r2_col2, r2_col3 = st.columns(3)
        #Trend Tabata (Recupero)
        with r2_col1:
            st.subheader("Curva di Recupero HR (Tabata)")
            if not df_comp.empty:
                ultimo_test = df_comp.iloc[-1]
                tempi = ['Inizio Test', 'Fine Test', '1 Minuto Recupero', '2 Minuti Recupero', '3 Minuti Recupero']
                battiti = [ultimo_test["hr_inizio_tabata"] , ultimo_test['hr_fine_tabata'], ultimo_test['hr_tabata_r1'], ultimo_test['hr_tabata_r2'], ultimo_test['hr_tabata_r3']]
                
                fig_curve = go.Figure()
                fig_curve.add_trace(go.Scatter(x=tempi, y=battiti, mode='lines+markers+text', text=battiti, textposition="top center", line=dict(color='purple', width=3)))
                fig_curve.update_layout(title=f"Profilo Battiti Test del {ultimo_test['Data']}")
                fig_curve.update_xaxes(type='category')
                st.plotly_chart(fig_curve, width="stretch")
            else:
                st.info("Dati mancanti.")
                    
        #Grafico SJTF
        with r2_col2:
            st.subheader("Trend SJTF")
            if not df_comp.empty:
                df_comp = analytics.calcola_metriche_sjtf(df_comp)
                pb_SJTF = df_comp['SJTF'].min()
                fig_sjtf = px.line(df_comp, x='Data', y='SJTF', markers=True)
                fig_sjtf.add_hline(y=pb_SJTF, line_dash="dash", line_color="gold", annotation_text=f"Personal Best: {pb_SJTF}")
                fig_sjtf.update_yaxes(autorange="reversed") 
                fig_sjtf.update_xaxes(type='category')
                st.plotly_chart(fig_sjtf, width="stretch")
            else:
                st.info("Dati mancanti.")

        with r2_col3:
            st.subheader("Drop Prestazioni Inizio-Fine")
            if not df_comp.empty and 'Drop_Off_Perc' in df_comp.columns:
                fig_drop = px.line(df_comp, x='Data', y='Drop_Off_Perc', markers=True)
                fig_drop.add_hrect(y0=-10, y1=25, fillcolor="green", opacity=0.15)
                fig_drop.add_hrect(y0=25, y1=50, fillcolor="red", opacity=0.15)
                fig_drop.update_xaxes(type='category')
                fig_drop.update_yaxes(title_text="Drop Off (%)")
                st.plotly_chart(fig_drop, width="stretch")
            else:
                st.info("Dati mancanti.")

    with tab2:
        st.subheader("Rapporto di Gruppo (Ultima rilevazione)")
        st.markdown("Tabella riassuntiva. Clicca sulle intestazioni delle colonne per ordinare gli atleti.")
    
        
        df_raw = db.get_group_benchmark_raw()
        df_bench = analytics.genera_tabella_benchmark(df_raw)
        if not df_bench.empty:
            st.dataframe(
                df_bench,
                hide_index=True,
                width="stretch",
                column_config={
                    "Nominativo": st.column_config.TextColumn("Atleta", pinned=True),
                    "Indice_Efficienza_SSC": st.column_config.NumberColumn("Efficienza SSC", format="%.3f"),
                    "W/Kg SquatJump": st.column_config.NumberColumn("W/Kg SquatJump", format="%.3f"),
                    "W/Kg CMJ": st.column_config.NumberColumn("W/Kg CMJ", format="%.3f"),
                    "Velocita_Media_vp": st.column_config.NumberColumn("Velocità Proiez. (ms)", format="%d"),
                    "hr_fine_tabata": st.column_config.NumberColumn("HR Fine Tabata (BPM)", format="%d"),
                    "Delta HR (Tabata)": st.column_config.NumberColumn("Supporto HR Tabata (BPM)", format="%d"),
                    "Recovery HR 1m (Tabata) %": st.column_config.NumberColumn("Recupero HR% 1m Tabata", format="%.1f %%"),
                    "SJTF": st.column_config.NumberColumn("Indice SJTF", format="%.2f"),
                    "sjtf_b15_1": st.column_config.NumberColumn("Slot 1 (15s)", format="%d"),
                    "sjtf_b30_1": st.column_config.NumberColumn("Slot 2 (30s)", format="%d"),
                    "sjtf_b30_2": st.column_config.NumberColumn("Slot 3 (30s)", format="%d"),
                    "sjtf_b15_2": st.column_config.NumberColumn("Slot 4 (15s)", format="%d"),
                }
            )
        else:
            st.info("Dati insufficienti per generare il benchmark.")
        st.download_button(
        label="Esporta Benchmark in CSV",
        data=df_bench.to_csv(index=False).encode('utf-8'),
        file_name=f"benchmark_dojo_{date.today()}.csv",
        mime="text/csv",
    )
        

        
st.sidebar.divider()
st.sidebar.markdown("### Gestione PC")
with st.sidebar.expander("Opzioni di Spegnimento", expanded=False):
    st.warning("Questa azione spegnerà fisicamente il PC-server")
    
    if st.button("Spegni PC Ora", width="stretch"):
        st.success("Comando inviato. Spegnimento in corso...")
        sistema = platform.system()
        if sistema == "Windows":
            os.system("shutdown /s /t 5")

        
if __name__ == "__main__":
    main()
