#!/bin/bash

API_URL="http://localhost:8000/api/auth/register"

create_user() {
email="$1"
password="$2"
full_name="$3"
role="$4"

curl -s -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$email\",
        \"password\": \"$password\",
        \"full_name\": \"$full_name\",
        \"role\": \"$role\"
    }"

    echo    # juste une ligne vide
}

# === Liste des utilisateurs à créer ===
create_user "admin@gmail.com" "admin" "Admin" "admin"
create_user "arthur@gmail.com" "arthur" "Dr. Arthur" "anatomopathologiste"
create_user "louna@gamil.com" "louna" "Dr. Louna" "anatomopathologiste"
create_user "jack@gamil.com" "jack" "Dr. Jack" "oncologue"
