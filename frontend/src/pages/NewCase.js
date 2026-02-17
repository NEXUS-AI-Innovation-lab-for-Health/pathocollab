import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, X, ChevronUp, ChevronDown, Upload } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { getCurrentUser } from "@/services/auth";


const CASES_API = process.env.REACT_APP_CASES_SERVICE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;
const WORKFLOW_API = process.env.REACT_APP_WORKFLOW_SERVICE_URL || `${window.location.protocol}//${window.location.hostname}:8000`;

const NewCase = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [patients, setPatients] = useState([]);
  const [loadingPatients, setLoadingPatients] = useState(true);
  const [selectedPatient, setSelectedPatient] = useState(null);
  const [patientImages, setPatientImages] = useState([
    {
      id: 1,
      name: "radio1.jpg",
      date: "10/11/2023",
      type: "Radio panoramique",
    },
    { id: 2, name: "radio2.jpg", date: "10/11/2023", type: "Radio latérale" },
  ]);
  const [selectedImages, setSelectedImages] = useState([]);
  const [specialists, setSpecialists] = useState([
    { id: 1, name: "Dr. Smith", specialty: "Orthodontiste" },
    { id: 2, name: "Dr. Johnson", specialty: "Chirurgien maxillo-facial" },
    { id: 3, name: "Dr. Williams", specialty: "Pédodontiste" },
  ]);
  const [selectedSpecialists, setSelectedSpecialists] = useState([]);
  const [description, setDescription] = useState("");





  const handleImageSelect = (imageId) => {
    setSelectedImages((prev) =>
      prev.includes(imageId)
        ? prev.filter((id) => id !== imageId)
        : [...prev, imageId],
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

  const addSpecialist = (specialistId) => {
    if (!specialistId) return; // Vérifier si l'ID est défini
    const specialist = specialists.find((s) => s.id === parseInt(specialistId));
    if (
      specialist &&
      !selectedSpecialists.some((s) => s.id === specialist.id)
    ) {
      setSelectedSpecialists([...selectedSpecialists, specialist]);
    }
  };

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const token = localStorage.getItem("access_token");
      console.log("Fetching patients with token:", token);
      const headers = token ? { Authorization: `Bearer ${token}` } : {};

      const response = await axios.get(`${CASES_API}/api/patients/`, {
        headers: headers,
      });
      setPatients(response.data);
      console.log("Patients chargés:", response.data);
    } catch (error) {
      console.error("Error fetching patients:", error);
      if (error.response?.status === 401) {
        toast.error("Erreur d'authentification. Veuillez vous reconnecter.");
      } else if (error.response?.status === 404) {
        toast.error(
          "Endpoint patients non trouvé. Le service est-il bien configuré ?",
        );
      } else {
        toast.error(`Erreur lors du chargement des patients: ${error.message}`);
      }
    } finally {
      setLoadingPatients(false);
    }
  };

  const removeSpecialist = (specialistId) => {
    setSelectedSpecialists(
      selectedSpecialists.filter((s) => s.id !== specialistId),
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!selectedPatient || selectedSpecialists.length === 0) {
      toast.error(
        "Veuillez sélectionner un patient et au moins un spécialiste",
      );
      return;
    }

    try {
      // Récupérer l'utilisateur connecté
      const currentUser = await getCurrentUser();
      const userName = currentUser
        ? currentUser.fullName
        : "Utilisateur inconnu";

      // Préparer les données du cas
      const caseData = {
        patient_id: selectedPatient.id,
        title: `Cas pour ${selectedPatient.full_name}`,
        description: description,
        status: "pending",
        created_by: userName,
        assigned_specialists: selectedSpecialists.map((s) => s.name),
      };

      // Envoyer au Cases Service
      const response = await axios.post(`${CASES_API}/api/cases/`, caseData, { headers });


      // Créer le workflow pour ce cas
      const workflowData = {
        case_id: response.data.id,
        specialists_order: selectedSpecialists.map((s) => {
          // Mapper les noms vers les emails
          if (s.name === "Dr. Smith") return "dr.smith@pixtral.fr";
          if (s.name === "Dr. Johnson") return "dr.johnson@pixtral.fr";
          if (s.name === "Dr. Williams") return "dr.williams@pixtral.fr";
          return s.name; // Fallback
        }),
      };

      await axios.post(`${WORKFLOW_API}/api/workflows`, workflowData, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      toast.success("Cas créé avec succès !");
      navigate("/dashboard");
    } catch (error) {
      console.error("Erreur lors de la création du cas:", error);
      toast.error("Une erreur est survenue lors de la création du cas");
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center mb-6">
        <Button variant="ghost" onClick={() => navigate(-1)} className="mr-4">
          &larr; Retour
        </Button>
        <h1 className="text-2xl font-bold">Nouveau cas</h1>
      </div>

      <div className="flex space-x-4 mb-6">
        <div
          className={`flex items-center ${
            step >= 1 ? "text-blue-600" : "text-gray-400"
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 1 ? "bg-blue-100" : "bg-gray-100"
            }`}
          >
            1
          </div>
          <span className="ml-2">Patient</span>
        </div>
        <div
          className="flex-1 border-t-2 mt-4"
          style={{ borderColor: step >= 2 ? "#2563eb" : "#e5e7eb" }}
        ></div>
        <div
          className={`flex items-center ${
            step >= 2 ? "text-blue-600" : "text-gray-400"
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 2 ? "bg-blue-100" : "bg-gray-100"
            }`}
          >
            2
          </div>
          <span className="ml-2">Images</span>
        </div>
        <div
          className="flex-1 border-t-2 mt-4"
          style={{ borderColor: step >= 3 ? "#2563eb" : "#e5e7eb" }}
        ></div>
        <div
          className={`flex items-center ${
            step >= 3 ? "text-blue-600" : "text-gray-400"
          }`}
        >
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center ${
              step >= 3 ? "bg-blue-100" : "bg-gray-100"
            }`}
          >
            3
          </div>
          <span className="ml-2">Spécialistes</span>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {step === 1 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Sélection du patient</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <Label htmlFor="patient">Rechercher un patient</Label>
                  <Select
                    onValueChange={(value) =>
                      setSelectedPatient(patients.find((p) => p.id === value))
                    }
                  >
                    <SelectTrigger className="w-full mt-1">
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
                          <SelectItem key={patient.id} value={patient.id}>
                            {patient.full_name} -{" "}
                            {new Date(patient.date_of_birth).toLocaleDateString(
                              "fr-FR",
                            )}
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                </div>

                {selectedPatient && (
                  <div className="mt-4 p-4 border rounded-lg bg-gray-50">
                    <h3 className="font-medium">Patient sélectionné :</h3>
                    <p className="text-sm text-gray-600">
                      {selectedPatient.full_name}
                    </p>
                    <p className="text-xs text-gray-500">
                      Date de naissance:{" "}
                      {new Date(
                        selectedPatient.date_of_birth,
                      ).toLocaleDateString("fr-FR")}
                    </p>
                  </div>
                )}

                <div className="flex justify-end mt-6">
                  <Button
                    type="button"
                    onClick={() => setStep(2)}
                    disabled={!selectedPatient}
                  >
                    Suivant
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Images du patient</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {patientImages.map((image) => (
                    <div
                      key={image.id}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        selectedImages.includes(image.id)
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200"
                      }`}
                      onClick={() => handleImageSelect(image.id)}
                    >
                      <div className="bg-gray-100 h-32 flex items-center justify-center rounded mb-2">
                        <span className="text-gray-400">
                          Image: {image.name}
                        </span>
                      </div>
                      <div className="text-sm">
                        <p className="font-medium">{image.type}</p>
                        <p className="text-xs text-gray-500">
                          Ajouté le {image.date}
                        </p>
                      </div>
                    </div>
                  ))}

                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 transition-colors">
                    <Upload className="h-6 w-6 text-gray-400 mb-2" />
                    <p className="text-sm text-gray-600">Ajouter des images</p>
                    <p className="text-xs text-gray-400 mt-1">
                      Glissez-déposez ou cliquez pour téléverser
                    </p>
                  </div>
                </div>

                <div className="flex justify-between mt-6">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep(1)}
                  >
                    Retour
                  </Button>
                  <Button
                    type="button"
                    onClick={() => setStep(3)}
                    disabled={selectedImages.length === 0}
                  >
                    Suivant
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {step === 3 && (
          <Card className="mb-6">
            <CardHeader>
              <CardTitle>Affectation des spécialistes</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-6">
                <div>
                  <Label htmlFor="specialist">Ajouter un spécialiste</Label>
                  <div className="flex space-x-2 mt-1">
                    <Select onValueChange={addSpecialist}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Sélectionner un spécialiste" />
                      </SelectTrigger>
                      <SelectContent>
                        {specialists
                          .filter(
                            (s) =>
                              !selectedSpecialists.some(
                                (sel) => sel.id === s.id,
                              ),
                          )
                          .map((specialist) => (
                            <SelectItem
                              key={specialist.id}
                              value={specialist.id.toString()}
                            >
                              {specialist.name} - {specialist.specialty}
                            </SelectItem>
                          ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Ordre de passage des spécialistes</Label>
                  <div className="space-y-2">
                    {selectedSpecialists.length > 0 ? (
                      selectedSpecialists.map((specialist, index) => (
                        <div
                          key={specialist.id}
                          className="flex items-center justify-between p-3 border rounded-lg"
                        >
                          <div>
                            <p className="font-medium">{specialist.name}</p>
                            <p className="text-sm text-gray-500">
                              {specialist.specialty}
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
                              disabled={
                                index === selectedSpecialists.length - 1
                              }
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
                    className="w-full mt-1 p-2 border rounded-md min-h-[100px]"
                    placeholder="Ajoutez des notes ou des instructions pour les spécialistes..."
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                </div>

                <div className="flex justify-between pt-4">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setStep(2)}
                  >
                    Retour
                  </Button>
                  <Button
                    type="submit"
                    disabled={selectedSpecialists.length === 0}
                  >
                    Créer le cas
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </form>
    </div>
  );
};

export default NewCase;
