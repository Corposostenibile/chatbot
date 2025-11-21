---
applyTo: '**'
---
# Resoconto Completo
**Stato dell'arte del progetto Chatbot Corposostenibile**

**Phase: Overview**
## 🌍 Panoramica Generale del Progetto
Il progetto consiste nello sviluppo di un **Chatbot Avanzato per Corposostenibile**, progettato per automatizzare e ottimizzare l'interazione con i lead e i clienti.

Il sistema opera come un backend intelligente che:
- **Riceve richieste da respond.io**: Agisce come cervello centrale elaborando i messaggi provenienti dai canali di messaggistica (WhatsApp, Messenger, ecc.) integrati via respond.io.
- **Gestisce il Ciclo di Vita dell'Utente**: Segue l'utente attraverso un funnel definito (da `NUOVA_LEAD` a `IN_TARGET`), adattando le risposte e le strategie di comunicazione in base allo stato corrente.
- **Fornisce Risposte AI Contestualizzate**: Utilizza modelli AI avanzati per generare risposte naturali, empatiche e persuasive, guidando l'utente verso l'obiettivo di conversione (es. prenotazione consulenza).

---

**Phase: Fase 1**
## 🏗️ Architettura Base e Setup Iniziale
Il progetto inizia con la configurazione dell'ambiente di sviluppo utilizzando **Poetry** per la gestione delle dipendenze Python. Viene implementato un sistema di containerizzazione **Docker** per garantire la riproducibilità dell'ambiente.

**Phase: Fase 2**
## 🤖 Implementazione del Sistema di Gestione del Ciclo di Vita
Viene sviluppato un sistema completo per la gestione del ciclo di vita. Il sistema gestisce le seguenti fasi:
- `NUOVA_LEAD`: Lead appena acquisito
- `CONTRASSEGNATO`: Lead che ha mostrato interesse
- `IN_TARGET`: Lead qualificato per il servizio
- `LINK_DA_INVIARE`: Pronto per ricevere link consulenza
- `LINK_INVIATO`: link inviato con successo

Il sistema utilizza un approccio dinamico con script specifici per ciascuna fase e trigger automatici di transizione basati sull'interazione con l'utente.

**Phase: Fase 3**
## 🗄️ Persistenza dei Dati e Database
Viene implementata la persistenza completa utilizzando **PostgreSQL** come database principale. Il sistema utilizza **SQLAlchemy** come ORM per gestire:
- **Sessioni di conversazione**: Memorizzazione di tutte le interazioni utente
- **Messaggi**: Cronologia completa delle conversazioni
- **Metadati**: Informazioni sul ciclo di vita e timestamp
- **System Prompts**: Gestione dinamica dei prompt di sistema con versioning
- **Human Tasks**: Sistema di task per intervento umano con associazione a sessioni specifiche

Vengono creati modelli Pydantic per la validazione dei dati e gestione sicura delle operazioni database.

**Phase: Fase 4**
## 🚀 Integrazione AI e Sistema dei Prompt
L'integrazione con **Google Gemini AI** viene ottimizzata per fornire risposte più naturali e coinvolgenti attraverso un sistema sofisticato di prompt statici e dinamici.

### Prompt Statico di Sistema
Viene definito un `SYSTEM_PROMPT` principale che stabilisce l'identità dell'AI e le regole fondamentali:
- **Identità**: Empatico, professionale ma colloquiale, rappresentante di Corposostenibile
- **Stile conversazionale**: Risposte brevi (2-3 righe), uso occasionale di emoji, tono caldo e amichevole
- **Regole generali**: Sempre fare domande per mantenere attivo il dialogo, non menzionare mai i lifecycle tecnici
- **Formato risposta**: JSON strutturato obbligatorio con messaggi, decisioni lifecycle e confidenza

### Script Dinamici per Lifecycle
Per ogni fase del ciclo di vita vengono definiti `LIFECYCLE_SCRIPTS` specifici contenenti:
- **Script guida**: Testo narrativo che l'AI deve seguire come base per le risposte
- **Obiettivo della fase**: Scopo specifico da raggiungere in quella fase
- **Indicatori di transizione**: Segni che indicano quando passare alla fase successiva
- **Prossima fase**: Lifecycle target per la transizione

