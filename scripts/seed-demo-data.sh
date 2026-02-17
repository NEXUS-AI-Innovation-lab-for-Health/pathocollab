#!/bin/bash
set -e

echo "🌱 Seeding demo data for Pixtral..."

API_AUTH="http://localhost:8001/api"
API_CASES="http://localhost:8002/api"
API_WORKFLOW="http://localhost:8003/api"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Creating demo users...${NC}"

# Create users
curl -s -X POST "$API_AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@pixtral.fr",
    "password": "Admin123!",
    "full_name": "Dr. Admin",
    "role": "admin"
  }' > /dev/null && echo -e "${GREEN}✓${NC} Admin user created"

curl -s -X POST "$API_AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "louna.dubois@pixtral.fr",
    "password": "Louna123!",
    "full_name": "Dr. Louna Dubois",
    "role": "anatomopathologiste"
  }' > /dev/null && echo -e "${GREEN}✓${NC} Dr. Louna Dubois created"

curl -s -X POST "$API_AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "arthur.laurent@pixtral.fr",
    "password": "Arthur123!",
    "full_name": "Dr. Arthur Laurent",
    "role": "anatomopathologiste"
  }' > /dev/null && echo -e "${GREEN}✓${NC} Dr. Arthur Laurent created"

curl -s -X POST "$API_AUTH/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "lea.roux@pixtral.fr",
    "password": "Lea123!",
    "full_name": "Dr. Léa Roux",
    "role": "oncologue"
  }' > /dev/null && echo -e "${GREEN}✓${NC} Dr. Léa Roux created"

echo -e "\n${YELLOW}Creating demo patients...${NC}"

# Create patient 1
PATIENT_1=$(curl -s -X POST "$API_CASES/patients" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Joe Lardin",
    "age": 62,
    "gender": "Homme",
    "medical_history": "Fumeur actif (30 paquets-années). Hypertension artérielle contrôlée.",
    "symptoms": "Toux persistante depuis 2 mois, hémoptysie occasionnelle.",
    "imaging_notes": "Scanner thoracique: nodule pulmonaire de 2,8cm lobe supérieur droit."
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓${NC} Patient created: $PATIENT_1"

# Create patient 2
PATIENT_2=$(curl -s -X POST "$API_CASES/patients" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Marie Dupont",
    "age": 58,
    "gender": "Femme",
    "medical_history": "Aucun antécédent notable.",
    "symptoms": "Douleurs abdominales, fatigue chronique.",
    "imaging_notes": "IRM abdominale: masse hépatique suspecte 4cm."
  }' | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓${NC} Patient created: $PATIENT_2"

echo -e "\n${YELLOW}Creating demo cases...${NC}"

# Get user IDs
LOUNA_ID=$(curl -s "$API_AUTH/auth/users/email/louna.dubois@pixtral.fr" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
ARTHUR_ID=$(curl -s "$API_AUTH/auth/users/email/arthur.laurent@pixtral.fr" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
LEA_ID=$(curl -s "$API_AUTH/auth/users/email/lea.roux@pixtral.fr" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")

# Create case 1
CASE_1=$(curl -s -X POST "$API_CASES/cases" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"$PATIENT_1\",
    \"title\": \"Biopsie pulmonaire - Nodule suspect\",
    \"description\": \"Analyse anatomopathologique d'un nodule pulmonaire de 2,8cm lobe supérieur droit.\",
    \"created_by\": \"$LOUNA_ID\",
    \"assigned_specialists\": [\"$LOUNA_ID\", \"$ARTHUR_ID\", \"$LEA_ID\"]
  }" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓${NC} Case created: $CASE_1"

# Create case 2
CASE_2=$(curl -s -X POST "$API_CASES/cases" \
  -H "Content-Type: application/json" \
  -d "{
    \"patient_id\": \"$PATIENT_2\",
    \"title\": \"Biopsie hépatique - Masse suspecte\",
    \"description\": \"Analyse d'une masse hépatique de 4cm découverte à l'IRM.\",
    \"created_by\": \"$ARTHUR_ID\",
    \"assigned_specialists\": [\"$ARTHUR_ID\", \"$LEA_ID\"]
  }" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo -e "${GREEN}✓${NC} Case created: $CASE_2"

echo -e "\n${YELLOW}Creating workflows...${NC}"

# Create workflow for case 1
curl -s -X POST "$API_WORKFLOW/workflows" \
  -H "Content-Type: application/json" \
  -d "{
    \"case_id\": \"$CASE_1\",
    \"specialists_order\": [\"$LOUNA_ID\", \"$ARTHUR_ID\", \"$LEA_ID\"]
  }" > /dev/null && echo -e "${GREEN}✓${NC} Workflow created for $CASE_1"

# Create workflow for case 2
curl -s -X POST "$API_WORKFLOW/workflows" \
  -H "Content-Type: application/json" \
  -d "{
    \"case_id\": \"$CASE_2\",
    \"specialists_order\": [\"$ARTHUR_ID\", \"$LEA_ID\"]
  }" > /dev/null && echo -e "${GREEN}✓${NC} Workflow created for $CASE_2"

echo -e "\n${GREEN}✅ Demo data seeded successfully!${NC}"
echo -e "\n${YELLOW}Login credentials:${NC}"
echo "Admin: admin@pixtral.fr / Admin123!"
echo "Dr. Louna Dubois: louna.dubois@pixtral.fr / Louna123!"
echo "Dr. Arthur Laurent: arthur.laurent@pixtral.fr / Arthur123!"
echo "Dr. Léa Roux: lea.roux@pixtral.fr / Lea123!"
