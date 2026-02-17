import requests
import json
from datetime import date

# Données des patients à créer
patients_data = [
    {
        "full_name": "Jean Dupont",
        "date_of_birth": "1980-05-15",
        "age": 44,
        "gender": "Homme",
        "medical_history": "Antécédents de hypertension",
        "symptoms": "Douleurs abdominales",
        "imaging_notes": "Scanner abdominal recommandé"
    },
    {
        "full_name": "Marie Martin", 
        "date_of_birth": "1975-09-22",
        "age": 48,
        "gender": "Femme",
        "medical_history": "Diabète de type 2",
        "symptoms": "Fatigue chronique",
        "imaging_notes": "IRM nécessaire"
    },
    {
        "full_name": "Robert Bernard",
        "date_of_birth": "1990-03-10",
        "age": 34,
        "gender": "Homme",
        "medical_history": "Aucun antécédent majeur",
        "symptoms": "Légère toux",
        "imaging_notes": "Radio pulmonaire prévue"
    }
]

def create_patients():
    """Créer les patients via l'API"""
    base_url = "http://localhost:8002"
    
    print("🔄 Création des patients dans la base de données...")
    
    for patient_data in patients_data:
        try:
            response = requests.post(
                f"{base_url}/api/patients/",
                json=patient_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 201:
                patient = response.json()
                print(f"✅ Patient créé: {patient['full_name']} (ID: {patient['id']})")
                print(f"   Date de naissance: {patient['date_of_birth']}")
            else:
                print(f"❌ Erreur création patient {patient_data['full_name']}: {response.status_code}")
                print(f"   Response: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("❌ Erreur de connexion au service cases-service")
            print("   Assurez-vous que le service est démarré sur localhost:8002")
            return False
        except requests.exceptions.Timeout:
            print("❌ Timeout lors de la création des patients")
            return False
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return False
    
    print("✨ Tous les patients ont été créés avec succès!")
    return True

def list_patients():
    """Lister tous les patients existants"""
    try:
        response = requests.get(
            "http://localhost:8002/api/patients/",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            patients = response.json()
            print(f"\n📋 Liste des patients dans la base ({len(patients)} patients):")
            for patient in patients:
                print(f"   • {patient['full_name']} (ID: {patient['id']})")
                print(f"     Date de naissance: {patient['date_of_birth']}")
                print(f"     Âge: {patient['age']}, Genre: {patient['gender']}")
                print()
        else:
            print(f"❌ Erreur récupération patients: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des patients: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🏥 SCRIPT DE CRÉATION DE PATIENTS - PATHOCOLLAB")
    print("=" * 60)
    
    # D'abord lister les patients existants
    list_patients()
    
    # Créer les nouveaux patients
    success = create_patients()
    
    if success:
        # Relister pour vérifier
        print("\n" + "=" * 60)
        list_patients()
    
    print("=" * 60)
    print("🏁 Script terminé")
    print("=" * 60)
