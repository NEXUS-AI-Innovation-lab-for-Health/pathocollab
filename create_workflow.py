import json
import requests

# Créer le workflow pour le cas existant
workflow_data = {
    "case_id": "BIO-2025-858715",
    "specialists_order": ["dr.smith@pixtral.fr", "dr.johnson@pixtral.fr", "dr.williams@pixtral.fr"]
}

try:
    response = requests.post(
        "http://localhost:8003/api/workflows",
        json=workflow_data,
        headers={
            "Content-Type": "application/json"
        }
    )
    
    if response.status_code == 201:
        print("✅ Workflow créé avec succès!")
        print("Réponse:", response.json())
    else:
        print(f"❌ Erreur: {response.status_code}")
        print("Réponse:", response.text)
        
except Exception as e:
    print(f"❌ Erreur de connexion: {e}")
