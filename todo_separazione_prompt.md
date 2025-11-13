"""
Task: Separare il prompt di sistema per dividere identità/atteggiamento dalle questioni tecniche

Obiettivo:
- Il prompt di sistema (in DB) deve contenere SOLO informazioni sull'identità e atteggiamento
- Le questioni tecniche (lifecycle, istruzioni generali) devono essere gestite in _get_unified_prompt

Passi completati:
1. ✅ Modificato system_prompt_service.py per definire SYSTEM_PROMPT con solo identità
2. ✅ Modificato _get_unified_prompt per includere lifecycle e istruzioni generali
3. ✅ Testato che il codice funzioni (import e inizializzazione OK)
4. ✅ Creata migration Alembic per aggiornare il prompt nel DB
5. ⏳ Applicare la migration quando il DB è disponibile (alembic upgrade head)

Note:
- Il prompt di sistema ora contiene solo:
  - Identità del chatter
  - Atteggiamento e tono da usare
- Le istruzioni tecniche sono state spostate in _get_unified_prompt
- Questo permette di modificare identità/atteggiamento senza toccare la logica tecnica
- Il comportamento dovrebbe rimanere invariato per l'utente finale
- Migration creata: 27379cc994a3_update_default_system_prompt_to_identity_only.py
"""