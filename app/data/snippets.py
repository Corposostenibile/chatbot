"""
Snippet di messaggi pre-scritti per il chatbot Corposostenibile
Organizzati per categoria e lifecycle
"""

# Snippet per il Lifecycle 2 (CONTRASSEGNATO)
LEVEL_2_SNIPPETS = {
    "livello_2": "Bene! :)",
    "a_livello_2_b": """Per poterti aiutare al meglio ti chiedo:
1) Qual è il risultato che vorresti raggiungere? 
2) Cosa hai provato in passato? 
3) Posso chiederti la tua età?""",
    "a_livello_2_c": "Ps. Posso chiederti il tuo nome per non fare gaffe? 🙏"
}

# Snippet per il Lifecycle 3 (IN_TARGET)
LEVEL_3_SNIPPETS = {
    "livello_3_a": "Grazie per la condivisione 🙏",
    "livello_3_b": "Però vorrei capire qual è la tua motivazione, cosa ti spinge a cambiare proprio ora?",
    "a_livello_3_c": "E la tua età gentilmente 😊🙏"
}

# Snippet per il Lifecycle 4 (LINK_DA_INVIARE)
LEVEL_4_SNIPPETS = {
    "a_livello_4_a_no_disponibilita": "Che ne dici di questo plan... fissiamo una call Gratuita quando hai un attimo libero e vediamo come posso aiutarti",
    "livello_4_b": "Possiamo discutere i tuoi obiettivi in modo più dettagliato e progettare un piano d'azione per realizzarli! Che ne dici?"
}

# Snippet per il Lifecycle 5 (LINK_INVIATO)
LEVEL_5_SNIPPETS = {
    "a_livello_5_a": "Perfetto!🔥 Ti invio il link di prenotazione così puoi scegliere tu giorno e orario che ti tornano più comodi. Troverai anche alcune domande per aiutarti al meglio durante la nostra call",
    "livello_5_b": "Il link di prenotazione ha una durata di 10 minuti prima di scadere, avresti 30 secondi per completarlo adesso? Ci vogliono pochissimi secondi :)"
}

# Snippet generici per obiezioni e situazioni specifiche
GENERIC_SNIPPETS = {
    "budget": """Capisco perfettamente che l'investimento possa sembrare importante, il mio impegno è offrire un percorso che porti valore concreto e risultati duraturi per la tua salute, con tutta la professionalità e l'attenzione che meriti.
Resto a tua disposizione per qualsiasi dubbio o se vorrai riparlarne in futuro. Il piacere è mio nel poterti accompagnare, anche solo con i miei contenuti. A presto! 💚""",
    "b_budget_obiezione": "Pensi che leventuale investimento sarebbe sostenibile per te, se fosse in linea con ciò che stai cercando? :)",
    "costo_a": "La Consulenza è totalmente gratuita, mentre per il Programma 1to1 si parte da 150 €/mese, ma tutto va valutato in base a di cosa hai bisogno tu affinché possa garantirti i risultati",
    "costo_b": "Ti mando il link per prenotare la Consulenza Gratuita così scegli giorno e orario che ti tornano più comodi?",
    "b_info_1": "Io mi occupo di Nutrizione Integrativa online, e nello specifico con il team Corposostenibile aiutiamo le persone a trasformare il proprio corpo e le proprie abitudini alimentari attraverso la combinazione personalizzata di Nutrizione, Sport e Psicologia Alimentare.",
    "b_info_2": "Non offrendo piani copia ed incolla si fissa una prima consulenza totalmente gratuita, finalizzata nel conoscerci ma soprattutto studiare i tuoi obiettivi, esigenze ed eventuali difficoltà per riuscire a presentarti poi la migliore soluzione in maniera sostenibile! Da lì avrai modo di fare le tue valutazioni e decidere se partire o meno .💪🏼☺️",
    "b_io_mi_occupo": "Io mi occupo di percorsi integrativi online, e nello specifico con il team Corposostenibile aiutiamo le persone a trasformare il proprio corpo e le proprie abitudini quotidiane attraverso una combinazione personalizzata , pensate alle esigenze di ogni persona",
    "b_nit": """Capisco e grazie per la tua trasparenza.
Non preoccuparti, noi rimaniamo qua. Quando sara il momento giusto per iniziare fammi sapere che sarò qui ad aiutarti 🙏""",
    "b_no_disponibilita": """Possiamo fare così: fissa ugualmente la consulenza in uno degli ultimi slot disponibili, giusto per fermarti il posto. Ho davvero paura che altrimenti non ci siano più disponibilità e sento che per te invece è una priorità.

Poi successivamente il consulente del mio team a te assegnato ti scriverà prontamente per presentarsi, avvisalo dell'esigenza della riprogrammazione così che possiate stabilire insieme per un giorno ed un orario comodo per entrambi. Che ne pensi?""",
    "parlare_con_te": """Sono molto presente con le persone che seguo ogni giorno durante il Programma 1to1 e ovviamente devo sempre dare priorità a qualsiasi richiesta mi facciano. 

Quello che ti posso garantire è che tra me o il Consulente Senior con cui parlerai del mio team, ti ascolteremo in modo professionale e comunque ci confronteremo per analizzare le tue esigenze in modo dettagliato prima di proporti qualsiasi possibile programma da percorrere insieme!""",
    "under18": "Grazie della condivisione, ma lavoro solo con gli over 18 🙏",
    "under": """Grazie della tua condivisione, mi permetto di condividerti un link con un rapido questionario che mi permetterà di indicarti il programma migliore da percorrere insieme (poi sarai tu a valutare tranquillamente se iniziare o meno!) ecco qui:
https://api.leadconnectorhq.com/widget/survey/BdZIlWao4BMoSAF5KGS8""",
}

