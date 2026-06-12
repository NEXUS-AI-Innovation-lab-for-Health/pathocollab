import React, { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";
import OpenSeadragonUrlViewer from "./OpenSeadragonUrlViewer";

type ApiBaseUrls = {
  cases?: string;
  workflow?: string;
  images?: string;
  reports?: string;
};

type WsiItem = {
  wsi_id: string;
  filename?: string;
  dzi_url?: string;
};

type PathoCollabExternalCaseDetailProps = {
  caseId: string;
  apiBaseUrls?: ApiBaseUrls;
  currentUserId?: string;
};

const defaultApiBaseUrls: Required<ApiBaseUrls> = {
  cases: "http://localhost:18002",
  workflow: "http://localhost:18003",
  images: "http://localhost:18004",
  reports: "http://localhost:18005",
};

function joinUrl(baseUrl: string, path: string) {
  return `${baseUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

function badgeStyle(status?: string): React.CSSProperties {
  const common: React.CSSProperties = {
    display: "inline-flex",
    alignItems: "center",
    borderRadius: 999,
    padding: "4px 10px",
    fontSize: 12,
    fontWeight: 700,
  };

  switch (status) {
    case "completed":
      return { ...common, background: "#dcfce7", color: "#166534" };
    case "in_progress":
      return { ...common, background: "#dbeafe", color: "#1d4ed8" };
    case "closed":
      return { ...common, background: "#e5e7eb", color: "#374151" };
    case "cancelled":
      return { ...common, background: "#fee2e2", color: "#b91c1c" };
    default:
      return { ...common, background: "#fef3c7", color: "#92400e" };
  }
}

function statusLabel(status?: string) {
  const labels: Record<string, string> = {
    pending: "En attente",
    in_progress: "En cours",
    completed: "Terminé",
    cancelled: "Annulé",
    closed: "Fermé",
  };
  return status ? labels[status] || status : "-";
}

export default function PathoCollabExternalCaseDetail({
  caseId,
  apiBaseUrls,
  currentUserId = "external-user",
}: PathoCollabExternalCaseDetailProps) {
  const api = { ...defaultApiBaseUrls, ...(apiBaseUrls || {}) };

  const [activeTab, setActiveTab] = useState<"overview" | "images" | "reports" | "team" | "discussion">("overview");
  const [caseData, setCaseData] = useState<any>(null);
  const [patient, setPatient] = useState<any>(null);
  const [workflow, setWorkflow] = useState<any>(null);
  const [reports, setReports] = useState<any[]>([]);
  const [wsis, setWsis] = useState<WsiItem[]>([]);
  const [selectedWsi, setSelectedWsi] = useState<WsiItem | null>(null);
  const [messages, setMessages] = useState<any[]>([]);
  const [messageInput, setMessageInput] = useState("");

  const [loading, setLoading] = useState(true);
  const [wsiLoading, setWsiLoading] = useState(false);
  const [reportTitle, setReportTitle] = useState("");
  const [reportContent, setReportContent] = useState("");
  const [savingReport, setSavingReport] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCase = useCallback(async () => {
    if (!caseId) return;

    try {
      setLoading(true);
      setError(null);

      const caseRes = await axios.get(joinUrl(api.cases, `/api/cases/external/${encodeURIComponent(caseId)}`));
      setCaseData(caseRes.data);

      const patientId = caseRes.data?.patient_id;
      if (patientId) {
        try {
          const patientRes = await axios.get(joinUrl(api.cases, `/api/patients/${encodeURIComponent(patientId)}`));
          setPatient(patientRes.data);
        } catch {
          setPatient(null);
        }
      }

      try {
        const workflowRes = await axios.get(joinUrl(api.workflow, `/api/workflows/case/${encodeURIComponent(caseId)}`));
        setWorkflow(workflowRes.data);
      } catch {
        setWorkflow(null);
      }
    } catch (err) {
      console.error("Erreur chargement cas PathoCollab:", err);
      setError("Impossible de charger le cas PathoCollab.");
    } finally {
      setLoading(false);
    }
  }, [api.cases, api.workflow, caseId]);

  const fetchWsis = useCallback(async (patientId: string) => {
    try {
      setWsiLoading(true);
      const res = await axios.get(joinUrl(api.images, `/api/wsi/patients/${encodeURIComponent(patientId)}/wsis`));
      const list = res.data?.wsis || [];
      setWsis(list);
      setSelectedWsi(list.length ? list[0] : null);
    } catch (err) {
      console.error("Erreur chargement WSI PathoCollab:", err);
      setWsis([]);
      setSelectedWsi(null);
    } finally {
      setWsiLoading(false);
    }
  }, [api.images]);

  const fetchReports = useCallback(async () => {
    try {
      const res = await axios.get(joinUrl(api.reports, `/api/reports/case/${encodeURIComponent(caseId)}`));
      setReports(Array.isArray(res.data) ? res.data : []);
    } catch {
      setReports([]);
    }
  }, [api.reports, caseId]);

  const fetchMessages = useCallback(async () => {
    try {
      const res = await axios.get(joinUrl(api.cases, `/api/discussions/case/${encodeURIComponent(caseId)}`));
      setMessages(Array.isArray(res.data) ? res.data : []);
    } catch {
      setMessages([]);
    }
  }, [api.cases, caseId]);

  useEffect(() => {
    fetchCase();
    fetchReports();
    fetchMessages();
  }, [fetchCase, fetchReports, fetchMessages]);

  useEffect(() => {
    if (caseData?.patient_id) fetchWsis(caseData.patient_id);
  }, [caseData?.patient_id, fetchWsis]);

  const viewerSource = useMemo(() => {
    if (!caseData?.patient_id || !selectedWsi?.wsi_id) return null;
    return joinUrl(
      api.images,
      `/api/wsi/patients/${encodeURIComponent(caseData.patient_id)}/${encodeURIComponent(selectedWsi.wsi_id)}/dzi`
    );
  }, [api.images, caseData?.patient_id, selectedWsi?.wsi_id]);

  const createReport = async () => {
    if (!reportTitle.trim() || !reportContent.trim()) return;

    try {
      setSavingReport(true);
      await axios.post(joinUrl(api.reports, "/api/reports/"), {
        case_id: caseId,
        title: reportTitle.trim(),
        content: reportContent.trim(),
        user_id: currentUserId,
        is_final: false,
      });
      setReportTitle("");
      setReportContent("");
      await fetchReports();
    } catch (err) {
      console.error("Erreur création rapport PathoCollab:", err);
      alert("Impossible de créer le rapport PathoCollab.");
    } finally {
      setSavingReport(false);
    }
  };

  const sendMessage = async () => {
    const content = messageInput.trim();
    if (!content) return;

    try {
      setSendingMessage(true);
      const res = await axios.post(joinUrl(api.cases, `/api/discussions/external/case/${encodeURIComponent(caseId)}`), {
        author: currentUserId,
        content,
      });
      setMessages((prev) => [...prev, res.data]);
      setMessageInput("");
    } catch (err) {
      console.error("Erreur envoi message PathoCollab:", err);
      alert("Impossible d'envoyer le message.");
    } finally {
      setSendingMessage(false);
    }
  };

  if (loading) {
    return <div style={{ padding: 24 }}>Chargement du cas PathoCollab...</div>;
  }

  if (error || !caseData) {
    return <div style={{ padding: 24, color: "#dc2626" }}>{error || "Cas introuvable."}</div>;
  }

  return (
    <div style={{ padding: 24, color: "#0f172a" }}>
      <div style={{ marginBottom: 18, display: "flex", justifyContent: "space-between", gap: 16 }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 24, fontWeight: 800 }}>{caseData.id}</h2>
          <p style={{ margin: "6px 0 0", color: "#64748b" }}>{caseData.title}</p>
        </div>
        <span style={badgeStyle(caseData.status)}>{statusLabel(caseData.status)}</span>
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 18 }}>
        {[
          ["overview", "Vue d'ensemble"],
          ["images", "Images / annotations"],
          ["reports", "Rapports"],
          ["team", "Workflow"],
          ["discussion", "Discussion"],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setActiveTab(key as any)}
            style={{
              border: "1px solid #cbd5e1",
              background: activeTab === key ? "#2563eb" : "#fff",
              color: activeTab === key ? "#fff" : "#0f172a",
              borderRadius: 10,
              padding: "9px 12px",
              cursor: "pointer",
              fontWeight: 700,
            }}
          >
            {label}
          </button>
        ))}
      </div>

      {activeTab === "overview" && (
        <section style={cardStyle}>
          <h3>Informations du cas</h3>
          <Info label="Cas" value={caseData.id} />
          <Info label="Patient" value={patient?.full_name || caseData.patient_id} />
          <Info label="Description" value={caseData.description || "Aucune description"} />
          <Info label="Créé par" value={caseData.created_by || "external"} />
          {patient && (
            <>
              <Info label="Âge" value={patient.age ? `${patient.age} ans` : "-"} />
              <Info label="Genre" value={patient.gender || "-"} />
              <Info label="Antécédents" value={patient.medical_history || "-"} />
              <Info label="Symptômes" value={patient.symptoms || "-"} />
            </>
          )}
        </section>
      )}

      {activeTab === "images" && (
        <section style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Images du patient</h3>
            <select
              disabled={wsiLoading || wsis.length === 0}
              value={selectedWsi?.wsi_id || ""}
              onChange={(e) => setSelectedWsi(wsis.find((w) => w.wsi_id === e.target.value) || null)}
              style={{ padding: 8, borderRadius: 8, border: "1px solid #cbd5e1", minWidth: 260 }}
            >
              {wsis.length === 0 ? <option>Aucune WSI disponible</option> : wsis.map((w) => (
                <option key={w.wsi_id} value={w.wsi_id}>{w.filename || w.wsi_id}</option>
              ))}
            </select>
          </div>

          {wsiLoading && <p>Chargement des images...</p>}
          {!wsiLoading && !viewerSource && <p style={{ color: "#64748b" }}>Aucune image disponible pour ce patient.</p>}
          {viewerSource && (
            <div style={{ height: "70vh", minHeight: 520, border: "1px solid #e5e7eb", borderRadius: 12, overflow: "hidden" }}>
              <OpenSeadragonUrlViewer
                sourceType="dzi"
                sourceUrl={viewerSource}
                imageKey={`${caseData.patient_id}:${selectedWsi?.wsi_id}`}
                imageId={selectedWsi?.wsi_id}
                caseId={caseId}
                currentUserId={currentUserId}
                apiBaseUrl={api.images}
              />
            </div>
          )}
        </section>
      )}

      {activeTab === "reports" && (
        <section style={cardStyle}>
          <h3>Rapports</h3>
          <div style={{ display: "grid", gap: 10, marginBottom: 18 }}>
            <input value={reportTitle} onChange={(e) => setReportTitle(e.target.value)} placeholder="Titre du rapport" style={inputStyle} />
            <textarea value={reportContent} onChange={(e) => setReportContent(e.target.value)} placeholder="Contenu du rapport" rows={6} style={inputStyle} />
            <button onClick={createReport} disabled={savingReport || !reportTitle.trim() || !reportContent.trim()} style={primaryButtonStyle}>
              {savingReport ? "Enregistrement..." : "Créer un rapport"}
            </button>
          </div>
          {reports.length === 0 ? <p>Aucun rapport.</p> : reports.map((r) => (
            <div key={r.id} style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, marginBottom: 10 }}>
              <strong>{r.title}</strong>
              <p style={{ color: "#64748b", fontSize: 13 }}>Auteur : {r.user_id}</p>
              <p style={{ whiteSpace: "pre-wrap" }}>{r.content}</p>
            </div>
          ))}
        </section>
      )}

      {activeTab === "team" && (
        <section style={cardStyle}>
          <h3>Workflow</h3>
          {!workflow?.specialists_order?.length ? <p>Aucun workflow disponible.</p> : workflow.specialists_order.map((s: string, i: number) => (
            <div key={`${s}-${i}`} style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 12, marginBottom: 8 }}>
              <strong>{i + 1}. {s}</strong>
              <div style={{ color: "#64748b", fontSize: 13 }}>
                {workflow.current_step === i ? "Étape en cours" : i < workflow.current_step ? "Terminé" : "En attente"}
              </div>
            </div>
          ))}
        </section>
      )}

      {activeTab === "discussion" && (
        <section style={cardStyle}>
          <h3>Discussion</h3>
          <div style={{ height: 300, overflow: "auto", border: "1px solid #e5e7eb", borderRadius: 10, padding: 12, marginBottom: 12 }}>
            {messages.length === 0 ? <p>Aucun message.</p> : messages.map((m) => (
              <div key={m.id || `${m.user_id}-${m.created_at}`} style={{ marginBottom: 10 }}>
                <strong>{m.user_id || "Utilisateur"}</strong>
                <p style={{ margin: "4px 0", whiteSpace: "pre-wrap" }}>{m.content}</p>
              </div>
            ))}
          </div>
          <textarea value={messageInput} onChange={(e) => setMessageInput(e.target.value)} rows={3} placeholder="Message..." style={inputStyle} />
          <button onClick={sendMessage} disabled={sendingMessage || !messageInput.trim()} style={{ ...primaryButtonStyle, marginTop: 8 }}>
            {sendingMessage ? "Envoi..." : "Envoyer"}
          </button>
        </section>
      )}
    </div>
  );
}

function Info({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: "#64748b", textTransform: "uppercase" }}>{label}</div>
      <div style={{ marginTop: 3 }}>{value}</div>
    </div>
  );
}

const cardStyle: React.CSSProperties = {
  background: "#fff",
  border: "1px solid #e5e7eb",
  borderRadius: 14,
  padding: 18,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  border: "1px solid #cbd5e1",
  borderRadius: 10,
  padding: 10,
  fontSize: 14,
  boxSizing: "border-box",
};

const primaryButtonStyle: React.CSSProperties = {
  border: "none",
  background: "#2563eb",
  color: "#fff",
  borderRadius: 10,
  padding: "10px 14px",
  fontWeight: 700,
  cursor: "pointer",
};
