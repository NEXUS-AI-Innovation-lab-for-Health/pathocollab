#!/usr/bin/env python3
"""
Seed (créer) des patients fictifs via l'API.

Usage (exemples) :

# Patients sur 8002
python3 creation-patients.py --auth-url http://localhost:8000 --api-url http://localhost:8002 \
    --email admin@gmail.com --password adminadmin -n 10
"""
import argparse
import random
import requests
from datetime import date, timedelta
from typing import Dict, Any, List, Optional


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


def random_birth_date(min_age: int = 18, max_age: int = 90) -> date:
    """Génère une date de naissance cohérente (colonne SQL = DATE)."""
    today = date.today()
    age = random.randint(min_age, max_age)
    base = today - timedelta(days=age * 365)
    return base - timedelta(days=random.randint(0, 364))


def compute_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def build_patient(i: int) -> Dict[str, Any]:
    gender = random.choice(["Homme", "Femme"])
    first = random.choice(FIRST_NAMES_M if gender == "Homme" else FIRST_NAMES_F)
    last = random.choice(LAST_NAMES)
    dob = random_birth_date()

    # IMPORTANT : date_of_birth doit être une string "YYYY-MM-DD" (pas datetime)
    return {
        "full_name": f"{first} {last}",
        "date_of_birth": dob.strftime("%Y-%m-%d"),
        "age": compute_age(dob),
        "gender": gender,
        "medical_history": random.choice(HISTORY),
        "symptoms": random.choice(SYMPTOMS),
        "imaging_notes": random.choice(IMAGING),
    }


def unique_full_name(base_name: str, existing_names: set[str]) -> str:
    """Retourne un nom unique. Si base_name existe déjà, ajoute (2), (3), ..."""
    if base_name not in existing_names:
        return base_name
    counter = 2
    while True:
        candidate = f"{base_name} ({counter})"
        if candidate not in existing_names:
            return candidate
        counter += 1



def login(auth_url: str, email: str, password: str, timeout: int = 10) -> str:
    url = f"{auth_url.rstrip('/')}/api/auth/login"
    r = requests.post(url, json={"email": email, "password": password}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"Réponse login inattendue: {data}")
    return data["access_token"]


def auth_headers(access_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}


def list_patients(api_url: str, patients_path: str, headers: Dict[str, str], timeout: int = 10) -> Any:
    url = f"{api_url.rstrip('/')}{patients_path}"
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()


def create_patient(api_url: str, patients_path: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 10) -> requests.Response:
    url = f"{api_url.rstrip('/')}{patients_path}"
    return requests.post(url, json=payload, headers=headers, timeout=timeout)


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed patients via API")
    parser.add_argument("-n", "--count", type=int, default=10, help="Nombre de patients à créer")
    parser.add_argument("--auth-url", type=str, default="http://localhost:8000", help="Base URL du service d'auth (ex: http://localhost:8000)")
    parser.add_argument("--api-url", type=str, default="http://localhost:8002", help="Base URL du service patients/cases (ex: http://localhost:8002)")
    parser.add_argument("--patients-path-list", type=str, default="/api/patients/list", help="Chemin patients pour liste (/api/patients/list)")
    parser.add_argument("--patients-path-create", type=str, default="/api/patients/create", help="Chemin patients pour création (/api/patients/create)")
    parser.add_argument("--skip-duplicates", action="store_true", help="Ignore les patients si full_name existe déjà")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout HTTP en secondes")
    parser.add_argument("--email", required=True, help="Email pour se connecter")
    parser.add_argument("--password", required=True, help="Mot de passe pour se connecter")
    args = parser.parse_args()

    # 1) Auth
    token = login(args.auth_url, args.email, args.password, timeout=args.timeout)
    headers = auth_headers(token)
    print("🔐 Auth OK (token récupéré)")

    # 2) Endpoint info
    patients_url = f"{args.api_url.rstrip('/')}{args.patients_path_create}"
    print(f"🔗 API Patients: {patients_url}")

    # 3) Duplicate check
    existing_names = set()
    if args.skip_duplicates:
        try:
            existing = list_patients(args.api_url, args.patients_path_list, headers=headers, timeout=args.timeout)
            if isinstance(existing, list):
                for p in existing:
                    if isinstance(p, dict) and "full_name" in p:
                        existing_names.add(p["full_name"])
            print(f"📋 Patients existants (détectés): {len(existing_names)}")
        except Exception as e:
            print(f"⚠️ Impossible de lister les patients (skip duplicates désactivé): {e}")
            args.skip_duplicates = False

    # 4) Create
    created = 0
    for i in range(1, args.count + 1):
        patient = build_patient(i)

        # Solution 3 : garantir un nom unique sans suffixe numérique brut.
        base_name = patient["full_name"]
        if args.skip_duplicates and base_name in existing_names:
            print(f"⏭️  Skip duplicate: {base_name}")
            continue

        patient["full_name"] = unique_full_name(base_name, existing_names)
        existing_names.add(patient["full_name"])

        try:
            resp = create_patient(args.api_url, args.patients_path_create, patient, headers=headers, timeout=args.timeout)

            if resp.status_code in (200, 201):
                data = resp.json() if resp.content else {}
                created += 1
                dob_echo = data.get("date_of_birth") if isinstance(data, dict) else None
                if dob_echo is None:
                    # pas bloquant, mais utile à diagnostiquer si l'API ignore le champ
                    print(f"✅ Created: {patient['full_name']} (DOB envoyé={patient['date_of_birth']})")
                    print("   ⚠️  L'API ne renvoie pas date_of_birth -> vérifie que le modèle/schema backend inclut bien ce champ.")
                else:
                    print(f"✅ Created: {patient['full_name']} (DOB={dob_echo})")
            else:
                print(f"❌ Failed ({resp.status_code}) for {patient['full_name']}: {resp.text}")

        except requests.exceptions.ConnectionError:
            print("❌ Connexion impossible. Vérifie que les services tournent et que les ports/URLs sont corrects.")
            return
        except Exception as e:
            print(f"❌ Erreur inattendue: {e}")
            return

    print(f"✨ Terminé. Patients créés: {created}/{args.count}")


if __name__ == "__main__":
    main()
