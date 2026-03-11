from alembic import op
import sqlalchemy as sa
import uuid
from datetime import datetime, date, timezone

revision = "002_seed_patients"
down_revision = "001_initial_migration"
branch_labels = None
depends_on = None


def upgrade():

    conn = op.get_bind()

    patients = [
        {
            "id": f"PAT-azer1234",
            "full_name": "Jean Dupont",
            "age": 54,
            "gender": "Homme",
            "date_of_birth": date(1970, 5, 12),
            "medical_history": "Hypertension",
            "symptoms": "Douleur thoracique",
            "imaging_notes": "Suspicion de tumeur pulmonaire",
        },
        {
            "id": f"PAT-qsdf5678",
            "full_name": "Marie Martin",
            "age": 63,
            "gender": "Femme",
            "date_of_birth": date(1961, 3, 2),
            "medical_history": "Diabète type 2",
            "symptoms": "Fatigue persistante",
            "imaging_notes": "Anomalie hépatique",
        },
        {
            "id": f"PAT-wxcv7412",
            "full_name": "Paul Durand",
            "age": 47,
            "gender": "Homme",
            "date_of_birth": date(1977, 11, 23),
            "medical_history": "Tabagisme",
            "symptoms": "Toux chronique",
            "imaging_notes": "Nodule pulmonaire",
        },
        {
            "id": f"PAT-tyui8569",
            "full_name": "Sophie Bernard",
            "age": 38,
            "gender": "Femme",
            "date_of_birth": date(1986, 8, 15),
            "medical_history": "Asthme",
            "symptoms": "Essoufflement",
            "imaging_notes": "Inflammation bronchique",
        },
        {
            "id": f"PAT-ghjk7613",
            "full_name": "Luc Moreau",
            "age": 71,
            "gender": "Homme",
            "date_of_birth": date(1953, 1, 30),
            "medical_history": "Cancer antérieur",
            "symptoms": "Perte de poids",
            "imaging_notes": "Masse suspecte abdominale",
        },
    ]

    for patient in patients:
        conn.execute(
            sa.text(
                """
                INSERT INTO patients (
                    id,
                    full_name,
                    age,
                    gender,
                    date_of_birth,
                    medical_history,
                    symptoms,
                    imaging_notes,
                    created_at,
                    updated_at
                )
                VALUES (
                    :id,
                    :full_name,
                    :age,
                    :gender,
                    :date_of_birth,
                    :medical_history,
                    :symptoms,
                    :imaging_notes,
                    :created_at,
                    :updated_at
                )
                """
            ),
            {
                **patient,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            },
        )


def downgrade():

    conn = op.get_bind()

    conn.execute(
        sa.text(
            """
            DELETE FROM patients
            WHERE full_name IN (
                'Jean Dupont',
                'Marie Martin',
                'Paul Durand',
                'Sophie Bernard',
                'Luc Moreau'
            )
            """
        )
    )