### Sistema di Snippet di Messaggi
Viene implementato un sistema avanzato di snippet pre-scritti per migliorare la qualità e consistenza delle risposte:
- **Snippet Organizzati per Lifecycle**: Raccolta di messaggi specifici per ogni fase
- **Snippet Generici**: Messaggi per obiezioni comuni (budget, costi, informazioni sul servizio)
- **Primo Messaggio Automatico**: Sistema di risposta fissa per il primo contatto che include automaticamente snippet appropriati
- **Risorse di Supporto**: Link diretti a materiali informativi (Bibbia del Cortisolo, Sonno, Digestione)
- **Info Professionali**: Descrizioni standardizzate dei servizi offerti
- **Gestione Tardiva**: Risposte predefinite per gestire ritardi nelle comunicazioni

### Costruzione Dinamica dei Prompt
Il sistema genera prompt unificati in tempo reale combinando:
- Contesto statico (System Prompt)
- Contesto dinamico (Script Lifecycle)
- Snippet Disponibili
- Cronologia conversazione (ultimi 10 messaggi)
- Messaggio utente
- Istruzioni specifiche

### Decisioni AI sul Lifecycle
L'AI prende decisioni automatiche sulla progressione attraverso:
- **Valutazione confidenza**: Punteggio da 0.0 a 1.0 per ogni decisione
- **Soglia di transizione**: Cambio lifecycle solo con confidenza ≥ 0.7
- **Ragionamento esplicito**: Spiegazione delle decisioni per tracciabilità
- **Transizioni condizionate**: Passaggio automatico basato sugli indicatori definiti

### Funzionalità Avanzate dell'AI
- **Prompting avanzato**: Istruzioni specifiche per interazioni umane
- **Gestione della confidenza**: Valutazione dell'affidabilità delle decisioni AI
- **Logging dettagliato**: Tracciamento completo delle risposte e decisioni
- **Supporto messaggi multipli**: Possibilità di fornire multipli messaggi in un unico output con delay controllati
- **Batch Waiting**: Sistema di aggregazione messaggi per evitare chiamate AI multiple in sequenza rapida (default 60s)

**Phase: Fase 5**
## 🌐 Interfaccia Web e Template
Viene sviluppata un'interfaccia web completa utilizzando FastAPI con Jinja2 per il rendering dei template:
- **Endpoint /preview**: Interfaccia di test per la rotta principale /chat
- **Template HTML**: Pagine web per l'interazione e il monitoraggio
- **Dashboard di monitoraggio**: Visualizzazione dello stato del sistema
- **Gestione sessioni**: Interfaccia per visualizzare le conversazioni salvate
- **Gestione System Prompts**: Pagina dedicata per modificare i prompt di sistema
- **Dashboard Human Tasks**: Interfaccia completa per gestire task di intervento umano
- **Pagine Session Tasks**: Visualizzazioni specifiche per task associati a singole sessioni

**Phase: Fase 6**
## 🐳 Infrastruttura di Produzione Base
La configurazione di produzione include:
- **Docker Compose**: Orchestrazione completa dei servizi
- **Configurazione porte**: Mapping corretto per l'ambiente di produzione
- **Script di gestione**: Automazione completa delle operazioni server

**Phase: Fase 7**
## 🌐 Configurazione Webhook con Dominio Pubblico e SSL
Viene implementato il sistema completo per ricevere webhook esterni da respond.io attraverso un dominio pubblico sicuro:
- **Dominio DuckDNS**: Configurazione del dominio `corposostenibile.duckdns.org`
- **Nginx Reverse Proxy**: Setup di Nginx come proxy inverso
- **Certificato SSL Let's Encrypt**: Installazione e configurazione automatica di certificati SSL gratuiti
- **Integrazione Webhook respond.io**: Configurazione degli endpoint per ricevere webhook
- **Sicurezza e Autenticazione**: Meccanismi di sicurezza per validare i webhook in entrata