# Risorse di supporto
RESOURCE_SNIPPETS = {
    "c_bibbia_del_cortisolo": "https://www.corposostenibile.com/stressebook",
    "c_bibbia_del_sonno": "https://www.corposostenibile.com/sonnoebook?",
    "c_bibbia_della_digestione": "https://onedrive.live.com/?redeem=aHR0cHM6Ly8xZHJ2Lm1zL2IvYy83ZjVmOWRmYzNlZjcxNGI1L0VZUXhpVlB0Nm1kT3NxTmx0Tk5OVkxJQm8ybTY4NV9PMmgyOV9VX2dzY0twREE_ZT1mYWV4OXImbWNwX3Rva2VuPWV5SndhV1FpT2pVM05ESXpNeXdpYzJsa0lqbzVORFE1T0RReU15d2lZWGdpT2lJNVkyVXpNekEyWVdVMlptRXpPVFEzT0dWaE1HVmhNakppWlRZd01tSm1NQ0lzSW5Seklqb3hOelV6TnpFME56Z3pMQ0psZUhBaU9qRTNOVFl4TXpNNU9ETjkuQ3IySENMc2xYSTc5ZVVXS3pOamtTUi1Jd1BXa3cwRDVqd2RYbUJzZlEzRQ&cid=7F5F9DFC3EF714B5&id=7F5F9DFC3EF714B5%21s53893184eaed4e67b2a365b4d34d54b2&parId=7F5F9DFC3EF714B5%21150&o=OneUp&fbclid=PAQ0xDSwL0b7NleHRuA2FlbQIxMAABp4DqJVhGYa9ZIlQhQghr2o4u_cw8OdyuGr8RGHiWbjuWf1PxVOv-rbPjkd5H_aem_DfsALIgrYZr64MKxJCTJyQ",
    "c_dimagrimento_per_pigri": "https://my.manychat.com/r?act=462cea8f08f4ae2c31c156a66ad25b04&u=755888096&p=574233&h=a59649b2a5&fbclid=PAQ0xDSwL0btxleHRuA2FlbQIxMAABp1Y21cxZr3FGqqZHbbb_3gEHLIlsJtyOK5OkdzMOpspOn_iN45GhxIeSejSQ_aem_LMQvIfVuC4mVYlMv_Z1LbA"
}

# Info professionali
INFO_SNIPPETS = {
    "info_celestino": """Io mi occupo di reset posturale, e nello specifico con il team CorpoSostenibile aiutiamo le persone a trasformare il proprio corpo e la propria relazione con esso, attraverso un approccio integrato che unisce riequilibrio posturale, psicologia e nutrizione. 
Il reset posturale agisce in profondità sul corpo, lavorando su tensioni, blocchi e compensazioni che spesso raccontano molto anche del vissuto emotivo della persona"""
}

# Messaggi generici
GENERIC_MESSAGES = {
    "risposta_tardiva2": "Eccomi, scusami la risposta tardiva, come stai? Ricevo davvero tante richieste e ci tengo a rispondere personalmente.",
    "risposta_tardiva3": "Hey NOME Buon/a Giorno/Pomeriggio/Sera , scusami la risposta tardiva 🙏🏼\ncome stai? :)"
}

# Raccolta completa di tutti gli snippet organizzati
ALL_SNIPPETS = {
    **LEVEL_2_SNIPPETS,
    **LEVEL_3_SNIPPETS,
    **LEVEL_4_SNIPPETS,
    **LEVEL_5_SNIPPETS,
    **GENERIC_SNIPPETS,
    **RESOURCE_SNIPPETS,
    **INFO_SNIPPETS,
    **GENERIC_MESSAGES
}

def get_snippet(snippet_id: str) -> str:
    """Recupera uno snippet per ID"""
    return ALL_SNIPPETS.get(snippet_id, "")

def get_snippets_for_lifecycle(lifecycle_name: str) -> dict:
    """Recupera tutti gli snippet per un lifecycle specifico"""
    lifecycle_lower = lifecycle_name.lower()
    
    if "contrassegnato" in lifecycle_lower or "level_2" in lifecycle_lower:
        return LEVEL_2_SNIPPETS
    elif "in_target" in lifecycle_lower or "level_3" in lifecycle_lower:
        return LEVEL_3_SNIPPETS
    elif "link_da_inviare" in lifecycle_lower or "level_4" in lifecycle_lower:
        return LEVEL_4_SNIPPETS
    elif "link_inviato" in lifecycle_lower or "level_5" in lifecycle_lower:
        return LEVEL_5_SNIPPETS
    else:
        return {}
