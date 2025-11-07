#!/usr/bin/env python3
"""
Script di test per verificare la connessione al database PostgreSQL
"""
import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Carica variabili d'ambiente
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')

async def test_database_connection():
    """Testa la connessione al database e esegue alcune query di base"""
    print("🔍 Test connessione database PostgreSQL")
    print(f"📍 URL: {DATABASE_URL}")

    if not DATABASE_URL:
        print("❌ DATABASE_URL non configurata!")
        return False

    engine = None
    try:
        # Crea engine
        engine = create_async_engine(DATABASE_URL, echo=False)
        print("✅ Engine creato")

        # Test connessione
        async with engine.begin() as conn:
            print("✅ Connessione stabilita")

            # Test query semplice
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Versione PostgreSQL: {version[:50]}...")

            # Conta tabelle
            result = await conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = result.fetchall()
            print(f"✅ Tabelle trovate: {[t[0] for t in tables]}")

            # Test insert semplice (se tabelle esistono)
            if 'sessions' in [t[0] for t in tables]:
                # Conta sessioni esistenti
                result = await conn.execute(text("SELECT COUNT(*) FROM sessions"))
                count = result.fetchone()[0]
                print(f"✅ Sessioni esistenti: {count}")

                # Test insert temporaneo (rollback)
                await conn.execute(text("""
                    INSERT INTO sessions (session_id, current_lifecycle, created_at, updated_at)
                    VALUES ('test_session', 'NUOVA_LEAD', NOW(), NOW())
                """))
                print("✅ Insert test riuscito")

                # Rollback per pulizia
                await conn.rollback()
                print("✅ Rollback completato")

        print("🎉 Test database completato con successo!")
        return True

    except Exception as e:
        print(f"❌ Errore durante il test: {e}")
        return False

    finally:
        if engine:
            await engine.dispose()

if __name__ == "__main__":
    success = asyncio.run(test_database_connection())
    exit(0 if success else 1)