**Phase: Fase 8**
## 📊 Dashboard di Monitoraggio e Sessioni
Viene implementata una dashboard completa per la visualizzazione dei dati:
- **Dashboard sessioni**: Interfaccia web per esplorare tutte le conversazioni
- **Visualizzazione conversazioni**: Cronologia completa delle interazioni
- **Monitoraggio stato**: Controlli automatici di health e performance
- **Gestione risorse**: Monitoraggio dell'utilizzo del sistema
- **Gestione System Prompts**: Interfaccia per modificare e versionare i prompt AI

**Phase: Fase 9**
## 🛠️ Script di Gestione Completa

### Sviluppo Locale con local.sh
- Setup Automatico ambiente e DB Docker
- Virtual Environment e dipendenze Poetry
- Configurazione .env.local automatica
- Migrazioni Database con Alembic
- Comandi di Sviluppo (test, linting, format)

### Produzione con server.sh
- Gestione Server (start/stop/monitor)
- SSL Automation (Let's Encrypt)
- Monitoraggio Health e Troubleshooting
- Manutenzione e Aggiornamenti

**Phase: Fase 10**
## 🔧 Refactoring e Ottimizzazioni Finali
- **Migrazione a ORM**: Sostituzione query raw con SQLAlchemy
- **Pulizia template**: Utilizzo Jinja2Templates integrato
- **Refactoring UnifiedAgent**: Estrazione metodi helper
- **Gestione Timezone**: Risoluzione problemi datetime nei modelli

**Phase: Fase 11**
## 📚 Documentazione e Testing
- Documentazione tecnica e guide deployment
- Script di test automatici
- Documentazione flusso end-to-end
- Documentazione API interattiva (Swagger/OpenAPI)

**Phase: Fase 12**
## 🧑‍💼 Sistema di Gestione Task Umani
Viene implementato un sistema completo per la gestione di task di intervento umano, permettendo all'AI di richiedere assistenza professionale quando necessario.

### Modello Database Human Tasks
- Campi principali: title, description, status, assigned_to, completed, session_id
- Relazioni dirette con le sessioni
- Metadata JSON e Timestamp automatici

### Integrazione AI e Blocco Conversazionale
- **Creazione Automatica**: L'AI genera task basati sul contesto
- **Blocco del Flusso**: Sospensione risposte automatiche se esiste task aperto
- **Notifiche Non-Bloccanti**: Banner nell'interfaccia chat

### API Endpoints Completa
- CRUD completo per Human Tasks (POST, GET, PUT)
- Endpoint specifici per task di sessione

### Interfacce Web Avanzate
- **Human Tasks Dashboard**: Vista generale con filtri
- **Session Tasks Page**: Vista specifica per conversazione
- **Modali Interattive**: Dettagli completi task
- **Toggle Completamento**: Interfaccia intuitiva
- **Badge di Stato**: Indicatori visivi chiari

**Phase: Fase 13**
## 📝 Sistema di Feedback e Note sui Messaggi
È stato implementato un sistema di feedback granulare che permette ai coordinatori e agli sviluppatori di annotare specifici messaggi dell'AI per monitorare la qualità e pianificare miglioramenti.

### Modello Database Message Notes
- **Associazione Diretta**: Ogni nota è collegata a un singolo messaggio (`message_id`)
- **Rating e Feedback**: Possibilità di assegnare un voto (rating) e un commento testuale libero
- **Tracciabilità**: Registrazione dell'autore della nota e timestamp

### Workflow di Miglioramento Continuo
- **Review a Posteriori**: I coordinatori possono rileggere le sessioni e identificare risposte AI non ottimali
- **Annotazione Puntuale**: Inserimento di note specifiche su cosa non ha funzionato (es. "Tono troppo formale", "Ha ignorato la domanda")
- **Ottimizzazione Prompts**: Gli sviluppatori utilizzano questi feedback aggregati per raffinare i System Prompts e gli script dei Lifecycle

---
