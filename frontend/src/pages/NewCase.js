import React, { useState, useEffect } from "react";
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

const NewCase = () => {
  const navigate = useNavigate();

  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);

  const [specialists, setSpecialists] = useState([]);
  const [selectedSpecialists, setSelectedSpecialists] = useState([]);
  const [specialistsLoading, setSpecialistsLoading] = useState(false);
  const [specialistsError, setSpecialistsError] = useState(null);

  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const loadSpecialists = async () => {
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
        setSpecialistsError(e?.response?.data ?? e.message);
        toast.error("Erreur lors du chargement des spécialistes");
      } finally {
        setSpecialistsLoading(false);
      }
    };

    loadSpecialists();
  }, []);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const token = localStorage.getItem("access_token");
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await axios.get(`${CASES_API}/api/patients/list`, {
        headers,
      });

      setPatients(response.data);
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
  };

  const addSpecialist = (specialistId) => {
    if (!specialistId) return;

    const specialist = specialists.find(
      (s) => String(s.id) === String(specialistId)
    );

    if (
      specialist &&
      !selectedSpecialists.some((s) => String(s.id) === String(specialist.id))
    ) {
      setSelectedSpecialists((prev) => [...prev, specialist]);
    }
  };

  const removeSpecialist = (specialistId) => {
    setSelectedSpecialists((prev) =>
      prev.filter((s) => String(s.id) !== String(specialistId))
    );
  };

  const moveSpecialist = (index, direction) => {
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
  };

  const handleSubmit = async (e) => {
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
      const userName = currentUser?.fullName || "Utilisateur inconnu";

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
  };

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
            <div className="space-y-8">
              <div>
                <Label htmlFor="patient">Patient</Label>
                <Select
                  onValueChange={(value) =>
                    setSelectedPatient(
                      patients.find((p) => String(p.id) === String(value)) ||
                        null
                    )
                  }
                >
                  <SelectTrigger className="w-full mt-2">
                    <SelectValue placeholder="Sélectionner un patient" />
                  </SelectTrigger>

                  <SelectContent>
                    {loadingPatients ? (
                      <SelectItem value="loading" disabled>
                        Chargement des patients...
                      </SelectItem>
                    ) : patients.length === 0 ? (
                      <SelectItem value="empty" disabled>
                        Aucun patient trouvé
                      </SelectItem>
                    ) : (
                      patients.map((patient) => (
                        <SelectItem key={patient.id} value={String(patient.id)}>
                          {patient.full_name} -{" "}
                          {patient.date_of_birth
                            ? new Date(patient.date_of_birth).toLocaleDateString(
                                "fr-FR"
                              )
                            : "Date inconnue"}
                        </SelectItem>
                      ))
                    )}
                  </SelectContent>
                </Select>

                {selectedPatient && (
                  <div className="mt-4 p-4 border rounded-lg bg-gray-50">
                    <h3 className="font-medium">Patient sélectionné</h3>
                    <p className="text-sm text-gray-700">
                      {selectedPatient.full_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Date de naissance :{" "}
                      {selectedPatient.date_of_birth
                        ? new Date(
                            selectedPatient.date_of_birth
                          ).toLocaleDateString("fr-FR")
                        : "Non renseignée"}
                    </p>
                  </div>
                )}
              </div>

              <div>
                <Label htmlFor="specialist">Ajouter un spécialiste</Label>
                <div className="mt-2">
                  <Select onValueChange={addSpecialist}>
                    <SelectTrigger className="w-full">
                      <SelectValue
                        placeholder={
                          specialistsLoading
                            ? "Chargement des spécialistes..."
                            : "Sélectionner un spécialiste"
                        }
                      />
                    </SelectTrigger>

                    <SelectContent>
                      {specialistsLoading ? (
                        <SelectItem value="loading" disabled>
                          Chargement...
                        </SelectItem>
                      ) : specialistsError ? (
                        <SelectItem value="error" disabled>
                          Erreur de chargement
                        </SelectItem>
                      ) : specialists.filter(
                          (s) =>
                            !selectedSpecialists.some(
                              (sel) => String(sel.id) === String(s.id)
                            )
                        ).length === 0 ? (
                        <SelectItem value="empty" disabled>
                          Aucun spécialiste disponible
                        </SelectItem>
                      ) : (
                        specialists
                          .filter(
                            (s) =>
                              !selectedSpecialists.some(
                                (sel) => String(sel.id) === String(s.id)
                              )
                          )
                          .map((specialist) => (
                            <SelectItem
                              key={specialist.id}
                              value={String(specialist.id)}
                            >
                              {specialist.name}
                              {specialist.specialty
                                ? ` - ${specialist.specialty}`
                                : ""}
                            </SelectItem>
                          ))
                      )}
                    </SelectContent>
                  </Select>
                </div>
              </div>

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

              <div>
                <Label htmlFor="description">Notes supplémentaires</Label>
                <textarea
                  id="description"
                  className="w-full mt-2 p-3 border rounded-md min-h-[120px]"
                  placeholder="Ajoutez des notes ou des instructions pour les spécialistes..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
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
          </CardContent>
        </Card>
      </form>
    </div>
  );
};

export default NewCase;