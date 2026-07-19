# Sistema-di-Monitoraggio-delle-Performance-dei-Judoka
Una Architettura Ibrida basata su un Buffer ibrido Edge-Cloud per l’Analisi Neuromuscolare e Cardiovascolare degli Atleti di una palestra di Piccole-Medie dimensioni.


## Contesto e problema Principale
Il monitoraggio sistematico delle prestazioni atletiche richiede la raccolta periodica di KPI biometrici ad alta frequenza in ambienti operativi a bassa digitalizzazione come palestre, tatami e campi di allenamento, dove l'infrastruttura IT è tipicamente assente o ridotta al minimo. Nel contesto specifico di questo progetto, tale esigenza si scontra con tre vincoli strutturali simultanei: la necessità di un'interfaccia di data entry, utilizzabile direttamente sul campo da tecnici in maniera pratica e intuitiva tramite smartphone; la necessità di conformarsi al GDPR sulla gestione di dati biometrici e sanitari, preferendo l’esclusione di soluzioni cloud commerciali standard e un’infrastruttura intermittente per evitare di tenere un PC-server costantemente acceso solo in attesa di un inserimento dati a fine sessione.
Il problema di dominio richiede di consentire l'inserimento rapido di dati strutturati da smartphone a bordo tatami, azzerando i costi infrastrutturali, evitando l'installazione di applicazioni terze e garantendo nativamente la privacy.

## La soluzione
Il sistema progettato risponde a questi vincoli con un'architettura ibrida a tre livelli, basata sul disaccoppiamento tra il momento in cui il dato viene digitato e il momento in cui viene effettivamente elaborato e salvato nel database master.
Il primo livello è un Edge Client HTML/JS autonomo e stateless, salvato nella memoria del telefono del tecnico. Non contiene elenchi di atleti e non sa a chi appartengano i dati inseriti.
Un'istanza Supabase funge da buffer temporaneo. Sfruttando le Row Level Security (RLS) di PostgreSQL, l'edge client è vincolato alla sola operazione di INSERT per i payload pseudonimizzati, precludendo a livello di database qualsiasi operazione di lettura o manipolazione dei log.
Il terzo livello è il Master Data Store locale: un database SQLite locale sul PC del responsabile dei dati, configurato in modalità Write-Ahead Logging (WAL) per garantire la massima robustezza e ACIDità. Il PC si accende, interroga Supabase tramite uno script Python, scarica i pacchetti, associa i PIN ai veri nomi degli atleti e pulisce immediatamente il cloud.

## Business & Technical Value
L'architettura produce tre risultati misurabili:
•	Pseudonimizzazione ad alto isolamento: Nessun dato nominativo viene esposto sul cloud. Il sistema si basa su un rigoroso disaccoppiamento dei dati, dove il dizionario di de-anonimizzazione che collega il PIN all'identità risiede esclusivamente sul Master Data Store locale.
•	Costo Infrastrutturale Pari a Zero: Sfruttando Supabase esclusivamente come buffer transitorio (i dati restano online pochi minuti prima di essere scaricati e cancellati), il sistema rientra ampiamente nei tier gratuiti del servizio. 
•	Attrito di Adozione Inesistente: Il front-end si apre con interfaccia browser dello smartphone. Non ci sono account da creare, aggiornamenti o ulteriori possibili problemi legati a un App terza, compresa la poca intuitività e i primi attriti.
