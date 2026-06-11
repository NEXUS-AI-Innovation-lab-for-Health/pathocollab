import React, { useEffect, useMemo, useState } from "react";
import OpenSeadragon from "openseadragon";

type WsiItem = {
  wsi_id: string;
  filename?: string;
};

type PathoCollabPatientImageViewerProps = {
  patientId: string;
  imagesApiBaseUrl?: string;
  height?: string;
};

export default function PathoCollabPatientImageViewer({
  patientId,
  imagesApiBaseUrl = "http://localhost:8004",
  height = "600px",
}: PathoCollabPatientImageViewerProps) {
  const [wsis, setWsis] = useState<WsiItem[]>([]);
  const [selectedWsiId, setSelectedWsiId] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const viewerId = useMemo(
    () => `pathocollab-osd-${patientId}`,
    [patientId]
  );

  useEffect(() => {
    if (!patientId) return;

    async function loadPatientImages() {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(
          `${imagesApiBaseUrl}/api/debug/wsi-dzi?patient_id=${encodeURIComponent(patientId)}`
        );

        if (!response.ok) {
          throw new Error(`Erreur ${response.status}`);
        }

        const data = await response.json();
        const list = data?.wsis || data?.slides || [];

        setWsis(list);

        if (list.length > 0) {
          setSelectedWsiId(list[0].wsi_id);
        }
      } catch (err) {
        console.error("Erreur chargement images PathoCollab:", err);
        setError("Impossible de charger les images du patient.");
        setWsis([]);
        setSelectedWsiId("");
      } finally {
        setLoading(false);
      }
    }

    loadPatientImages();
  }, [patientId, imagesApiBaseUrl]);

  useEffect(() => {
    if (!patientId || !selectedWsiId) return;

    const dziUrl = `${imagesApiBaseUrl}/api/wsi/patients/${encodeURIComponent(
      patientId
    )}/${encodeURIComponent(selectedWsiId)}/dzi`;

    const viewer = OpenSeadragon({
      id: viewerId,
      prefixUrl: "http://localhost:8004/api/wsi/openseadragon-images/",
      tileSources: dziUrl,
      showNavigator: true,
      showRotationControl: true,
      animationTime: 0.8,
      blendTime: 0.1,
      constrainDuringPan: true,
      maxZoomPixelRatio: 2,
      minZoomImageRatio: 0.8,
      visibilityRatio: 0.8,
    });

    return () => {
      viewer.destroy();
    };
  }, [patientId, selectedWsiId, imagesApiBaseUrl, viewerId]);

  if (!patientId) {
    return <div>Aucun patient sélectionné.</div>;
  }

  return (
    <div style={{ width: "100%" }}>
      <div style={{ marginBottom: "12px", display: "flex", gap: "12px", alignItems: "center" }}>
        <strong>Images du patient</strong>

        {loading && <span>Chargement...</span>}

        {!loading && wsis.length > 0 && (
          <select
            value={selectedWsiId}
            onChange={(e) => setSelectedWsiId(e.target.value)}
          >
            {wsis.map((wsi) => (
              <option key={wsi.wsi_id} value={wsi.wsi_id}>
                {wsi.filename || `WSI ${wsi.wsi_id}`}
              </option>
            ))}
          </select>
        )}
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: "12px" }}>
          {error}
        </div>
      )}

      {!loading && !error && wsis.length === 0 && (
        <div>Aucune image disponible pour ce patient.</div>
      )}

      {selectedWsiId && (
        <div
          id={viewerId}
          style={{
            width: "100%",
            height,
            border: "1px solid #ddd",
            borderRadius: "8px",
            background: "#f8fafc",
          }}
        />
      )}
    </div>
  );
}