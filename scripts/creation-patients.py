import argparse
from html import parser
import random
import token
import requests
from datetime import date, timedelta

API_BASE = "http://localhost:8000"  # adapte si besoin
PATIENTS_ENDPOINT = f"{API_BASE}/api/patients/create"

FIRST_NAMES_M = ["Jean", "Robert", "Lucas", "Thomas", "Hugo", "Maxime", "Paul"]
FIRST_NAMES_F = ["Marie", "Camille", "Julie", "Emma", "Sarah", "Louna", "Chloé"]
LAST_NAMES = ["Dupont", "Martin", "Bernard", "Petit", "Robert", "Richard", "Durand", "Moreau"]

HISTORY = [
    "Aucun antécédent majeur",
    "Hypertension artérielle",
    "Diabète de type 2",
    "Asthme",
    "Antécédents familiaux de cancer",
    "Hypercholestérolémie",
]

SYMPTOMS = [
    "Douleurs abdominales",
    "Fatigue chronique",
    "Toux persistante",
    "Perte de poids involontaire",
    "Fièvre intermittente",
    "Douleurs thoraciques",
]

IMAGING = [
    "Scanner abdominal recommandé",
    "IRM nécessaire",
    "Radio pulmonaire prévue",
    "Échographie de contrôle",
    "TEP-scan à programmer",
]

def random_birth_date(min_age=18, max_age=90) -> date:
    today = date.today()
    age = random.randint(min_age, max_age)
    # date approx (age années + variation)
    base = today - timedelta(days=age * 365)
    return base - timedelta(days=random.randint(0, 364))

def compute_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def build_patient(i: int) -> dict:
    gender = random.choice(["Homme", "Femme"])
    first = random.choice(FIRST_NAMES_M if gender == "Homme" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    dob = random_birth_date()

    return {
        "full_name": f"{first} {last} {i}",
        "date_of_birth": dob.isoformat(),
        "age": compute_age(dob),
        "gender": gender,
        "medical_history": random.choice(HISTORY),
        "symptoms": random.choice(SYMPTOMS),
        "imaging_notes": random.choice(IMAGING),
    }

def list_patients(headers: dict, timeout=10):
    r = requests.get(PATIENTS_ENDPOINT, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

def create_patient(payload: dict, headers: dict, timeout=10):
    return requests.post(PATIENTS_ENDPOINT, json=payload, headers=headers, timeout=timeout)


def login(base_url: str, email: str, password: str, timeout=10) -> str:
    url = f"{base_url.rstrip('/')}/api/auth/login"
    r = requests.post(url, json={"email": email, "password": password}, timeout=timeout)
    r.raise_for_status()
    return r.json()["access_token"]

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main():
    parser = argparse.ArgumentParser(description="Seed patients via API")
    parser.add_argument("-n", "--count", type=int, default=10, help="Nombre de patients à créer")
    parser.add_argument("--base-url", type=str, default="http://localhost:8000", help="Base URL de l'API (ex: http://localhost:8000)")
    parser.add_argument("--skip-duplicates", action="store_true", help="Ignore les patients si full_name existe déjà")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout HTTP en secondes")
    parser.add_argument("--email", required=True, help="Email pour se connecter")
    parser.add_argument("--password", required=True, help="Mot de passe pour se connecter")


    args = parser.parse_args()

    API_BASE = args.base_url.rstrip("/")
    token = login(API_BASE, args.email, args.password, timeout=args.timeout)
    headers = auth_headers(token)
    print("🔐 Auth OK (token récupéré)")

    PATIENTS_ENDPOINT = f"{API_BASE}/api/patients/"

    print(f"🔗 API: {PATIENTS_ENDPOINT}")

    existing_names = set()
    if args.skip_duplicates:
        try:
            existing = list_patients(timeout=args.timeout)
            # si ton API retourne autre chose qu'une liste, adapte ici
            for p in existing:
                if isinstance(p, dict) and "full_name" in p:
                    existing_names.add(p["full_name"])
            print(f"📋 Patients existants: {len(existing_names)}")
        except Exception as e:
            print(f"⚠️ Impossible de lister les patients (skip duplicates désactivé): {e}")
            args.skip_duplicates = False

    created = 0
    for i in range(1, args.count + 1):
        patient = build_patient(i)

        if args.skip_duplicates and patient["full_name"] in existing_names:
            print(f"⏭️  Skip duplicate: {patient['full_name']}")
            continue

        try:
            resp = create_patient(patient, headers, timeout=args.timeout)
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"✅ Created: {patient['full_name']} (id={data.get('id')})")
                created += 1
            else:
                print(f"❌ Failed ({resp.status_code}) for {patient['full_name']}: {resp.text}")
        except requests.exceptions.ConnectionError:
            print("❌ Connexion impossible. Vérifie que le service patients/cases tourne (port 8002).")
            return
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return

    print(f"✨ Terminé. Patients créés: {created}/{args.count}")

if __name__ == "__main__":
    main()
