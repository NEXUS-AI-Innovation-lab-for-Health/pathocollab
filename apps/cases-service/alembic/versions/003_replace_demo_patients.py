from alembic import op
import sqlalchemy as sa
from datetime import datetime, date, timezone

revision = "003_replace_demo_patients"
down_revision = "002_seed_patients"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Supprime les anciens patients de test
    conn.execute(sa.text("""
        DELETE FROM patients
        WHERE id IN (
            'PAT-azer1234',
            'PAT-qsdf5678',
            'PAT-wxcv7412',
            'PAT-tyui8569',
            'PAT-ghjk7613'
        )
    """))

    patients = [
        ("PAT001", "Matthieu Ferreira", date(1963, 7, 26), "F"),
        ("PAT002", "Thibaut Blot", date(1970, 12, 24), "M"),
        ("PAT003", "Susan Brunet", date(1955, 6, 7), "F"),
        ("PAT004", "Renée Guillot", date(1995, 11, 14), "M"),
        ("PAT005", "Olivier Joly", date(1973, 2, 21), "M"),
        ("PAT006", "Frédérique Bousquet", date(1962, 12, 10), "M"),
        ("PAT007", "Zacharie Rossi", date(1984, 2, 2), "F"),
        ("PAT008", "Danielle Barre", date(1954, 9, 30), "M"),
        ("PAT009", "Célina Gomes", date(1983, 6, 18), "F"),
        ("PAT010", "Alice Fournier", date(1956, 12, 3), "M"),
    ]

    for patient_id, full_name, dob, gender in patients:
        age = datetime.now().year - dob.year

        conn.execute(sa.text("""
            INSERT INTO patients (
                id, full_name, age, gender, date_of_birth,
                medical_history, symptoms, imaging_notes,
                created_at, updated_at
            )
            VALUES (
                :id, :full_name, :age, :gender, :date_of_birth,
                '', '', '',
                :created_at, :updated_at
            )
            ON CONFLICT (id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                age = EXCLUDED.age,
                gender = EXCLUDED.gender,
                date_of_birth = EXCLUDED.date_of_birth,
                updated_at = EXCLUDED.updated_at
        """), {
            "id": patient_id,
            "full_name": full_name,
            "age": age,
            "gender": gender,
            "date_of_birth": dob,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
        })


def downgrade():
    conn = op.get_bind()
    conn.execute(sa.text("""
        DELETE FROM patients
        WHERE id LIKE 'PAT0%'
    """))