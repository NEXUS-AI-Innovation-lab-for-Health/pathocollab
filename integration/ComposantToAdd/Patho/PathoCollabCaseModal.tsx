import React from "react";
import { X } from "lucide-react";

type PathoCollabCaseModalProps = {
  open: boolean;
  title?: string;
  caseId?: string | null;
  onClose: () => void;
  children: React.ReactNode;
};

export default function PathoCollabCaseModal({
  open,
  title = "Analyse PathoCollab",
  caseId,
  onClose,
  children,
}: PathoCollabCaseModalProps) {
  if (!open) return null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 9999,
        background: "rgba(15, 23, 42, 0.72)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
      }}
    >
      <div
        style={{
          width: "min(1500px, 100%)",
          height: "92vh",
          background: "#fff",
          borderRadius: 16,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 24px 80px rgba(0,0,0,0.35)",
        }}
      >
        <div
          style={{
            height: 56,
            padding: "0 18px",
            borderBottom: "1px solid #e5e7eb",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 12,
          }}
        >
          <div>
            <div style={{ fontWeight: 700, color: "#111827" }}>{title}</div>
            {caseId && (
              <div style={{ fontSize: 12, color: "#6b7280", marginTop: 2 }}>
                Cas : {caseId}
              </div>
            )}
          </div>

          <button
            onClick={onClose}
            type="button"
            aria-label="Fermer"
            style={{
              width: 38,
              height: 38,
              borderRadius: 10,
              border: "1px solid #e5e7eb",
              background: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <X size={20} />
          </button>
        </div>

        <div style={{ flex: 1, minHeight: 0, overflow: "auto", background: "#f8fafc" }}>
          {children}
        </div>
      </div>
    </div>
  );
}
