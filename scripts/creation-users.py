#!/usr/bin/env python3
"""
create-users.py (v2)
- Récupère un token via --auth-url (POST /api/auth/login)
- Exécute ensuite les actions (register / cleanup list+delete) via --api-url

Pourquoi 2 URLs ?
- auth-url : le service qui délivre le JWT (auth/login)
- api-url  : le service qui expose les routes de gestion users (register, list, delete)
    

Endpoints par défaut côté api-url:
    REGISTER: POST   /api/auth/register
    LIST:     GET    /api/auth/users/          (si dispo, sinon configurable)
    DELETE:   DELETE /api/auth/users/{user_id} (si dispo, sinon configurable)

Tu peux surcharger:
    --register-path
    --list-users-path
    --delete-user-path

Exemples:
    # Même service pour token + actions
    python3 create-users.v2.py --auth-url http://localhost:8000 --api-url http://localhost:8000 --cleanup --email admin@gmail.com --password adminadmin

    # Token via auth-service (8000) mais actions via gateway (8001)
    python3 create-users.v2.py --auth-url http://localhost:8000 --api-url http://localhost:8001 --cleanup --email admin@gmail.com --password adminadmin

    # Actions seulement (pas de cleanup), création
    python3 create-users.v2.py --auth-url http://localhost:8000 --api-url http://localhost:8001
"""

from __future__ import annotations
import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple
import requests

DEFAULT_USERS = [
    {"email": "admin@gmail.com", "password": "adminadmin", "full_name": "Admin", "role": "admin"},
    {"email": "arthur@gmail.com", "password": "arthur1234", "full_name": "Dr. Arthur", "role": "anatomopathologiste"},
    {"email": "louna@gmail.com", "password": "louna1234", "full_name": "Dr. Louna", "role": "radiologue"},
    {"email": "jack@gmail.com", "password": "jack1234", "full_name": "Dr. Jack", "role": "oncologue"},
]

def url_join(base: str, path: str) -> str:
    return base.rstrip("/") + "/" + path.lstrip("/")

def login(auth_url: str, email: str, password: str, timeout: int) -> str:
    url = url_join(auth_url, "/api/auth/login")
    r = requests.post(url, json={"email": email, "password": password}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    token = data.get("access_token") or data.get("token") or data.get("accessToken")
    if not token:
        raise RuntimeError(f"Réponse login inattendue (pas de token): {data}")
    return token

def register(api_url: str, register_path: str, user: Dict[str, Any], headers: Dict[str, str], timeout: int) -> Tuple[bool, str]:
    url = url_join(api_url, register_path)
    r = requests.post(url, json=user, headers=headers, timeout=timeout)
    if r.status_code in (200, 201):
        return True, "created"
    return False, f"{r.status_code} {r.text.strip()}"

def list_users(api_url: str, list_path: str, headers: Dict[str, str], timeout: int) -> List[Dict[str, Any]]:
    url = url_join(api_url, list_path)
    r = requests.get(url, headers=headers, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    for k in ("items", "results", "users"):
        v = data.get(k)
        if isinstance(v, list):
            return v
    raise RuntimeError(f"Format liste users inattendu: {data}")

def delete_user(api_url: str, delete_path_tpl: str, user_id: str, headers: Dict[str, str], timeout: int) -> Tuple[bool, str]:
    path = delete_path_tpl.replace("{user_id}", str(user_id)).replace("{id}", str(user_id))
    url = url_join(api_url, path)
    r = requests.delete(url, headers=headers, timeout=timeout)
    if r.status_code in (200, 204):
        return True, "deleted"
    return False, f"{r.status_code} {r.text.strip()}"

def load_users_from_file(path: str) -> List[Dict[str, Any]]:
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "users" in data and isinstance(data["users"], list):
            return data["users"]
        raise ValueError("JSON attendu: liste d'utilisateurs ou {users:[...]}")
    import csv
    users = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            users.append({
                "email": (row.get("email") or "").strip(),
                "password": (row.get("password") or "").strip(),
                "full_name": (row.get("full_name") or "").strip(),
                "role": (row.get("role") or "").strip(),
            })
    return users

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-url", default="http://localhost:8000", help="Service qui délivre le token (login)")
    ap.add_argument("--api-url", default="http://localhost:8001", help="Service cible pour register/list/delete users")
    ap.add_argument("--timeout", type=int, default=10)
    ap.add_argument("--users-file", default="", help="Optionnel: fichier JSON/CSV d'utilisateurs")

    ap.add_argument("--cleanup", action="store_true", help="Supprimer d'abord les utilisateurs existants ayant les mêmes emails")
    ap.add_argument("--email", default="", help="Email admin pour récupérer le token")
    ap.add_argument("--password", default="", help="Mot de passe admin")

    ap.add_argument("--register-path", default="/api/auth/register", help="Path register sur api-url")
    ap.add_argument("--list-users-path", default="/api/auth/users/list", help="Path liste users sur api-url")
    ap.add_argument("--delete-user-path", default="/api/auth/users/{user_id}", help="Path delete user sur api-url")

    ap.add_argument("--skip-duplicates", action="store_true", help="Ne pas afficher comme erreur si 'Email déjà utilisé'")
    args = ap.parse_args()

    users = load_users_from_file(args.users_file) if args.users_file else DEFAULT_USERS
    users = [u for u in users if u.get("email") and u.get("password") and u.get("full_name") and u.get("role")]
    if not users:
        print("Aucun utilisateur valide à créer.", file=sys.stderr)
        return 2

    # Token via auth-url
    token = None
    if args.email and args.password:
        try:
            token = login(args.auth_url, args.email, args.password, args.timeout)
            print("🔑 Auth OK (token récupéré)")
        except Exception as ex:
            print(f"❌ Auth KO: {ex}", file=sys.stderr)
            return 1
    else:
        # Certains services autorisent register sans token. On continue sans.
        print("⚠️ Pas de --email/--password admin fournis: register sera tenté sans token. Cleanup désactivé.", file=sys.stderr)
        args.cleanup = False

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # Cleanup via api-url
    if args.cleanup:
        try:
            all_users = list_users(args.api_url, args.list_users_path, headers, args.timeout)
        except Exception as ex:
            print(f"⚠️ Cleanup ignoré: impossible de lister les users sur {args.api_url}{args.list_users_path}: {ex}", file=sys.stderr)
        else:
            by_email = {(u.get("email") or "").lower(): u for u in all_users if isinstance(u, dict)}
            for u in users:
                e = u["email"].lower()
                if e in by_email:
                    obj = by_email[e]
                    uid = obj.get("id") or obj.get("user_id") or obj.get("uuid")
                    if not uid:
                        print(f"⚠️ ID introuvable pour {u['email']}, suppression ignorée.")
                        continue
                    ok, msg = delete_user(args.api_url, args.delete_user_path, str(uid), headers, args.timeout)
                    print(("🗑️ Supprimé" if ok else "⚠️ Delete KO") + f" {u['email']}: {msg}")

    # Create via api-url
    created = 0
    for u in users:
        ok, msg = register(args.api_url, args.register_path, u, headers, args.timeout)
        if ok:
            created += 1
            print(f"✅ Créé: {u['email']} ({u['role']})")
        else:
            if args.skip_duplicates and ("déjà utilisé" in msg.lower() or "already" in msg.lower()):
                print(f"↩️ Existe déjà: {u['email']} ({u['role']})")
            else:
                print(f"⚠️ Non créé: {u['email']} ({u['role']}): {msg}")

    print(f"Terminé. Créés: {created}/{len(users)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
