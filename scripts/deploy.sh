#!/bin/bash

# Script per il deployment su Google Cloud Run
set -e

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Funzione per stampare messaggi colorati
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verifica che gcloud sia installato
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI non è installato. Installalo da: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Verifica che docker sia installato
if ! command -v docker &> /dev/null; then
    print_error "Docker non è installato. Installalo da: https://docs.docker.com/get-docker/"
    exit 1
fi

# Leggi il PROJECT_ID
if [ -z "$GOOGLE_CLOUD_PROJECT" ]; then
    print_warning "GOOGLE_CLOUD_PROJECT non è impostato."
    read -p "Inserisci il tuo Google Cloud Project ID: " PROJECT_ID
    export GOOGLE_CLOUD_PROJECT=$PROJECT_ID
else
    PROJECT_ID=$GOOGLE_CLOUD_PROJECT
fi

print_status "Usando il progetto: $PROJECT_ID"

# Configura gcloud
print_status "Configurando gcloud..."
gcloud config set project $PROJECT_ID

# Abilita le API necessarie
print_status "Abilitando le API necessarie..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build e deploy usando Cloud Build
print_status "Avviando build e deploy con Cloud Build..."
gcloud builds submit --config cloudbuild.yaml .

# Ottieni l'URL del servizio
SERVICE_URL=$(gcloud run services describe chatbot --region=europe-west1 --format="value(status.url)")

print_status "Deploy completato!"
print_status "Il tuo chatbot è disponibile all'indirizzo: $SERVICE_URL"
print_status "Documentazione API: $SERVICE_URL/docs"
print_status "Health check: $SERVICE_URL/health"

echo ""
print_status "Comandi utili:"
echo "  - Visualizza logs: gcloud run services logs read chatbot --region=europe-west1"
echo "  - Aggiorna servizio: gcloud run services update chatbot --region=europe-west1"
echo "  - Elimina servizio: gcloud run services delete chatbot --region=europe-west1"