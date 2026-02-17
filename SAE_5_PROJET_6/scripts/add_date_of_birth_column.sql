-- Migration pour ajouter la colonne date_of_birth à la table patients
-- Exécuter cette commande dans la base de données PostgreSQL

-- Ajouter la colonne date_of_birth à la table patients
ALTER TABLE patients ADD COLUMN IF NOT EXISTS date_of_birth DATE;

-- Mettre à jour les patients existants avec des dates de naissance par défaut
UPDATE patients SET date_of_birth = '1980-01-01' WHERE date_of_birth IS NULL AND full_name LIKE '%Jean%';
UPDATE patients SET date_of_birth = '1975-01-01' WHERE date_of_birth IS NULL AND full_name LIKE '%Marie%';
UPDATE patients SET date_of_birth = '1990-01-01' WHERE date_of_birth IS NULL AND full_name LIKE '%Robert%';

-- Afficher les patients mis à jour
SELECT id, full_name, date_of_birth, age, gender FROM patients;
