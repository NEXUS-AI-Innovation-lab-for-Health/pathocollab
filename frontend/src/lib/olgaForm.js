export async function fetchOlgaForm(formId) {
    const response = await fetch(`http://localhost:8000/api/forms/olga/${formId}`);

    if (!response.ok) {
        throw new Error("Impossible de récupérer le formulaire Olga");
    }

    return response.json();
}