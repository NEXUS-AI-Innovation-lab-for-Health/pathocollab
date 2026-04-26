import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  FileText,
  User,
  Image,
  Users,
  MessageSquare,
  Download,
  Upload,
  CheckCircle2,
  FileCheck,
  Lock,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import jsPDF from "jspdf";

import OpenSeadragonUrlViewer from "../components/OpenSeadragon/OpenSeadragonUrlViewer.tsx";
import CornerstoneViewer from "../components/Cornerstone/CornerstoneViewer.tsx";

const CASES_API =
  process.env.REACT_APP_BACKEND_URL ||
  `${window.location.protocol}//${window.location.hostname}:8002`;
const WORKFLOW_API =
  process.env.REACT_APP_WORKFLOW_URL ||
  `${window.location.protocol}//${window.location.hostname}:8003`;
const IMAGES_API =
  process.env.REACT_APP_IMAGES_URL ||
  `${window.location.protocol}//${window.location.hostname}:8004`;
const REPORTS_API =
  process.env.REACT_APP_REPORTS_URL ||
  `${window.location.protocol}//${window.location.hostname}:8005`;

const getStatusLabel = (status) => {
  const labels = {
    pending: "En attente",
    in_progress: "En cours",
    completed: "Terminé",
    cancelled: "Annulé",
    closed: "Fermé",
  };
  return labels[status] || status;
};

