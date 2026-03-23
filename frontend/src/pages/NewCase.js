import React, { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { X, ChevronUp, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { getCurrentUser } from "@/services/auth";

const AUTH_API =
  process.env.REACT_APP_AUTH_SERVICE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8001`;

const CASES_API =
  process.env.REACT_APP_CASES_SERVICE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8002`;

const WORKFLOW_API =
  process.env.REACT_APP_WORKFLOW_SERVICE_URL ||
  `${window.location.protocol}//${window.location.hostname}:8003`;

const OLGA_API =
  process.env.REACT_APP_OLGA_API ||
  `${window.location.protocol}//${window.location.hostname}:9091`;

function normalizeKey(key = "") {
  return String(key)
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function buildDefaultValuesFromOlgaForm(form) {
  const values = {};
  (form?.form || []).forEach((field) => {
    const type = String(field?.field_type || "").toLowerCase();
    if (type.includes("checkbox")) {
      values[field.field_key] = false;
    } else {
      values[field.field_key] = "";
    }
  });
  return values;
}

function getFieldOptions(field) {
  return (
    field?.options ||
    field?.field_options?.options ||
    field?.field_options?.values?.map((v) => ({
      label: v,
      value: v,
    })) ||
    []
  );
}

const NewCase = () => {
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [specialists, setSpecialists] = useState([]);
  const [selectedSpecialists, setSelectedSpecialists] = useState([]);
  const [specialistsLoading, setSpecialistsLoading] = useState(false);
  const [specialistsError, setSpecialistsError] = useState(null);

  const [submitting, setSubmitting] = useState(false);

  const [olgaForm, setOlgaForm] = useState(null);
  const [olgaLoading, setOlgaLoading] = useState(true);
  const [olgaError, setOlgaError] = useState(null);
  const [formValues, setFormValues] = useState({});

  useEffect(() => {
    loadOlgaForm();
    loadSpecialists();
    fetchPatients();
  }, []);

  const patientField = useMemo(
    () =>
      (olgaForm?.form || []).find((field) =>
        ["patient_id", "patientid"].includes(normalizeKey(field.field_key))
      ),
    [olgaForm]
  );

  const specialistField = useMemo(
    () =>
      (olgaForm?.form || []).find((field) =>
        ["specialiste_id", "specialist_id", "specialisteid", "specialistid"].includes(
          normalizeKey(field.field_key)
        )
      ),
    [olgaForm]
  );

  const priorityField = useMemo(
    () =>
      (olgaForm?.form || []).find((field) =>
        ["priorite", "priority"].includes(normalizeKey(field.field_key))
      ),
    [olgaForm]
  );

  const notesField = useMemo(
    () =>
      (olgaForm?.form || []).find((field) =>
        ["notes", "description", "commentaire", "commentaires"].includes(
          normalizeKey(field.field_key)
        )
      ),
    [olgaForm]
  );

  async function loadOlgaForm() {
    try {
      setOlgaLoading(true);
      setOlgaError(null);

      const response = await fetch(
        `${OLGA_API}/forms/getFromID/creationCasPathoCollab`
      );

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`Erreur Olga ${response.status}: ${text}`);
      }

      const data = await response.json();
      setOlgaForm(data);
      setFormValues(buildDefaultValuesFromOlgaForm(data));
    } catch (error) {
      console.error("Erreur chargement formulaire Olga:", error);
      setOlgaError("Impossible de charger le formulaire Olga.");
      setOlgaForm(null);
    } finally {
      setOlgaLoading(false);
    }
  }

  async function loadSpecialists() {
    setSpecialistsLoading(true);
    setSpecialistsError(null);

    try {
      const token = localStorage.getItem("access_token");

      const res = await axios.get(`${AUTH_API}/api/auth/specialists/`, {
        headers: {
          Authorization: `Bearer ${token}`,
          Accept: "application/json",
        },
      });

      const list = Array.isArray(res.data) ? res.data : res.data?.items ?? [];

      const normalized = list.map((s) => ({
        id: String(s.id ?? s.user_id ?? s.uuid ?? ""),
        name: s.full_name ?? s.name ?? s.username ?? s.email ?? "Spécialiste",
        email: s.email ?? s.mail ?? "",
        specialty: s.role ?? s.specialty ?? s.job ?? "",
      }));

      setSpecialists(normalized);
    } catch (e) {
      console.error("Erreur chargement spécialistes:", e);
      setSpecialistsError(e?.response?.data ?? e.message);
      toast.error("Erreur lors du chargement des spécialistes");
    } finally {
      setSpecialistsLoading(false);
    }
  }

  async function fetchPatients() {
    try {
      const token = localStorage.getItem("access_token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await axios.get(`${CASES_API}/api/patients/list`, {
        headers,
      });

      setPatients(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error("Error fetching patients:", error);

      if (error.response?.status === 401) {
        toast.error("Erreur d'authentification. Veuillez vous reconnecter.");
      } else if (error.response?.status === 404) {
        toast.error(
          "Endpoint patients non trouvé. Le service est-il bien configuré ?"
        );
      } else {
        toast.error(`Erreur lors du chargement des patients: ${error.message}`);
      }
    } finally {
      setLoadingPatients(false);
    }
  }

  function setFieldValue(key, value) {
    setFormValues((prev) => ({
      ...prev,
      [key]: value,
    }));
  }

  function addSpecialist(specialistId) {
    if (!specialistId) return;

    const specialist = specialists.find(
      (s) => String(s.id) === String(specialistId)
    );

    if (
      specialist &&
      !selectedSpecialists.some((s) => String(s.id) === String(specialist.id))
    ) {
      setSelectedSpecialists((prev) => [...prev, specialist]);

      if (specialistField?.field_key) {
        setFieldValue(specialistField.field_key, "");
      }
    }
  }

  function removeSpecialist(specialistId) {
    setSelectedSpecialists((prev) =>
      prev.filter((s) => String(s.id) !== String(specialistId))
    );
  }

  function moveSpecialist(index, direction) {
    const newSpecialists = [...selectedSpecialists];
    const temp = newSpecialists[index];

    if (direction === "up" && index > 0) {
      newSpecialists[index] = newSpecialists[index - 1];
      newSpecialists[index - 1] = temp;
    } else if (direction === "down" && index < newSpecialists.length - 1) {
      newSpecialists[index] = newSpecialists[index + 1];
      newSpecialists[index + 1] = temp;
    }

    setSelectedSpecialists(newSpecialists);
  }

  function getPatientOptions() {
    return patients.map((patient) => ({
      label: `${patient.full_name} - ${
        patient.date_of_birth
          ? new Date(patient.date_of_birth).toLocaleDateString("fr-FR")
          : "Date inconnue"
      }`,
      value: String(patient.id),
    }));
  }

  function getSpecialistOptions() {
    return specialists
      .filter(
        (s) =>
          !selectedSpecialists.some((sel) => String(sel.id) === String(s.id))
      )
      .map((specialist) => ({
        label: specialist.specialty
          ? `${specialist.name} - ${specialist.specialty}`
          : specialist.name,
        value: String(specialist.id),
      }));
  }

  function getOptionsForField(field) {
    const key = normalizeKey(field?.field_key);

    if (["patient_id", "patientid"].includes(key)) {
      return getPatientOptions();
    }

    if (
      ["specialiste_id", "specialist_id", "specialisteid", "specialistid"].includes(
        key
      )
    ) {
      return getSpecialistOptions();
    }

    return getFieldOptions(field).map((opt) => ({
      label: opt?.label ?? opt?.value ?? "",
      value: String(opt?.value ?? opt?.label ?? ""),
    }));
  }

  async function handleSubmit(e) {
    e.preventDefault();

    if (!selectedPatient) {
      toast.error("Veuillez sélectionner un patient");
      return;
    }

    if (selectedSpecialists.length === 0) {
      toast.error("Veuillez sélectionner au moins un spécialiste");
      return;
    }

    try {
      setSubmitting(true);

      const currentUser = await getCurrentUser();
      const userName =
        currentUser?.fullName ||
        currentUser?.full_name ||
        currentUser?.name ||
        "Utilisateur inconnu";

      const priorityValue = priorityField?.field_key
        ? formValues[priorityField.field_key] || null
        : null;

      const notesValue = notesField?.field_key
        ? formValues[notesField.field_key] || ""
        : "";

      const description = [
        notesValue?.trim() || "",
        priorityValue ? `Priorité: ${priorityValue}` : "",
      ]
        .filter(Boolean)
        .join("\n\n");

      const caseData = {
        patient_id: selectedPatient.id,
        title: `Cas pour ${selectedPatient.full_name}`,
        description,
        status: "pending",
        created_by: userName,
        assigned_specialists: selectedSpecialists.map((s) => s.email),
      };

      const response = await axios.post(
        `${CASES_API}/api/cases/create/`,
        caseData,
        {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        }
      );

      const workflowData = {
        case_id: response.data.id,
        specialists_order: selectedSpecialists.map((s) => s.email),
      };

      await axios.post(`${WORKFLOW_API}/api/workflows/`, workflowData, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      toast.success("Cas créé avec succès");
      navigate("/dashboard");
    } catch (error) {
      console.error("Erreur lors de la création du cas:", error);
      toast.error("Une erreur est survenue lors de la création du cas");
    } finally {
      setSubmitting(false);
    }
  }

  function renderField(field) {
    const type = String(field?.field_type || "").toLowerCase();
    const key = field.field_key;
    const normalizedKey = normalizeKey(key);
    const label = field?.field_label || key;
    const value = formValues[key] ?? "";

    if (type.includes("select")) {
      const options = getOptionsForField(field);

      const isPatientField = ["patient_id", "patientid"].includes(normalizedKey);
      const isSpecialistField = [
        "specialiste_id",
        "specialist_id",
        "specialisteid",
        "specialistid",
      ].includes(normalizedKey);

      return (
        <div key={field.unique_id || key}>
          <Label htmlFor={key}>{label}</Label>
          <Select
            value={value}
            onValueChange={(selectedValue) => {
              setFieldValue(key, selectedValue);

              if (isPatientField) {
                const patient =
                  patients.find(
                    (p) => String(p.id) === String(selectedValue)
                  ) || null;
                setSelectedPatient(patient);
              }

              if (isSpecialistField) {
                addSpecialist(selectedValue);
              }
            }}
          >
            <SelectTrigger className="w-full mt-2">
              <SelectValue
                placeholder={
                  isPatientField && loadingPatients
                    ? "Chargement des patients..."
                    : isSpecialistField && specialistsLoading
                    ? "Chargement des spécialistes..."
                    : `Sélectionner ${label.toLowerCase()}`
                }
              />
            </SelectTrigger>

            <SelectContent>
              {isPatientField && loadingPatients ? (
                <SelectItem value="loading" disabled>
                  Chargement des patients...
                </SelectItem>
              ) : isSpecialistField && specialistsLoading ? (
                <SelectItem value="loading" disabled>
                  Chargement des spécialistes...
                </SelectItem>
              ) : isSpecialistField && specialistsError ? (
                <SelectItem value="error" disabled>
                  Erreur de chargement
                </SelectItem>
              ) : options.length === 0 ? (
                <SelectItem value="empty" disabled>
                  Aucune option disponible
                </SelectItem>
              ) : (
                options.map((opt) => (
                  <SelectItem key={`${key}-${opt.value}`} value={String(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>

          {isPatientField && selectedPatient && (
            <div className="mt-4 p-4 border rounded-lg bg-gray-50">
              <h3 className="font-medium">Patient sélectionné</h3>
              <p className="text-sm text-gray-700">
                {selectedPatient.full_name}
              </p>
              <p className="text-xs text-gray-500">
                Date de naissance :{" "}
                {selectedPatient.date_of_birth
                  ? new Date(selectedPatient.date_of_birth).toLocaleDateString(
                      "fr-FR"
                    )
                  : "Non renseignée"}
              </p>
            </div>
          )}
        </div>
      );
    }

    if (type.includes("textarea")) {
      return (
        <div key={field.unique_id || key}>
          <Label htmlFor={key}>{label}</Label>
          <textarea
            id={key}
            className="w-full mt-2 p-3 border rounded-md min-h-[120px]"
            placeholder={field?.field_hint || `Entrer ${label.toLowerCase()}...`}
            value={value}
            onChange={(e) => setFieldValue(key, e.target.value)}
          />
        </div>
      );
    }

    if (type.includes("checkbox")) {
      return (
        <div key={field.unique_id || key} className="flex items-center gap-2">
          <input
            id={key}
            type="checkbox"
            checked={!!value}
            onChange={(e) => setFieldValue(key, e.target.checked)}
          />
          <Label htmlFor={key}>{label}</Label>
        </div>
      );
    }

    return (
      <div key={field.unique_id || key}>
        <Label htmlFor={key}>{label}</Label>
        <input
          id={key}
          type="text"
          className="w-full mt-2 p-3 border rounded-md"
          placeholder={field?.field_hint || `Entrer ${label.toLowerCase()}...`}
          value={value}
          onChange={(e) => setFieldValue(key, e.target.value)}
        />
      </div>
    );
  }

  return (
    <div className="container mx-auto max-w-5xl p-6">
      <div className="flex items-center mb-6">
        <Button variant="ghost" onClick={() => navigate(-1)} className="mr-4">
          &larr; Retour
        </Button>
        <h1 className="text-2xl font-bold">Nouveau cas</h1>
      </div>

      <form onSubmit={handleSubmit}>
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Création d’un nouveau cas</CardTitle>
          </CardHeader>

          <CardContent>
            {olgaLoading ? (
              <p className="text-sm text-gray-500">
                Chargement du formulaire Olga...
              </p>
            ) : olgaError ? (
              <p className="text-sm text-red-500">{olgaError}</p>
            ) : !olgaForm?.form?.length ? (
              <p className="text-sm text-gray-500">
                Aucun champ trouvé dans le formulaire Olga.
              </p>
            ) : (
              <div className="space-y-8">
                {olgaForm.form.map((field) => renderField(field))}

                <div>
                  <Label>Ordre de passage des spécialistes</Label>
                  <div className="space-y-2 mt-2">
                    {selectedSpecialists.length > 0 ? (
                      selectedSpecialists.map((specialist, index) => (
                        <div
                          key={specialist.id}
                          className="flex items-center justify-between p-3 border rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{specialist.name}</p>
                            <p className="text-sm text-gray-500">
                              {specialist.specialty || specialist.email}
                            </p>
                          </div>

                          <div className="flex space-x-2">
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => moveSpecialist(index, "up")}
                              disabled={index === 0}
                            >
                              <ChevronUp className="h-4 w-4" />
                            </Button>

                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => moveSpecialist(index, "down")}
                              disabled={index === selectedSpecialists.length - 1}
                            >
                              <ChevronDown className="h-4 w-4" />
                            </Button>

                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              onClick={() => removeSpecialist(specialist.id)}
                            >
                              <X className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </div>
                      ))
                    ) : (
                      <p className="text-sm text-gray-500">
                        Aucun spécialiste sélectionné
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    type="submit"
                    disabled={
                      !selectedPatient ||
                      selectedSpecialists.length === 0 ||
                      submitting
                    }
                  >
                    {submitting ? "Création..." : "Créer le cas"}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </form>
    </div>
  );
};

export default NewCase;