import requests
import argparse

def login(auth_url, email, password):
    url = f"{auth_url}/api/auth/login"
    r = requests.post(url, json={"email": email, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auth-url", required=True)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    token = login(args.auth_url, args.email, args.password)
    headers = {"Authorization": f"Bearer {token}"}

    # Récupérer tous les patients
    r = requests.get(f"{args.api_url}/api/patients/list", headers=headers)
    r.raise_for_status()
    patients = r.json()

    print(f"Patients trouvés : {len(patients)}")

    for p in patients:
        patient_id = p["id"]
        delete_url = f"{args.api_url}/api/patients/delete/{patient_id}"
        resp = requests.delete(delete_url, headers=headers)

        if resp.status_code == 200:
            print(f"Supprimé : {patient_id}")
        else:
            print(f"Erreur suppression {patient_id} : {resp.status_code}")

    print("Terminé.")

if __name__ == "__main__":
    main()
