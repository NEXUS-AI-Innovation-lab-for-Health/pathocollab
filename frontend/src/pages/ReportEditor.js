import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ArrowLeft, Save, Send, FileText, User, Calendar } from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import { getCurrentUser } from "@/services/auth";


const CASES_API = process.env.REACT_APP_CASES_SERVICE_URL || `${window.location.protocol}//${window.location.hostname}:8002`;
const WORKFLOW_API = process.env.REACT_APP_WORKFLOW_SERVICE_URL || `${window.location.protocol}//${window.location.hostname}:8003`;
const REPORTS_API = process.env.REACT_APP_REPORTS_SERVICE_URL || `${window.location.protocol}//${window.location.hostname}:8005`;

const getStatusLabel = (status) => {
  const labels = {
    pending: "En attente",
    in_progress: "En cours",
    completed: "Terminé",
    cancelled: "Annulé",
  };
  return labels[status] || status;
};

const getStatusColor = (status) => {
  const colors = {
    pending: "bg-yellow-100 text-yellow-800",
    in_progress: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
  };
  return colors[status] || "bg-gray-100 text-gray-800";
};

const ReportEditor = () => {
  const { caseId, reportId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState(null);
  const [existingReport, setExistingReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(!!reportId);

  // État du formulaire
  const [reportData, setReportData] = useState({
    title: "",
    patient_id: "",
    clinical_findings: "",
    diagnosis: "",
    recommendations: "",
    conclusion: "",
    specialist_name: "",
    date: new Date().toISOString().split("T")[0],
  });

  useEffect(() => {
    fetchCaseDetails();
    if (isEditing) {
      fetchExistingReport();
    }
  }, [caseId, isEditing]);

  const getAuthHeaders = () => {
    const token = localStorage.getItem("access_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const fetchCaseDetails = async () => {
    try {
      const response = await axios.get(
        `${CASES_API}/api/cases/${caseId}`,
        {
          headers: getAuthHeaders(),
        }
      );

      setCaseData(response.data);

      let userId = "Spécialiste inconnu";
      const token = localStorage.getItem("access_token");

      if (token) {
        try {
          const tokenData = JSON.parse(atob(token.split(".")[1]));
          const email = tokenData.sub || tokenData.email || "";
          userId = email || "Spécialiste inconnu";
        } catch (error) {
          console.error("Erreur de décodage du token:", error);
        }
      }

      setReportData((prev) => ({
        ...prev,
        title: `Rapport d'analyse - ${response.data.id}`,
        patient_id: response.data.patient_id,
        specialist_name: userId,
      }));
    } catch (error) {
      console.error("Error fetching case details:", error);

      if (error.response?.status === 401) {
        toast.error("Session expirée ou non authentifiée");
        navigate("/login");
        return;
      }

      if (error.response?.status === 403) {
        toast.error("Vous n'êtes pas autorisé à accéder à ce cas");
        navigate("/dashboard");
        return;
      }

      toast.error("Erreur lors du chargement du cas");
    } finally {
      setLoading(false);
    }
  };

  const fetchExistingReport = async () => {
    try {
      const response = await axios.get(
        `${REPORTS_API}/api/reports/${reportId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );
      setExistingReport(response.data);

      // Parser le contenu du rapport pour pré-remplir les champs
      const content = response.data.content;
      const sections = content.split("**");

      const parsedData = {
        title: response.data.title,
        clinical_findings: "",
        diagnosis: "",
        recommendations: "",
        conclusion: "",
      };

      for (let i = 0; i < sections.length; i++) {
        if (sections[i].includes("Observations cliniques")) {
          parsedData.clinical_findings = sections[i + 1]?.trim() || "";
        } else if (sections[i].includes("Diagnostic")) {
          parsedData.diagnosis = sections[i + 1]?.trim() || "";
        } else if (sections[i].includes("Recommandations")) {
          parsedData.recommendations = sections[i + 1]?.trim() || "";
        } else if (sections[i].includes("Conclusion")) {
          parsedData.conclusion = sections[i + 1]?.trim() || "";
        }
      }

      setReportData(parsedData);
    } catch (error) {
      console.error("Error fetching existing report:", error);
      toast.error("Erreur lors du chargement du rapport");
    }
  };

  const canEditReport = () => {
    // Récupérer l'ID de l'utilisateur connecté
    const currentUserId = localStorage.getItem("user_id") || "admin";

    // Pour l'instant, on autorise tout le monde à éditer
    // À améliorer : vérifier si c'est le spécialiste actuel du workflow
    return true;
  };

  const handleInputChange = (field, value) => {
    setReportData((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSave = async () => {
    if (
      !reportData.title ||
      !reportData.clinical_findings ||
      !reportData.diagnosis
    ) {
      toast.error("Veuillez remplir les champs obligatoires");
      return;
    }

    setSaving(true);
    try {
      // Récupérer l'utilisateur connecté
      const token = localStorage.getItem("access_token");
      let userId = "Utilisateur inconnu";

      if (token) {
        try {
          const tokenData = JSON.parse(atob(token.split(".")[1]));
          const email = tokenData.sub || tokenData.email || "";

          userId = email || "Utilisateur inconnu";
        } catch (error) {
          console.error("Erreur de décodage du token:", error);
        }
      }

      // Construire le contenu du rapport
      const reportContent = `
        **Observations cliniques**
        ${reportData.clinical_findings}

        **Diagnostic**
        ${reportData.diagnosis}

        **Recommandations**
        ${reportData.recommendations || "Aucune recommandation"}

        **Conclusion**
        ${reportData.conclusion || "Aucune conclusion"}
              `.trim();

      // Préparer les données pour l'API
      const reportPayload = {
        case_id: caseId,
        user_id: userId,
        title: reportData.title,
        content: reportContent,
        is_final: false,
      };

      // Sauvegarder dans la base de données
      let response;
      if (isEditing) {
        // Mettre à jour le rapport existant
        response = await axios.put(
          `${REPORTS_API}/api/reports/${reportId}`,
          reportPayload,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          },
        );
      } else {
        // Créer un nouveau rapport
        response = await axios.post(
          `${REPORTS_API}/api/reports/`,
          reportPayload,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          },
        );
      }

      console.log("Rapport sauvegardé:", response.data);
      toast.success("Rapport sauvegardé avec succès");

      // Si le rapport est marqué comme final, mettre à jour le workflow
      if (reportPayload.is_final) {
        try {
          const workflowResponse = await axios.get(
            `${WORKFLOW_API}/api/workflows/case/${caseId}`,
            { headers: getAuthHeaders() }
          );

          await axios.post(
            `${WORKFLOW_API}/api/workflows/${workflowResponse.data.id}/advance`,
            {},
            { headers: getAuthHeaders() }
          );
          console.log("Workflow mis à jour avec succès");
        } catch (workflowError) {
          console.error("Error updating workflow:", workflowError);
          console.warn(
            "Le workflow n'a pas pu être mis à jour automatiquement",
          );
        }
      }
    } catch (error) {
      console.error("Error saving report:", error);
      toast.error("Erreur lors de la sauvegarde du rapport");
    } finally {
      setSaving(false);
    }
  };

  const handleSubmit = async () => {
    if (
      !reportData.title ||
      !reportData.clinical_findings ||
      !reportData.diagnosis
    ) {
      toast.error("Veuillez remplir les champs obligatoires");
      return;
    }

    setSaving(true);
    try {
      // Récupérer l'utilisateur connecté
      const token = localStorage.getItem("access_token");
      let userId = "Utilisateur inconnu";

      if (token) {
        try {
          const tokenData = JSON.parse(atob(token.split(".")[1]));
          const email = tokenData.sub || tokenData.email || "";

          userId = email || "Utilisateur inconnu";
        } catch (error) {
          console.error("Erreur de décodage du token:", error);
        }
      }

      // Construire le contenu du rapport
      const reportContent = `
**Observations cliniques**
${reportData.clinical_findings}

**Diagnostic**
${reportData.diagnosis}

**Recommandations**
${reportData.recommendations || "Aucune recommandation"}

**Conclusion**
${reportData.conclusion || "Aucune conclusion"}
      `.trim();

      // Préparer les données pour l'API
      const reportPayload = {
        case_id: caseId,
        user_id: userId,
        title: reportData.title,
        content: reportContent,
        is_final: true, // Marquer comme final lors de la soumission
      };

      // Sauvegarder dans la base de données
      let response;
      if (isEditing) {
        // Mettre à jour le rapport existant et le marquer comme final
        response = await axios.put(
          `${REPORTS_API}/api/reports/${reportId}`,
          reportPayload,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          },
        );
      } else {
        // Créer un nouveau rapport
        response = await axios.post(
          `${REPORTS_API}/api/reports/`,
          reportPayload,
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          },
        );
      }

      console.log("Rapport soumis:", response.data);
      toast.success("Rapport soumis avec succès");

      // Mettre à jour le workflow pour passer à l'étape suivante
      try {
        // D'abord récupérer le workflow par case_id
        const workflowResponse = await axios.get(
          `${WORKFLOW_API}/api/workflows/case/${caseId}`,
        );

        // Puis avancer le workflow avec son ID
        await axios.post(
          `${WORKFLOW_API}/api/workflows/${workflowResponse.data.id}/advance`,
          {},
        );
        console.log("Workflow mis à jour avec succès");
      } catch (workflowError) {
        console.error("Error updating workflow:", workflowError);
        // Ne pas bloquer l'utilisateur si le workflow ne se met pas à jour
        console.warn("Le workflow n'a pas pu être mis à jour automatiquement");
      }

      // Mettre à jour le statut du cas
      try {
        await axios.patch(
          `${CASES_API}/api/cases/${caseId}/status?status=in_progress`,
          {},
          {
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${localStorage.getItem("access_token")}`,
            },
          },
        );
        console.log("Statut du cas mis à jour avec succès");
      } catch (statusError) {
        console.error("Error updating case status:", statusError);
        console.warn(
          "Le statut du cas n'a pas pu être mis à jour automatiquement",
        );
      }

      navigate(`/cases/${caseId}`);
    } catch (error) {
      console.error("Error submitting report:", error);
      toast.error("Erreur lors de la soumission du rapport");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-600">Chargement...</p>
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <p className="text-slate-600">Cas non trouvé</p>
      </div>
    );
  }

  if (!canEditReport()) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <FileText className="h-8 w-8 text-red-600" />
              </div>
              <h3 className="text-lg font-semibold text-slate-900 mb-2">
                Accès non autorisé
              </h3>
              <p className="text-sm text-slate-500 mb-4">
                Vous n'êtes pas autorisé à créer ou modifier un rapport pour ce
                cas.
              </p>
              <Button onClick={() => navigate(`/cases/${caseId}`)}>
                Retour au cas
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate(`/cases/${caseId}`)}
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex-1">
              <h1 className="text-2xl font-bold text-slate-900">
                Rédaction du rapport
              </h1>
              <p className="text-sm text-slate-500 mt-1">Cas: {caseData.id}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" onClick={handleSave} disabled={saving}>
                <Save className="h-4 w-4 mr-2" />
                {saving ? "Sauvegarde..." : "Sauvegarder"}
              </Button>
              <Button onClick={handleSubmit} disabled={saving}>
                <Send className="h-4 w-4 mr-2" />
                {saving ? "Soumission..." : "Soumettre"}
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Informations du cas */}
          <div className="lg:col-span-1">
            <Card className="mb-6">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  Informations du cas
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-sm font-medium text-slate-500">
                    ID du cas
                  </Label>
                  <p className="font-semibold">{caseData.id}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-500">
                    Titre
                  </Label>
                  <p className="font-semibold">{caseData.title}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-500">
                    ID Patient
                  </Label>
                  <p className="font-semibold">{caseData.patient_id}</p>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-500">
                    Statut
                  </Label>
                  <Badge className={getStatusColor(caseData.status)}>
                    {getStatusLabel(caseData.status)}
                  </Badge>
                </div>
                <div>
                  <Label className="text-sm font-medium text-slate-500">
                    Spécialistes assignés
                  </Label>
                  <div className="mt-1">
                    {caseData.assigned_specialists?.map((specialist, index) => (
                      <Badge
                        key={index}
                        variant="outline"
                        className="mr-1 mb-1"
                      >
                        {specialist}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Métadonnées du rapport */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <User className="h-5 w-5" />
                  Métadonnées
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="specialist_name">Spécialiste</Label>
                  <Input
                    id="specialist_name"
                    value={reportData.specialist_name}
                    onChange={(e) =>
                      handleInputChange("specialist_name", e.target.value)
                    }
                    placeholder="Votre nom"
                  />
                </div>
                <div>
                  <Label htmlFor="date">Date du rapport</Label>
                  <Input
                    id="date"
                    type="date"
                    value={reportData.date}
                    onChange={(e) => handleInputChange("date", e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Formulaire du rapport */}
          <div className="lg:col-span-2">
            <Card>
              <CardHeader>
                <CardTitle>Contenu du rapport</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div>
                  <Label htmlFor="title">Titre du rapport *</Label>
                  <Input
                    id="title"
                    value={reportData.title}
                    onChange={(e) => handleInputChange("title", e.target.value)}
                    placeholder="Titre du rapport"
                  />
                </div>

                <div>
                  <Label htmlFor="clinical_findings">
                    Observations cliniques *
                  </Label>
                  <Textarea
                    id="clinical_findings"
                    value={reportData.clinical_findings}
                    onChange={(e) =>
                      handleInputChange("clinical_findings", e.target.value)
                    }
                    placeholder="Décrivez vos observations cliniques détaillées..."
                    rows={6}
                  />
                </div>

                <div>
                  <Label htmlFor="diagnosis">Diagnostic *</Label>
                  <Textarea
                    id="diagnosis"
                    value={reportData.diagnosis}
                    onChange={(e) =>
                      handleInputChange("diagnosis", e.target.value)
                    }
                    placeholder="Diagnostic basé sur vos observations..."
                    rows={4}
                  />
                </div>

                <div>
                  <Label htmlFor="recommendations">Recommandations</Label>
                  <Textarea
                    id="recommendations"
                    value={reportData.recommendations}
                    onChange={(e) =>
                      handleInputChange("recommendations", e.target.value)
                    }
                    placeholder="Recommandations pour le traitement ou le suivi..."
                    rows={4}
                  />
                </div>

                <div>
                  <Label htmlFor="conclusion">Conclusion</Label>
                  <Textarea
                    id="conclusion"
                    value={reportData.conclusion}
                    onChange={(e) =>
                      handleInputChange("conclusion", e.target.value)
                    }
                    placeholder="Conclusion finale du rapport..."
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ReportEditor;
