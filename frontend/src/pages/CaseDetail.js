import React, { useState, useEffect, useRef, useMemo } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  FileText,
  Calendar,
  User,
  Plus,
  Edit,
  Trash2,
  Image,
  Users,
  MessageSquare,
  Download,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";

import OpenSeadragonUrlViewer from "../components/OpenSeadragon/OpenSeadragonUrlViewer.tsx";

const CASES_API = process.env.REACT_APP_BACKEND_URL || `${window.location.protocol}//${window.location.hostname}:8002`;
const WORKFLOW_API = process.env.REACT_APP_WORKFLOW_URL || `${window.location.protocol}//${window.location.hostname}:8003`;
const IMAGES_API = process.env.REACT_APP_IMAGES_URL || `${window.location.protocol}//${window.location.hostname}:8004`;
const REPORTS_API = process.env.REACT_APP_REPORTS_URL || `${window.location.protocol}//${window.location.hostname}:8005`;

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

const CaseDetail = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCase] = useState(null);
  const [patient, setPatient] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [reports, setReports] = useState([]);
  const [loadingReports, setLoadingReports] = useState(true);
  const [loading, setLoading] = useState(true);
  const [generatingPDF, setGeneratingPDF] = useState(false);
  const reportRefs = useRef({});

  const [wsis, setWsis] = useState([]);
  const [selectedWsi, setSelectedWsi] = useState(null);
  const [wsiLoading, setWsiLoading] = useState(false);
  const [wsiError, setWsiError] = useState(null);

  useEffect(() => {
    fetchCaseDetails();
    fetchReports();
  }, [caseId]);

  useEffect(() => {
    if (!patient?.id) return;

    let cancelled = false;

    (async () => {
      try {
        setWsiLoading(true);
        setWsiError(null);
        setWsis([]);
        setSelectedWsi(null);

        const token = localStorage.getItem("access_token");
        const res = await axios.get(
          `${IMAGES_API}/api/debug/wsi-dzi?patient_id=${encodeURIComponent(patient.id)}`,
          token ? { headers: { Authorization: `Bearer ${token}` } } : undefined,
        );

        const list = res.data?.wsis || res.data?.slides || [];
        if (cancelled) return;

        setWsis(list);
        if (list.length > 0) setSelectedWsi(list[0]);
      } catch (e) {
        if (!cancelled) {
          console.error("Error loading WSI/DZI:", e);
          setWsiError(e);
          setWsis([]);
          setSelectedWsi(null);
        }
      } finally {
        if (!cancelled) setWsiLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [patient?.id]);

  const viewerSource = useMemo(() => {
    if (!patient?.id || !selectedWsi?.wsi_id) return null;

    return {
      type: "dzi",
      url: `${IMAGES_API}/api/wsi/patients/${encodeURIComponent(patient.id)}/${encodeURIComponent(selectedWsi.wsi_id)}/dzi`,
      key: `${patient.id}:${selectedWsi.wsi_id}`,
    };
  }, [patient?.id, selectedWsi?.wsi_id]);

  const fetchCaseDetails = async () => {
    try {
      // Fetch case
      const caseResponse = await axios.get(
        `${CASES_API}/api/cases/${caseId}`,
      );
      setCase(caseResponse.data);

      // Fetch patient depuis la base de données
      try {
        const patientResponse = await axios.get(
          `${CASES_API}/api/patients/${caseResponse.data.patient_id}`,
        );
        setPatient(patientResponse.data);
      } catch (err) {
        console.log("No patient found for this case");
      }

      // Fetch workflow
      try {
        const workflowResponse = await axios.get(
          `${WORKFLOW_API}/api/workflows/case/${caseId}`,
        );
        setWorkflow(workflowResponse.data);
      } catch (err) {
        console.log("No workflow found for this case");
      }
    } catch (error) {
      console.error("Error fetching case details:", error);
      toast.error("Erreur lors du chargement du cas");
    } finally {
      setLoading(false);
    }
  };

  const fetchReports = async () => {
    try {
      const response = await axios.get(
        `${REPORTS_API}/api/reports/case/${caseId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );
      setReports(response.data);
      console.log("Rapports chargés:", response.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
      // Ne pas afficher d'erreur si aucun rapport n'existe
      setReports([]);
    } finally {
      setLoadingReports(false);
    }
  };

  const handleDeleteReport = async (reportId, reportUserId) => {
    if (!canDeleteReport(reportUserId)) {
      toast.error("Vous n'êtes pas autorisé à supprimer ce rapport");
      return;
    }

    if (!window.confirm("Êtes-vous sûr de vouloir supprimer ce rapport ?")) {
      return;
    }

    try {
      await axios.delete(`${REPORTS_API}/api/reports/${reportId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });

      toast.success("Rapport supprimé avec succès");
      // Recharger la liste des rapports
      fetchReports();
    } catch (error) {
      console.error("Error deleting report:", error);
      if (error.response?.status === 400) {
        toast.error("Impossible de supprimer un rapport final");
      } else {
        toast.error("Erreur lors de la suppression du rapport");
      }
    }
  };

  const getSpecialistStep = (reportUserId, reportIndex) => {
    if (!workflow || !workflow.specialists_order) return null;

    const specialistIndex = workflow.specialists_order.findIndex(
      (specialist) => specialist === reportUserId,
    );

    if (specialistIndex === -1) return null;

    return {
      step: specialistIndex + 1,
      totalSteps: workflow.specialists_order.length,
      isCurrentStep: specialistIndex === workflow.current_step,
      isCompleted: specialistIndex < workflow.current_step,
    };
  };

  const getCurrentUserId = () => {
    // Récupérer l'ID de l'utilisateur connecté depuis le token JWT
    const token = localStorage.getItem("access_token");
    let currentUserId = "admin"; // Valeur par défaut

    if (token) {
      try {
        // Décoder le token pour obtenir l'ID utilisateur
        const tokenData = JSON.parse(atob(token.split(".")[1]));
        // Utiliser l'email directement comme identifiant
        const email = tokenData.sub || tokenData.email || "";

        if (email === "dr.smith@pixtral.fr") {
          currentUserId = "dr.smith@pixtral.fr";
        } else if (email === "admin@pixtral.fr") {
          currentUserId = "admin@pixtral.fr";
        } else {
          currentUserId = email || "admin";
        }

        console.log("Token décodé:", tokenData);
        console.log("Email détecté:", email);
        console.log("User ID final:", currentUserId);
      } catch (error) {
        console.error("Erreur de décodage du token:", error);
      }
    }

    return currentUserId;
  };

  const isAdmin = () => {
    const currentUserId = getCurrentUserId();
    return currentUserId === "admin" || currentUserId === "admin@pixtral.fr";
  };

  const canCreateReport = () => {
    // Vérifier si l'utilisateur connecté est un spécialiste assigné à ce cas
    if (!workflow || !workflow.specialists_order) return false;

    const currentUserId = getCurrentUserId();

    console.log("Workflow spécialistes:", workflow.specialists_order);
    console.log("Étape actuelle:", workflow.current_step);
    console.log("User ID:", currentUserId);

    // L'admin ne peut pas créer de rapports
    if (isAdmin()) return false;

    // Vérifier si l'utilisateur est dans la liste des spécialistes
    const isSpecialist = workflow.specialists_order.includes(currentUserId);
    console.log("Est spécialiste:", isSpecialist);

    // Vérifier si c'est le tour de cet utilisateur (spécialiste actuel)
    const isCurrentSpecialist =
      workflow.specialists_order[workflow.current_step] === currentUserId;
    console.log("Est spécialiste actuel:", isCurrentSpecialist);

    return isSpecialist && isCurrentSpecialist;
  };

  const canEditReport = (reportUserId) => {
    const currentUserId = getCurrentUserId();

    console.log(
      "Vérification édition - User ID:",
      currentUserId,
      "Report User ID:",
      reportUserId,
    );

    // L'admin ne peut pas modifier les rapports
    if (isAdmin()) {
      console.log("Admin ne peut pas modifier");
      return false;
    }

    // Seul l'auteur du rapport peut le modifier
    const canEdit = currentUserId === reportUserId;
    console.log("Peut modifier:", canEdit);

    return canEdit;
  };

  const canDeleteReport = (reportUserId) => {
    const currentUserId = getCurrentUserId();

    console.log(
      "Vérification suppression - User ID:",
      currentUserId,
      "Report User ID:",
      reportUserId,
    );

    // L'admin ne peut pas supprimer les rapports
    if (isAdmin()) {
      console.log("Admin ne peut pas supprimer");
      return false;
    }

    // Seul l'auteur du rapport peut le supprimer
    const canDelete = currentUserId === reportUserId;
    console.log("Peut supprimer:", canDelete);

    return canDelete;
  };

  const getCurrentSpecialist = () => {
    if (!workflow || !workflow.specialists_order) return null;
    return workflow.specialists_order[workflow.current_step];
  };

  const handleDownloadPDF = async (report) => {
      setGeneratingPDF(true);
      try {
        const pdf = new jsPDF();
        let yPos = 20;
  
        const ensurePage = (extra = 0) => {
          if (yPos + extra > 270) {
            pdf.addPage();
            yPos = 20;
          }
        };
  
        // Add header information
        pdf.setFontSize(18);
        pdf.setFont("helvetica", "bold");
        ensurePage(10);
        pdf.text(`Rapport d'analyse - ${caseData.id}`, 20, yPos);
        yPos += 10;
  
        pdf.setFontSize(12);
        pdf.setFont("helvetica", "normal");
        ensurePage(8);
        pdf.text(
          `Par ${report.user_id} • ${new Date(
            report.created_at,
          ).toLocaleDateString("fr-FR")}`,
          20,
          yPos,
        );
        yPos += 8;
  
        pdf.setFontSize(14);
        pdf.setFont("helvetica", "bold");
        ensurePage(12);
        pdf.text(`Titre: ${report.title}`, 20, yPos);
        yPos += 12;
  
        // Parse and add report content with proper formatting
        pdf.setFontSize(12);
        pdf.setFont("helvetica", "normal");
  
        const lines = report.content.split("\n");
        for (const line of lines) {
          if (line.trim()) {
            // Check if it's a title (starts with **)
            if (line.startsWith("**") && line.endsWith("**")) {
              pdf.setFont("helvetica", "bold");
              const title = line.replace(/\*\*/g, "");
              ensurePage(8);
              pdf.text(title, 20, yPos);
              yPos += 8;
            } else {
              pdf.setFont("helvetica", "normal");
              // Handle long lines by splitting them
              const splitText = pdf.splitTextToSize(line, 170);
              for (const textLine of splitText) {
                ensurePage(6);
                pdf.text(textLine, 20, yPos);
                yPos += 6;
              }
            }
          } else {
            ensurePage(4);
            yPos += 4; // Add space for empty lines
          }
  }
  
        pdf.save(
          `rapport_${report.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}.pdf`,
        );
  
        toast.success("PDF téléchargé avec succès");
      } catch (error) {
        console.error("Error generating PDF:", error);
        toast.error("Erreur lors de la génération du PDF");
      } finally {
        setGeneratingPDF(false);
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

  return (
    <div className="min-h-screen bg-slate-50" data-testid="case-detail-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate("/dashboard")}
              data-testid="back-button"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  {caseData.id}
                </h1>
                <Badge className={getStatusColor(caseData.status)}>
                  {getStatusLabel(caseData.status)}
                </Badge>
              </div>
              <p className="text-sm text-slate-500 mt-1">{caseData.title}</p>
              {workflow && getCurrentSpecialist() && (
                <p className="text-xs text-blue-600 mt-1">
                  En attente du rapport de Dr. {getCurrentSpecialist()}
                </p>
              )}
            </div>
            {canCreateReport() && (
              <Button
                data-testid="start-analysis-button"
                onClick={() => navigate(`/cases/${caseId}/report`)}
              >
                Commencer mon rapport
              </Button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        <Tabs defaultValue="overview" className="space-y-6">
          <TabsList>
            <TabsTrigger value="overview" data-testid="tab-overview">
              <User className="h-4 w-4 mr-2" />
              Vue d'ensemble
            </TabsTrigger>
            <TabsTrigger value="images" data-testid="tab-images">
              <Image className="h-4 w-4 mr-2" />
              Images
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="tab-reports">
              <FileText className="h-4 w-4 mr-2" />
              Rapports
            </TabsTrigger>
            <TabsTrigger value="team" data-testid="tab-team">
              <Users className="h-4 w-4 mr-2" />
              Équipe
            </TabsTrigger>
            <TabsTrigger value="discussion" data-testid="tab-discussion">
              <MessageSquare className="h-4 w-4 mr-2" />
              Discussion
            </TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            {/* Case Information Card */}
            <Card>
              <CardHeader>
                <CardTitle>Informations du cas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-500">
                      ID du cas
                    </p>
                    <p className="text-base text-slate-900">{caseData.id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">Titre</p>
                    <p className="text-base text-slate-900">{caseData.title}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">
                      ID Patient
                    </p>
                    <p className="text-base text-slate-900">
                      {caseData.patient_id}
                    </p>
                  </div>
                  {patient && (
                    <div>
                      <p className="text-sm font-medium text-slate-500">
                        Date de naissance
                      </p>
                      <p className="text-base text-slate-900">
                        {new Date(patient.date_of_birth).toLocaleDateString(
                          "fr-FR",
                        )}
                      </p>
                    </div>
                  )}
                  <div>
                    <p className="text-sm font-medium text-slate-500">Statut</p>
                    <Badge className={getStatusColor(caseData.status)}>
                      {getStatusLabel(caseData.status)}
                    </Badge>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-500">
                      Description
                    </p>
                    <p className="text-base text-slate-900">
                      {caseData.description || "Aucune description"}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-500">
                      Créé par
                    </p>
                    <p className="text-base text-slate-900">
                      {caseData.created_by}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-500">
                      Date de création
                    </p>
                    <p className="text-base text-slate-900">
                      {new Date(caseData.created_at).toLocaleDateString(
                        "fr-FR",
                      )}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            {patient && (
              <Card data-testid="patient-info-card">
                <CardHeader>
                  <CardTitle>Informations Patient</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-medium text-slate-500">
                        Nom complet
                      </p>
                      <p className="text-base text-slate-900">
                        {patient.full_name}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">
                        ID Patient
                      </p>
                      <p className="text-base text-slate-900">{patient.id}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">Âge</p>
                      <p className="text-base text-slate-900">
                        {patient.age} ans
                      </p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">
                        Genre
                      </p>
                      <p className="text-base text-slate-900">
                        {patient.gender}
                      </p>
                    </div>
                    {patient.medical_history && (
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-slate-500">
                          Antécédents
                        </p>
                        <p className="text-base text-slate-900">
                          {patient.medical_history}
                        </p>
                      </div>
                    )}
                    {patient.symptoms && (
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-slate-500">
                          Symptômes
                        </p>
                        <p className="text-base text-slate-900">
                          {patient.symptoms}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {workflow && (
              <Card data-testid="workflow-card">
                <CardHeader>
                  <CardTitle>Workflow Collaboratif</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {workflow.specialists_order.map((specialist, index) => (
                      <div
                        key={index}
                        className={`flex items-center gap-3 p-3 rounded-lg border ${
                          index === workflow.current_step
                            ? "border-blue-300 bg-blue-50"
                            : index < workflow.current_step
                              ? "border-green-300 bg-green-50"
                              : "border-slate-200 bg-slate-50"
                        }`}
                        data-testid={`workflow-step-${index}`}
                      >
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === workflow.current_step
                              ? "bg-blue-600 text-white"
                              : index < workflow.current_step
                                ? "bg-green-600 text-white"
                                : "bg-slate-300 text-slate-600"
                          }`}
                        >
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-slate-900">
                            Spécialiste {specialist}
                          </p>
                          <p className="text-sm text-slate-500">
                            {index === workflow.current_step
                              ? "En cours d'analyse"
                              : index < workflow.current_step
                                ? "Terminé"
                                : "En attente"}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Images Tab */}
          <TabsContent value="images" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Images WSI (OpenSeadragon)</CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                {/* Selector */}
                <div className="flex flex-col md:flex-row md:items-center gap-3">
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600">Patient :</span>
                    <Badge variant="outline">
                      {patient?.full_name || patient?.id}
                    </Badge>
                  </div>

                  <div className="flex-1" />

                  <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-600">WSI :</span>

                    <select
                      className="border border-slate-200 rounded-md px-3 py-2 bg-white text-sm min-w-[260px]"
                      disabled={wsiLoading || wsis.length === 0}
                      value={selectedWsi?.wsi_id || ""}
                      onChange={(e) => {
                        const w = wsis.find((x) => x.wsi_id === e.target.value);
                        setSelectedWsi(w || null);
                      }}
                    >
                      {wsis.length === 0 ? (
                        <option value="">Aucune WSI disponible</option>
                      ) : (
                        wsis.map((w) => (
                          <option key={w.wsi_id} value={w.wsi_id}>
                            {w.filename || `WSI ${w.wsi_id}`}
                          </option>
                        ))
                      )}
                    </select>

                    <span className="text-xs text-slate-500">
                      {wsis.length} WSI
                    </span>
                  </div>
                </div>

                {/* States */}
                {wsiLoading && (
                  <div className="text-sm text-slate-600">
                    Chargement des images…
                  </div>
                )}

                {!wsiLoading && wsiError && (
                  <div className="text-sm text-red-600">
                    Impossible de charger les WSI pour ce patient.
                  </div>
                )}

                {/* Viewer */}
                <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                  <div className="h-[70vh] min-h-[520px]">
                    {!viewerSource ? (
                      <div className="h-full flex items-center justify-center text-slate-500">
                        Sélectionnez une image WSI.
                      </div>
                    ) : (
                      <OpenSeadragonUrlViewer
                        sourceType={viewerSource.type}
                        sourceUrl={viewerSource.url}
                        imageKey={viewerSource.key}
                        imageId={selectedWsi?.wsi_id}
                        caseId={caseData?.id}
                      />
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reports Tab */}
          <TabsContent value="reports">
            <Card>
              <CardHeader>
                <CardTitle>Rapports des spécialistes</CardTitle>
              </CardHeader>
              <CardContent>
                {loadingReports ? (
                  <div className="flex items-center justify-center py-8">
                    <p className="text-slate-500">Chargement des rapports...</p>
                  </div>
                ) : reports.length === 0 ? (
                  <div className="text-center py-8">
                    <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500 mb-4">
                      Aucun rapport n'a encore été créé pour ce cas
                    </p>
                    {canCreateReport() ? (
                      <Button
                        onClick={() => navigate(`/cases/${caseId}/report`)}
                      >
                        <FileText className="h-4 w-4 mr-2" />
                        Créer mon rapport
                      </Button>
                    ) : (
                      <div className="text-sm text-slate-500">
                        {workflow && getCurrentSpecialist() ? (
                          <p>
                            En attente du rapport de Dr.{" "}
                            {getCurrentSpecialist()}
                          </p>
                        ) : (
                          <p>Vous n'êtes pas assigné à ce cas</p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {reports.map((report, index) => {
                      const specialistStep = getSpecialistStep(
                        report.user_id,
                        index,
                      );

                      return (
                        <Card
                          key={report.id}
                          className="border border-slate-200"
                        >
                          <CardContent className="pt-6">
                            <div className="flex items-start justify-between mb-4">
                              <div className="flex-1">
                                <div className="flex items-center gap-2 mb-2">
                                  <div
                                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                                      specialistStep?.isCurrentStep
                                        ? "bg-blue-100"
                                        : specialistStep?.isCompleted
                                          ? "bg-green-100"
                                          : "bg-slate-100"
                                    }`}
                                  >
                                    <User
                                      className={`h-4 w-4 ${
                                        specialistStep?.isCurrentStep
                                          ? "text-blue-600"
                                          : specialistStep?.isCompleted
                                            ? "text-green-600"
                                            : "text-slate-600"
                                      }`}
                                    />
                                  </div>
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                      <h3 className="font-semibold text-slate-900">
                                        {report.title}
                                      </h3>
                                      {specialistStep && (
                                        <Badge
                                          variant="outline"
                                          className={`text-xs ${
                                            specialistStep.isCurrentStep
                                              ? "border-blue-200 text-blue-700 bg-blue-50"
                                              : specialistStep.isCompleted
                                                ? "border-green-200 text-green-700 bg-green-50"
                                                : "border-slate-200 text-slate-600 bg-slate-50"
                                          }`}
                                        >
                                          Étape {specialistStep.step}/
                                          {specialistStep.totalSteps}
                                        </Badge>
                                      )}
                                    </div>
                                    <p className="text-sm font-medium text-slate-700">
                                      Dr. {report.user_id}
                                      {specialistStep?.isCurrentStep && (
                                        <span className="ml-2 text-xs text-blue-600 font-medium">
                                          (En cours)
                                        </span>
                                      )}
                                      {specialistStep?.isCompleted && (
                                        <span className="ml-2 text-xs text-green-600 font-medium">
                                          (Terminé)
                                        </span>
                                      )}
                                    </p>
                                  </div>
                                </div>
                                <p className="text-sm text-slate-500 ml-10">
                                  {new Date(
                                    report.created_at,
                                  ).toLocaleDateString("fr-FR")}{" "}
                                  à{" "}
                                  {new Date(
                                    report.created_at,
                                  ).toLocaleTimeString("fr-FR", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </p>
                              </div>
                              <div className="flex items-center gap-2">
                                <Badge
                                  className={
                                    report.is_final
                                      ? "bg-green-100 text-green-800"
                                      : "bg-yellow-100 text-yellow-800"
                                  }
                                >
                                  {report.is_final ? "Final" : "Brouillon"}
                                </Badge>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleDownloadPDF(report)}
                                  disabled={generatingPDF}
                                  className="border-green-600 text-green-600 hover:bg-green-50 disabled:opacity-50"
                                >
                                  <Download className="h-4 w-4 mr-1" />
                                  {generatingPDF ? "Génération..." : "PDF"}
                                </Button>
                                {canEditReport(report.user_id) && (
                                  <Button
                                    size="sm"
                                    onClick={() =>
                                      navigate(
                                        `/cases/${caseId}/report/${report.id}`,
                                      )
                                    }
                                    className="bg-blue-600 hover:bg-blue-700 text-white"
                                  >
                                    ✏️ Modifier
                                  </Button>
                                )}
                                {canDeleteReport(report.user_id) && (
                                  <Button
                                    size="sm"
                                    variant="destructive"
                                    onClick={() =>
                                      handleDeleteReport(
                                        report.id,
                                        report.user_id,
                                      )
                                    }
                                    className="bg-red-600 hover:bg-red-700 text-white"
                                  >
                                    🗑️ Supprimer
                                  </Button>
                                )}
                              </div>
                            </div>
                            <div
                              ref={(el) => (reportRefs.current[report.id] = el)}
                              className="prose prose-sm max-w-none"
                            >
                              <div className="text-sm text-slate-700 bg-slate-50 p-4 rounded-lg">
                                <div className="space-y-4">
                                  <ReactMarkdown
                                    components={{
                                      strong: ({ children }) => (
                                        <strong className="block font-semibold text-slate-900 mb-2 first:mt-0 mt-4">
                                          {children}
                                        </strong>
                                      ),
                                      p: ({ children }) => (
                                        <p className="mb-4 last:mb-0 leading-relaxed break-words">
                                          {children}
                                        </p>
                                      ),
                                    }}
                                  >
                                    {report.content}
                                  </ReactMarkdown>
                                </div>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      );
                    })}
                    <div className="mt-6 pt-4 border-t border-slate-200">
                      {canCreateReport() && (
                        <Button
                          onClick={() => navigate(`/cases/${caseId}/report`)}
                        >
                          <FileText className="h-4 w-4 mr-2" />
                          Ajouter mon rapport
                        </Button>
                      )}
                      {!canCreateReport() && (
                        <div className="text-sm text-slate-500 text-center">
                          {workflow && getCurrentSpecialist() ? (
                            <p>
                              En attente du rapport de Dr.{" "}
                              {getCurrentSpecialist()}
                            </p>
                          ) : (
                            <p>Vous n'êtes pas assigné à ce cas</p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Team Tab */}
          <TabsContent value="team">
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  {caseData.assigned_specialists?.map((specialist, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-3 border border-slate-200 rounded-lg"
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white font-bold">
                        {specialist.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">
                          {specialist}
                        </p>
                        <p className="text-sm text-slate-500">Spécialiste</p>
                      </div>
                    </div>
                  )) || (
                    <p className="text-center text-slate-500">
                      Aucun spécialiste assigné
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Discussion Tab */}
          <TabsContent value="discussion">
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-slate-500 py-8">
                  Chat collaboratif entre spécialistes (à implémenter)
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default CaseDetail;
