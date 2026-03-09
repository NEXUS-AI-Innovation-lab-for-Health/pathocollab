export async function createPatientFromDynamicForm(formId, data) {
    const response = await fetch("http://localhost:8000/api/patients/from-form", {
        method: "POST",
        headers: {
        "Content-Type": "application/json",
        },
        body: JSON.stringify({
        form_id: formId,
        data,
        }),
    });

    const result = await response.json();

    if (!response.ok) {
        throw new Error(result.detail || "Erreur lors de la création du patient");
    }

    return result;
}