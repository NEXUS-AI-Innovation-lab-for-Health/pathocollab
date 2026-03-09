import React from "react";

const FIELD_LABELS = {
    id: "Identifiant",
    nom: "Nom",
    prenom: "Prénom",
    age: "Âge",
    naissance: "Date de naissance",
    sexe: "Sexe",
    historique: "Historique",
    symptome: "Symptôme",
    notes: "Notes",
};

function getLabel(field) {
    if (field.field_label && field.field_label.trim() !== "") {
        return field.field_label;
    }
    return FIELD_LABELS[field.field_key] || field.field_key;
}

export default function OlgaFormRenderer({schema, values, errors, onChange, onSubmit, loading,}) {
    const renderField = (field) => {
        const key = field.field_key;
        const required = field.field_required;
        const value = values[key] || "";
        const label = getLabel(field);

        if (field.field_type === "input:text") {
        return (
            <div key={field.unique_id} style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", marginBottom: 6 }}>
                    {label} {required ? "*" : ""}
                </label>
                <input
                    type="text"
                    value={value}
                    onChange={(e) => onChange(key, e.target.value)}
                    required={required}
                    style={{ width: "100%", padding: "10px" }}
                />
                {errors[key] && (
                    <div style={{ color: "red", marginTop: 4 }}>{errors[key]}</div>
                )}
            </div>
        );
        }

        if (field.field_type === "datepicker") {
        return (
            <div key={field.unique_id} style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", marginBottom: 6 }}>
                    {label} {required ? "*" : ""}
                </label>
                <input
                    type="date"
                    value={value}
                    onChange={(e) => onChange(key, e.target.value)}
                    required={required}
                    style={{ width: "100%", padding: "10px" }}
                />
                {errors[key] && (
                    <div style={{ color: "red", marginTop: 4 }}>{errors[key]}</div>
                )}
            </div>
        );
        }

        return (
        <div key={field.unique_id} style={{ marginBottom: "16px" }}>
            <p>Type non supporté : {field.field_type}</p>
        </div>
        );
    };

    return (
        <form
            onSubmit={onSubmit}
            style={{
                maxWidth: 700,
                margin: "0 auto",
                padding: 24,
                border: "1px solid #ddd",
                borderRadius: 12,
            }}
        >
        <h2 style={{ marginBottom: 24 }}>{schema.form_label}</h2>

        {schema.form.map(renderField)}

        <button
            type="submit"
            disabled={loading}
            style={{
            padding: "12px 18px",
            borderRadius: 8,
            border: "none",
            cursor: "pointer",
            }}
        >
            {loading ? "Enregistrement..." : "Créer le patient"}
        </button>
        </form>
    );
}