const getStatusColor = (status) => {
  const colors = {
    pending: "bg-yellow-100 text-yellow-800",
    in_progress: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
    closed: "bg-slate-200 text-slate-800",
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

  const [generatingFinalPDF, setGeneratingFinalPDF] = useState(false);
  const [closingCase, setClosingCase] = useState(false);
  const [finalPdfReady, setFinalPdfReady] = useState(false);

  const [imageMode, setImageMode] = useState("pathology");

  const [radiologySeries, setRadiologySeries] = useState([]);
  const [selectedRadiologySeries, setSelectedRadiologySeries] = useState(null);
  const [radiologyLoading, setRadiologyLoading] = useState(false);
  const [radiologyError, setRadiologyError] = useState(null);

  const [radiologyUploadFiles, setRadiologyUploadFiles] = useState([]);
  const [radiologyUploading, setRadiologyUploading] = useState(false);

  const [wsis, setWsis] = useState([]);
  const [selectedWsi, setSelectedWsi] = useState(null);
  const [wsiLoading, setWsiLoading] = useState(false);
  const [wsiError, setWsiError] = useState(null);

  const [discussionMessages, setDiscussionMessages] = useState([]);
  const [discussionLoading, setDiscussionLoading] = useState(false);
  const [discussionInput, setDiscussionInput] = useState("");
  const [sendingDiscussion, setSendingDiscussion] = useState(false);

  const getAuthHeaders = useCallback(() => {
    const token = localStorage.getItem("access_token");
    return token ? { Authorization: `Bearer ${token}` } : {};
  }, []);

  const getCurrentUserId = useCallback(() => {
    const token = localStorage.getItem("access_token");
    let currentUserId = "admin";

    if (token) {
      try {
        const tokenData = JSON.parse(atob(token.split(".")[1]));
        const email = tokenData.sub || tokenData.email || "";

        if (email === "dr.smith@pixtral.fr") {
          currentUserId = "dr.smith@pixtral.fr";
        } else if (email === "admin@pixtral.fr") {
          currentUserId = "admin@pixtral.fr";
        } else {
          currentUserId = email || "admin";
        }
      } catch (error) {
        console.error("Erreur de décodage du token:", error);
      }
    }

    return currentUserId;
  }, []);

  const isAdmin = useCallback(() => {
    const currentUserId = getCurrentUserId();
    return currentUserId === "admin" || currentUserId === "admin@pixtral.fr";
  }, [getCurrentUserId]);

  const isClosed = caseData?.status === "closed";

  const getCurrentUserRole = useCallback(() => {
    const token = localStorage.getItem("access_token");
    if (!token) return null;

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      return payload.role || null;
    } catch {
      return null;
    }
  }, []);

  const isMedecinGeneraliste = useCallback(() => {
    return getCurrentUserRole() === "medecin_generaliste";
  }, [getCurrentUserRole]);

  const areAllReportsFinal = useMemo(() => {
    if (!reports.length) return false;
    return reports.every((report) => report.is_final === true);
  }, [reports]);

  const canGeneralistValidateFinalReport = useMemo(() => {
    return isMedecinGeneraliste() && caseData?.status === "completed" && areAllReportsFinal;
  }, [isMedecinGeneraliste, caseData?.status, areAllReportsFinal]);

  const hasRadiology = radiologySeries.length > 0;
  const hasPathology = wsis.length > 0;

  const buildSafeFileName = (value) =>
    (value || "rapport_final")
      .toString()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-zA-Z0-9_-]+/g, "_")
      .replace(/_+/g, "_")
      .replace(/^_|_$/g, "")
      .toLowerCase();

  const addWrappedText = (pdf, text, x, y, maxWidth, lineHeight = 6) => {
    const lines = pdf.splitTextToSize(text || "", maxWidth);
    lines.forEach((line) => {
      if (y > 280) {
        pdf.addPage();
        y = 20;
      }
      pdf.text(line, x, y);
      y += lineHeight;
    });
    return y;
  };

  const fetchCaseDetails = useCallback(async () => {
    try {
      setLoading(true);

      const authHeaders = { headers: getAuthHeaders() };

      const caseResponse = await axios.get(
        `${CASES_API}/api/cases/${caseId}`,
        authHeaders
      );
      setCase(caseResponse.data);

      try {
        const patientResponse = await axios.get(
          `${CASES_API}/api/patients/${caseResponse.data.patient_id}`,
          authHeaders
        );
        setPatient(patientResponse.data);
      } catch (err) {
        console.log("No patient found for this case");
        setPatient(null);
      }

      try {
        const workflowResponse = await axios.get(
          `${WORKFLOW_API}/api/workflows/case/${caseId}`,
          authHeaders
        );
        setWorkflow(workflowResponse.data);
      } catch (err) {
        console.log("No workflow found for this case");
        setWorkflow(null);
      }
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

      if (error.response?.status === 404) {
        toast.error("Cas introuvable");
        navigate("/dashboard");
        return;
      }

      toast.error("Erreur lors du chargement du cas");
    } finally {
      setLoading(false);
    }
  }, [caseId, getAuthHeaders, navigate]);

  const fetchReports = useCallback(async () => {
    try {
      setLoadingReports(true);

      const response = await axios.get(`${REPORTS_API}/api/reports/case/${caseId}`, {
        headers: getAuthHeaders(),
      });

      setReports(response.data);
    } catch (error) {
      console.error("Error fetching reports:", error);
      setReports([]);
    } finally {
      setLoadingReports(false);
    }
  }, [caseId, getAuthHeaders]);

  const getWorkflowProgressPercent = () => {
    if (!workflow?.specialists_order?.length) return 0;

    const total = workflow.specialists_order.length;

    if (workflow.is_completed) return 100;

    return Math.min(
      100,
      Math.round((workflow.current_step / total) * 100)
    );
  };

  const getWorkflowMemberStatus = (specialist, index) => {
    if (!workflow?.specialists_order?.length) {
      return {
        label: "Non défini",
        className: "bg-slate-100 text-slate-700",
        description: "Aucun workflow disponible",
      };
    }

    if (workflow.is_completed) {
      return {
        label: "Terminé",
        className: "bg-green-100 text-green-800",
        description: "Étape validée",
      };
    }

    if (index < workflow.current_step) {
      return {
        label: "Terminé",
        className: "bg-green-100 text-green-800",
        description: "Rapport déjà réalisé",
      };
    }

    if (index === workflow.current_step) {
      return {
        label: "En cours",
        className: "bg-blue-100 text-blue-800",
        description: "Étape actuelle",
      };
    }

    return {
      label: "En attente",
      className: "bg-yellow-100 text-yellow-800",
      description: "En attente du tour",
    };
  };

  const getWorkflowCurrentStepLabel = () => {
    if (!workflow?.specialists_order?.length) {
      return "Aucun workflow défini";
    }

    if (workflow.is_completed) {
      return `Workflow terminé (${workflow.specialists_order.length}/${workflow.specialists_order.length})`;
    }

    return `Étape ${Math.min(
      workflow.current_step + 1,
      workflow.specialists_order.length
    )}/${workflow.specialists_order.length}`;
  };

  const getWorkflowMembers = () => {
    if (workflow?.specialists_order?.length) {
      return workflow.specialists_order;
    }
    return caseData?.assigned_specialists || [];
  };

  const handleGenerateFinalConsolidatedPDF = async () => {
    if (!canGeneralistValidateFinalReport) {
      toast.error("Vous ne pouvez pas générer le rapport final consolidé");
      return;
    }

    setGeneratingFinalPDF(true);

    try {
      const pdf = new jsPDF();
      let yPos = 20;

      const ensurePage = (extra = 0) => {
        if (yPos + extra > 280) {
          pdf.addPage();
          yPos = 20;
        }
      };

      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(18);
      pdf.text("Rapport final consolidé", 20, yPos);
      yPos += 10;

      pdf.setFontSize(12);
      pdf.setFont("helvetica", "normal");
      pdf.text(`Cas : ${caseData?.id || "-"}`, 20, yPos);
      yPos += 7;
      pdf.text(`Titre : ${caseData?.title || "-"}`, 20, yPos);
      yPos += 7;
      pdf.text(`Patient : ${patient?.full_name || patient?.id || caseData?.patient_id || "-"}`, 20, yPos);
      yPos += 7;
      pdf.text(
        `Validé par le médecin généraliste : ${getCurrentUserId()}`,
        20,
        yPos
      );
      yPos += 10;

      if (patient) {
        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(14);
        ensurePage(10);
        pdf.text("Contexte patient", 20, yPos);
        yPos += 8;

        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(11);

        const patientLines = [
          `Identifiant patient : ${patient.id || "-"}`,
          `Nom : ${patient.full_name || "-"}`,
          `Âge : ${patient.age ?? "-"}`,
          `Genre : ${patient.gender || "-"}`,
          `Antécédents : ${patient.medical_history || "Non renseignés"}`,
          `Symptômes : ${patient.symptoms || "Non renseignés"}`,
        ];

        for (const line of patientLines) {
          ensurePage(8);
          yPos = addWrappedText(pdf, line, 20, yPos, 170);
          yPos += 1;
        }
        yPos += 4;
      }

      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(14);
      ensurePage(10);
      pdf.text("Synthèse des rapports spécialistes", 20, yPos);
      yPos += 10;

      const sortedReports = [...reports].sort((a, b) => {
        const aDate = new Date(a.created_at).getTime();
        const bDate = new Date(b.created_at).getTime();
        return aDate - bDate;
      });

      sortedReports.forEach((report, index) => {
        ensurePage(20);

        pdf.setFont("helvetica", "bold");
        pdf.setFontSize(13);
        pdf.text(
          `${index + 1}. ${report.title || "Rapport sans titre"}`,
          20,
          yPos
        );
        yPos += 7;

        pdf.setFont("helvetica", "normal");
        pdf.setFontSize(11);
        pdf.text(
          `Auteur : ${report.user_id} | Date : ${new Date(report.created_at).toLocaleString("fr-FR")}`,
          20,
          yPos
        );
        yPos += 8;

        const cleanedContent = (report.content || "")
          .replace(/\*\*/g, "")
          .replace(/#+/g, "")
          .trim();

        yPos = addWrappedText(pdf, cleanedContent, 20, yPos, 170, 6);
        yPos += 8;
      });

      ensurePage(20);
      pdf.setFont("helvetica", "bold");
      pdf.setFontSize(14);
      pdf.text("Conclusion consolidée", 20, yPos);
      yPos += 8;

      pdf.setFont("helvetica", "normal");
      pdf.setFontSize(11);
      yPos = addWrappedText(
        pdf,
        `L'ensemble des rapports spécialistes du cas ${caseData?.id} a été relu et validé. Ce document constitue la synthèse consolidée transmise après validation finale du médecin généraliste.`,
        20,
        yPos,
        170,
        6
      );

      const filename = `rapport_final_${buildSafeFileName(caseData?.id)}.pdf`;
      pdf.save(filename);

      setFinalPdfReady(true);
      toast.success("Rapport final consolidé généré avec succès");
    } catch (error) {
      console.error("Erreur génération rapport final consolidé:", error);
      toast.error("Erreur lors de la génération du rapport final");
    } finally {
      setGeneratingFinalPDF(false);
    }
  };

  const handleCloseCase = async () => {
    if (!canGeneralistValidateFinalReport) {
      toast.error("Vous ne pouvez pas fermer ce cas");
      return;
    }

    if (!finalPdfReady) {
      toast.error("Générez d'abord le PDF final consolidé");
      return;
    }

    const confirmed = window.confirm(
      "Confirmez-vous la fermeture définitive de ce cas ?"
    );
    if (!confirmed) return;

    try {
      setClosingCase(true);

      await axios.post(
        `${CASES_API}/api/cases/${caseId}/close`,
        {
          closed_by: getCurrentUserId(),
        },
        {
          headers: getAuthHeaders(),
        }
      );

      toast.success("Cas fermé avec succès");
      await fetchCaseDetails();
      await fetchReports();
    } catch (error) {
      console.error("Erreur fermeture du cas:", error);
      toast.error("Erreur lors de la fermeture du cas");
    } finally {
      setClosingCase(false);
    }
  };

  const fetchRadiologySeries = useCallback(
    async (patientId) => {
      if (!patientId) return;

      try {
        setRadiologyLoading(true);
        setRadiologyError(null);
        setRadiologySeries([]);
        setSelectedRadiologySeries(null);

        const res = await axios.get(
          `${IMAGES_API}/api/radiology/patients/${encodeURIComponent(patientId)}/series`,
          { headers: getAuthHeaders() }
        );

        const list = res.data || [];
        setRadiologySeries(list);
        setSelectedRadiologySeries(list.length > 0 ? list[0] : null);
      } catch (error) {
        console.error("Error loading radiology series:", error);
        setRadiologyError(error);
        setRadiologySeries([]);
        setSelectedRadiologySeries(null);
      } finally {
        setRadiologyLoading(false);
      }
    },
    [getAuthHeaders]
  );

  const fetchWsis = useCallback(
    async (patientId) => {
      if (!patientId) return;

      try {
        setWsiLoading(true);
        setWsiError(null);
        setWsis([]);
        setSelectedWsi(null);

        const res = await axios.get(
          `${IMAGES_API}/api/debug/wsi-dzi?patient_id=${encodeURIComponent(patientId)}`,
          { headers: getAuthHeaders() }
        );

        const list = res.data?.wsis || res.data?.slides || [];
        setWsis(list);
        setSelectedWsi(list.length > 0 ? list[0] : null);
      } catch (e) {
        console.error("Error loading WSI/DZI:", e);
        setWsiError(e);
        setWsis([]);
        setSelectedWsi(null);
      } finally {
        setWsiLoading(false);
      }
    },
    [getAuthHeaders]
  );

  const fetchDiscussionMessages = useCallback(async () => {
    try {
      setDiscussionLoading(true);

      const response = await axios.get(
        `${CASES_API}/api/discussions/case/${caseId}`,
        { headers: getAuthHeaders() }
      );

      setDiscussionMessages(response.data || []);
    } catch (error) {
      console.error("Error fetching discussion messages:", error);
      setDiscussionMessages([]);
    } finally {
      setDiscussionLoading(false);
    }
  }, [caseId, getAuthHeaders]);

  const handleSendDiscussionMessage = async () => {
    const content = discussionInput.trim();
    if (!content) return;

    try {
      setSendingDiscussion(true);

      const response = await axios.post(
        `${CASES_API}/api/discussions/case/${caseId}`,
        { content },
        { headers: getAuthHeaders() }
      );

      setDiscussionMessages((prev) => [...prev, response.data]);
      setDiscussionInput("");
    } catch (error) {
      console.error("Error sending discussion message:", error);
      toast.error("Erreur lors de l'envoi du message");
    } finally {
      setSendingDiscussion(false);
    }
  };

  useEffect(() => {
    fetchCaseDetails();
    fetchReports();
  }, [fetchCaseDetails, fetchReports]);

  useEffect(() => {
    if (!patient?.id) return;
    fetchWsis(patient.id);
    fetchRadiologySeries(patient.id);
  }, [patient?.id, fetchWsis, fetchRadiologySeries]);

  useEffect(() => {
    fetchDiscussionMessages();
  }, [fetchDiscussionMessages]);

  useEffect(() => {
    if (!patient?.id) return;

    if (hasPathology && !hasRadiology && imageMode !== "pathology") {
      setImageMode("pathology");
      return;
    }

    if (hasRadiology && !hasPathology && imageMode !== "radiology") {
      setImageMode("radiology");
      return;
    }

    if (!hasPathology && !hasRadiology && imageMode !== "pathology") {
      setImageMode("pathology");
    }
  }, [patient?.id, hasPathology, hasRadiology, imageMode]);

  const viewerSource = useMemo(() => {
    if (!patient?.id || !selectedWsi?.wsi_id) return null;

    return {
      type: "dzi",
      url: `${IMAGES_API}/api/wsi/patients/${encodeURIComponent(
        patient.id
      )}/${encodeURIComponent(selectedWsi.wsi_id)}/dzi`,
      key: `${patient.id}:${selectedWsi.wsi_id}`,
    };
  }, [patient?.id, selectedWsi?.wsi_id]);

  const canCreateReport = () => {
    if (!workflow || !workflow.specialists_order) return false;

    const currentUserRole = getCurrentUserRole();
    if (currentUserRole === "medecin_generaliste") return false;
    if (isAdmin()) return false;

    const currentUserId = getCurrentUserId();
    const isSpecialist = workflow.specialists_order.includes(currentUserId);
    const isCurrentSpecialist =
      workflow.specialists_order[workflow.current_step] === currentUserId;

    return isSpecialist && isCurrentSpecialist;
  };

  const canEditReport = (reportUserId) => {
    const currentUserId = getCurrentUserId();
    const currentUserRole = getCurrentUserRole();
    if (currentUserRole === "medecin_generaliste") return false;
    if (isAdmin()) return false;
    return currentUserId === reportUserId;
  };

  const canDeleteReport = (reportUserId) => {
    const currentUserId = getCurrentUserId();
    if (isAdmin()) return false;
    return currentUserId === reportUserId;
  };

  const getCurrentSpecialist = () => {
    if (!workflow || !workflow.specialists_order) return null;
    return workflow.specialists_order[workflow.current_step];
  };

  const getSpecialistStep = (reportUserId) => {
    if (!workflow || !workflow.specialists_order) return null;

    const specialistIndex = workflow.specialists_order.findIndex(
      (specialist) => specialist === reportUserId
    );

    if (specialistIndex === -1) return null;

    return {
      step: specialistIndex + 1,
      totalSteps: workflow.specialists_order.length,
      isCurrentStep: specialistIndex === workflow.current_step,
      isCompleted: specialistIndex < workflow.current_step,
    };
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
        headers: getAuthHeaders(),
      });

      toast.success("Rapport supprimé avec succès");
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

  const handleRadiologyFileChange = (e) => {
    const files = Array.from(e.target.files || []);
    setRadiologyUploadFiles(files);
  };

  const handleRadiologyUpload = async () => {
    if (!patient?.id) {
      toast.error("Patient introuvable");
      return;
    }

    if (!radiologyUploadFiles.length) {
      toast.error("Sélectionnez au moins un fichier DICOM");
      return;
    }

    try {
      setRadiologyUploading(true);

      const form = new FormData();
      radiologyUploadFiles.forEach((f) => form.append("files", f));

      const currentUserId = getCurrentUserId();

      await axios.post(
        `${IMAGES_API}/api/radiology/upload?patient_id=${encodeURIComponent(
          patient.id
        )}&uploaded_by=${encodeURIComponent(currentUserId)}`,
        form,
        {
          headers: {
            "Content-Type": "multipart/form-data",
            ...getAuthHeaders(),
          },
        }
      );

      toast.success("Images radiologiques importées avec succès");
      setRadiologyUploadFiles([]);
      await fetchRadiologySeries(patient.id);
      setImageMode("radiology");
    } catch (error) {
      console.error("Error uploading radiology images:", error);
      toast.error("Erreur lors de l'import des images radiologiques");
    } finally {
      setRadiologyUploading(false);
    }
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

      pdf.setFontSize(18);
      pdf.setFont("helvetica", "bold");
      ensurePage(10);
      pdf.text(`Rapport d'analyse - ${caseData.id}`, 20, yPos);
      yPos += 10;

      pdf.setFontSize(12);
      pdf.setFont("helvetica", "normal");
      ensurePage(8);
      pdf.text(
        `Par ${report.user_id} • ${new Date(report.created_at).toLocaleDateString("fr-FR")}`,
        20,
        yPos
      );
      yPos += 8;

      pdf.setFontSize(14);
      pdf.setFont("helvetica", "bold");
      ensurePage(12);
      pdf.text(`Titre: ${report.title}`, 20, yPos);
      yPos += 12;

      pdf.setFontSize(12);
      pdf.setFont("helvetica", "normal");

      const lines = report.content.split("\n");
      for (const line of lines) {
        if (line.trim()) {
          if (line.startsWith("**") && line.endsWith("**")) {
            pdf.setFont("helvetica", "bold");
            const title = line.replace(/\*\*/g, "");
            ensurePage(8);
            pdf.text(title, 20, yPos);
            yPos += 8;
          } else {
            pdf.setFont("helvetica", "normal");
            const splitText = pdf.splitTextToSize(line, 170);
            for (const textLine of splitText) {
              ensurePage(6);
              pdf.text(textLine, 20, yPos);
              yPos += 6;
            }
          }
        } else {
          ensurePage(4);
          yPos += 4;
        }
      }

      pdf.save(
        `rapport_${report.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}.pdf`
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
                <h1 className="text-2xl font-bold text-slate-900">{caseData.id}</h1>
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

            {canCreateReport() && !isClosed && (
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

          <TabsContent value="overview" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Informations du cas</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-medium text-slate-500">ID du cas</p>
                    <p className="text-base text-slate-900">{caseData.id}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">Titre</p>
                    <p className="text-base text-slate-900">{caseData.title}</p>
                  </div>
                  <div>
                    <p className="text-sm font-medium text-slate-500">ID Patient</p>
                    <p className="text-base text-slate-900">{caseData.patient_id}</p>
                  </div>
                  {patient && (
                    <div>
                      <p className="text-sm font-medium text-slate-500">
                        Date de naissance
                      </p>
                      <p className="text-base text-slate-900">
                        {new Date(patient.date_of_birth).toLocaleDateString("fr-FR")}
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
                    <p className="text-sm font-medium text-slate-500">Description</p>
                    <p className="text-base text-slate-900">
                      {caseData.description || "Aucune description"}
                    </p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-500">Créé par</p>
                    <p className="text-base text-slate-900">{caseData.created_by}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm font-medium text-slate-500">
                      Date de création
                    </p>
                    <p className="text-base text-slate-900">
                      {new Date(caseData.created_at).toLocaleDateString("fr-FR")}
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
                      <p className="text-sm font-medium text-slate-500">Nom complet</p>
                      <p className="text-base text-slate-900">{patient.full_name}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">ID Patient</p>
                      <p className="text-base text-slate-900">{patient.id}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">Âge</p>
                      <p className="text-base text-slate-900">{patient.age} ans</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-slate-500">Genre</p>
                      <p className="text-base text-slate-900">{patient.gender}</p>
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
                        <p className="text-base text-slate-900">{patient.symptoms}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          <TabsContent value="images" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Imagerie du patient</CardTitle>
              </CardHeader>

              <CardContent className="space-y-4">
                <div className="flex flex-col gap-3">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-600">Patient :</span>
                      <Badge variant="outline">{patient?.full_name || patient?.id}</Badge>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant={imageMode === "pathology" ? "default" : "outline"}
                        onClick={() => setImageMode("pathology")}
                        disabled={!hasPathology}
                      >
                        Pathologie
                      </Button>

                      <Button
                        variant={imageMode === "radiology" ? "default" : "outline"}
                        onClick={() => setImageMode("radiology")}
                        disabled={!hasRadiology && !patient?.id}
                      >
                        Radiologie
                      </Button>
                    </div>
                  </div>

                  {!hasPathology && !hasRadiology && !wsiLoading && !radiologyLoading && (
                    <div className="text-sm text-slate-500">
                      Aucune imagerie disponible pour ce patient pour le moment.
                    </div>
                  )}

                  {imageMode === "pathology" ? (
                    <>
                      <div className="flex flex-col md:flex-row md:items-center gap-3">
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

                          <span className="text-xs text-slate-500">{wsis.length} WSI</span>
                        </div>
                      </div>

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

                      {!wsiLoading && !wsiError && wsis.length === 0 && (
                        <div className="text-sm text-slate-500">
                          Aucune image de pathologie disponible pour ce patient.
                        </div>
                      )}

                      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                        <div className="h-[70vh] min-h-[520px]">
                          {!viewerSource ? (
                            <div className="h-full flex items-center justify-center text-slate-500">
                              Sélectionnez une image WSI.
                            </div>
                          ) : (
                            <OpenSeadragonUrlViewer
                              key={viewerSource.key}
                              sourceType={viewerSource.type}
                              sourceUrl={viewerSource.url}
                              imageKey={viewerSource.key}
                              imageId={selectedWsi?.wsi_id}
                              caseId={caseData?.id}
                            />
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="flex flex-col gap-4">
                        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
                            <input
                              type="file"
                              multiple
                              accept=".dcm,application/dicom"
                              onChange={handleRadiologyFileChange}
                              className="block w-full text-sm text-slate-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
                            />

                            <Button
                              onClick={handleRadiologyUpload}
                              disabled={radiologyUploading || !radiologyUploadFiles.length}
                            >
                              <Upload className="h-4 w-4 mr-2" />
                              {radiologyUploading ? "Import..." : "Importer DICOM"}
                            </Button>
                          </div>

                          <div className="text-sm text-slate-500">
                            {radiologyUploadFiles.length > 0
                              ? `${radiologyUploadFiles.length} fichier(s) sélectionné(s)`
                              : "Aucun fichier sélectionné"}
                          </div>
                        </div>

                        <div className="flex flex-col md:flex-row md:items-center gap-3">
                          <div className="flex-1" />
                          <div className="flex items-center gap-2">
                            <span className="text-sm text-slate-600">Série :</span>

                            <select
                              className="border border-slate-200 rounded-md px-3 py-2 bg-white text-sm min-w-[320px]"
                              disabled={radiologyLoading || radiologySeries.length === 0}
                              value={selectedRadiologySeries?.orthanc_series_id || ""}
                              onChange={(e) => {
                                const s = radiologySeries.find(
                                  (x) => x.orthanc_series_id === e.target.value
                                );
                                setSelectedRadiologySeries(s || null);
                              }}
                            >
                              {radiologySeries.length === 0 ? (
                                <option value="">Aucune série radiologique disponible</option>
                              ) : (
                                radiologySeries.map((s) => (
                                  <option
                                    key={s.orthanc_series_id}
                                    value={s.orthanc_series_id}
                                  >
                                    {[s.modality, s.study_date, s.series_description]
                                      .filter(Boolean)
                                      .join(" · ") || s.orthanc_series_id}
                                  </option>
                                ))
                              )}
                            </select>

                            <span className="text-xs text-slate-500">
                              {radiologySeries.length} série(s)
                            </span>
                          </div>
                        </div>
                      </div>

                      {radiologyLoading && (
                        <div className="text-sm text-slate-600">
                          Chargement des séries radiologiques…
                        </div>
                      )}

                      {!radiologyLoading && radiologyError && (
                        <div className="text-sm text-red-600">
                          Impossible de charger les séries radiologiques pour ce patient.
                        </div>
                      )}

                      {!radiologyLoading && !radiologyError && radiologySeries.length === 0 && (
                        <div className="text-sm text-slate-500">
                          Aucune série radiologique disponible pour ce patient.
                        </div>
                      )}

                      <div className="border border-slate-200 rounded-lg overflow-hidden bg-white">
                        <div className="h-[70vh] min-h-[520px]">
                          <CornerstoneViewer series={selectedRadiologySeries} />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="reports">
            <Card>
              <CardHeader>
                <CardTitle>Rapports des spécialistes</CardTitle>
              </CardHeader>

              {canGeneralistValidateFinalReport && (
                <Card className="mb-6 border-green-200 bg-green-50">
                  <CardContent className="pt-6">
                    <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 mb-2">
                          <FileCheck className="h-5 w-5 text-green-700" />
                          <h3 className="text-lg font-semibold text-green-900">
                            Validation finale du médecin généraliste
                          </h3>
                        </div>
                        <p className="text-sm text-green-800">
                          Tous les rapports spécialistes sont finalisés. Vous pouvez générer
                          un PDF final consolidé, le relire, puis fermer définitivement le cas.
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <Button
                          onClick={handleGenerateFinalConsolidatedPDF}
                          disabled={generatingFinalPDF}
                          className="bg-green-600 hover:bg-green-700 text-white"
                        >
                          <Download className="h-4 w-4 mr-2" />
                          {generatingFinalPDF ? "Génération..." : "Générer le PDF final"}
                        </Button>

                        {false && (
                          <Button
                            variant="outline"
                            onClick={handleCloseCase}
                            disabled={!finalPdfReady || closingCase}
                            className="border-slate-300"
                          >
                            <Lock className="h-4 w-4 mr-2" />
                            {closingCase ? "Fermeture..." : "Fermer le cas"}
                          </Button>
                        )}
                      </div>
                    </div>

                    {!finalPdfReady && (
                      <p className="text-xs text-slate-600 mt-3">
                        Le cas ne pourra être fermé qu’après génération du PDF final consolidé.
                      </p>
                    )}

                    {finalPdfReady && (
                      <div className="mt-3 flex items-center gap-2 text-sm text-green-700">
                        <CheckCircle2 className="h-4 w-4" />
                        PDF final prêt. Vous pouvez maintenant fermer le cas.
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}

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
                      <Button onClick={() => navigate(`/cases/${caseId}/report`)}>
                        <FileText className="h-4 w-4 mr-2" />
                        Créer mon rapport
                      </Button>
                    ) : (
                      <div className="text-sm text-slate-500">
                        {workflow && getCurrentSpecialist() ? (
                          <p>En attente du rapport de Dr. {getCurrentSpecialist()}</p>
                        ) : (
                          <p>Vous n'êtes pas assigné à ce cas</p>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="space-y-4">
                    {reports.map((report) => {
                      const specialistStep = getSpecialistStep(report.user_id);

                      return (
                        <Card key={report.id} className="border border-slate-200">
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
                                    </p>
                                  </div>
                                </div>

                                <p className="text-sm text-slate-500 ml-10">
                                  {new Date(report.created_at).toLocaleDateString("fr-FR")} à{" "}
                                  {new Date(report.created_at).toLocaleTimeString("fr-FR", {
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
                                      navigate(`/cases/${caseId}/report/${report.id}`)
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
                                      handleDeleteReport(report.id, report.user_id)
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
                      {canCreateReport() ? (
                        <Button onClick={() => navigate(`/cases/${caseId}/report`)}>
                          <FileText className="h-4 w-4 mr-2" />
                          Ajouter mon rapport
                        </Button>
                      ) : (
                        <div className="text-sm text-slate-500 text-center">
                          {workflow && getCurrentSpecialist() ? (
                            <p>En attente du rapport de Dr. {getCurrentSpecialist()}</p>
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

          <TabsContent value="team">
            <div className="space-y-6">
              <Card>
                <CardHeader>
                  <CardTitle>Workflow du cas</CardTitle>
                </CardHeader>

                <CardContent className="space-y-6">
                  {!workflow || !workflow.specialists_order?.length ? (
                    <div className="text-sm text-slate-500">
                      Aucun workflow disponible pour ce cas.
                    </div>
                  ) : (
                    <>
                      <div className="space-y-3">
                        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-2">
                          <div>
                            <p className="text-sm font-medium text-slate-900">
                              {getWorkflowCurrentStepLabel()}
                            </p>
                            <p className="text-sm text-slate-500">
                              {workflow.is_completed
                                ? "Tous les spécialistes ont terminé leur étape."
                                : `Spécialiste actuel : Dr. ${getCurrentSpecialist() || "-"}`}
                            </p>
                          </div>

                          <Badge className={workflow.is_completed
                            ? "bg-green-100 text-green-800"
                            : "bg-blue-100 text-blue-800"
                          }>
                            {workflow.is_completed ? "Workflow terminé" : "Workflow en cours"}
                          </Badge>
                        </div>

                        <div className="w-full h-3 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-blue-600 transition-all duration-300"
                            style={{ width: `${getWorkflowProgressPercent()}%` }}
                          />
                        </div>

                        <p className="text-xs text-slate-500">
                          Progression : {getWorkflowProgressPercent()} %
                        </p>
                      </div>

                      <div className="space-y-3">
                        <h3 className="text-sm font-semibold text-slate-900">
                          Liste des spécialistes
                        </h3>

                        <div className="space-y-3">
                          {getWorkflowMembers().map((specialist, index) => {
                            const status = getWorkflowMemberStatus(specialist, index);

                            return (
                              <div
                                key={`${specialist}-${index}`}
                                className="flex items-center justify-between gap-4 p-4 border border-slate-200 rounded-lg bg-white"
                              >
                                <div className="flex items-center gap-3">
                                  <div
                                    className={`w-10 h-10 rounded-full flex items-center justify-center font-bold ${
                                      status.label === "Terminé"
                                        ? "bg-green-100 text-green-700"
                                        : status.label === "En cours"
                                          ? "bg-blue-100 text-blue-700"
                                          : "bg-yellow-100 text-yellow-700"
                                    }`}
                                  >
                                    {index + 1}
                                  </div>

                                  <div>
                                    <p className="font-medium text-slate-900">
                                      Dr. {specialist}
                                    </p>
                                    <p className="text-sm text-slate-500">
                                      Position {index + 1}
                                    </p>
                                  </div>
                                </div>

                                <div className="flex flex-col items-end gap-1">
                                  <Badge className={status.className}>{status.label}</Badge>
                                  <span className="text-xs text-slate-500">
                                    {status.description}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </>
                  )}
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          <TabsContent value="discussion">
            <Card>
              <CardHeader>
                <CardTitle>Discussion du cas</CardTitle>
              </CardHeader>

              <CardContent className="pt-6">
                <div className="flex flex-col gap-4">
                  <div className="border border-slate-200 rounded-lg bg-slate-50 p-4 h-[50vh] overflow-y-auto">
                    {discussionLoading ? (
                      <p className="text-center text-slate-500">Chargement des messages...</p>
                    ) : discussionMessages.length === 0 ? (
                      <p className="text-center text-slate-500">
                        Aucun message pour le moment
                      </p>
                    ) : (
                      <div className="space-y-3">
                        {discussionMessages.map((message) => {
                          const isMine = message.user_id === getCurrentUserId();

                          return (
                            <div
                              key={message.id}
                              className={`flex ${isMine ? "justify-end" : "justify-start"}`}
                            >
                              <div
                                className={`max-w-[75%] rounded-lg px-4 py-3 shadow-sm ${
                                  isMine
                                    ? "bg-blue-600 text-white"
                                    : "bg-white border border-slate-200 text-slate-900"
                                }`}
                              >
                                <div className="text-xs font-semibold mb-1 opacity-90">
                                  {message.user_id}
                                </div>

                                <p className="text-sm whitespace-pre-wrap break-words">
                                  {message.content}
                                </p>

                                <div
                                  className={`text-[11px] mt-2 ${
                                    isMine ? "text-blue-100" : "text-slate-500"
                                  }`}
                                >
                                  {new Date(message.created_at).toLocaleDateString("fr-FR")} à{" "}
                                  {new Date(message.created_at).toLocaleTimeString("fr-FR", {
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  <div className="flex gap-3">
                    <textarea
                      value={discussionInput}
                      onChange={(e) => setDiscussionInput(e.target.value)}
                      placeholder="Tapez votre message..."
                      rows={3}
                      className="flex-1 border border-slate-200 rounded-md px-3 py-2 bg-white text-sm resize-none"
                    />

                    <Button
                      onClick={handleSendDiscussionMessage}
                      disabled={sendingDiscussion || !discussionInput.trim()}
                    >
                      {sendingDiscussion ? "Envoi..." : "Envoyer"}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default CaseDetail;