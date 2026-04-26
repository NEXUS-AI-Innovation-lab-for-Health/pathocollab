import React, { useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import {
  Download,
  Move,
  Search,
  Contrast,
  Ruler,
  Square,
  Circle,
  RotateCcw,
} from "lucide-react";

const IMAGES_API =
  process.env.REACT_APP_IMAGES_URL ||
  `${window.location.protocol}//${window.location.hostname}:8004`;

type RadiologySeriesSummary = {
  id: string;
  app_patient_id: string;
  uploaded_by: string;
  orthanc_patient_id: string;
  orthanc_study_id: string;
  orthanc_series_id: string;
  preview_instance_id?: string | null;
  patient_name?: string | null;
  dicom_patient_id?: string | null;
  study_instance_uid?: string | null;
  series_instance_uid?: string | null;
  modality?: string | null;
  study_date?: string | null;
  study_description?: string | null;
  series_description?: string | null;
  instances_count: number;
};

type SeriesInstance = {
  instance_id: string;
  instance_number?: number | string | null;
  index_in_series?: number | null;
  sop_instance_uid?: string | null;
  preview_url: string;
  file_url: string;
  metadata_url?: string;
  image_id?: string;
};

type Props = {
  series: RadiologySeriesSummary | null;
};

const TOOL_GROUP_ID = "radiology-stack-tool-group";
const RENDERING_ENGINE_ID = "radiology-stack-engine";
const VIEWPORT_ID = "radiology-stack-viewport";

export default function CornerstoneViewer({ series }: Props) {
  const [instances, setInstances] = useState<SeriesInstance[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [cornerstoneReady, setCornerstoneReady] = useState(false);
  const [fallbackPreviewMode, setFallbackPreviewMode] = useState(false);
  const [activeTool, setActiveTool] = useState<
    "windowLevel" | "pan" | "zoom" | "length" | "rectangleRoi" | "ellipticalRoi"
  >("windowLevel");

  const viewportRef = useRef<HTMLDivElement | null>(null);
  const runtimeRef = useRef<any>(null);

  useEffect(() => {
    if (!series?.orthanc_series_id) {
      setInstances([]);
      setError(null);
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        setError(null);
        setInstances([]);

        const token = localStorage.getItem("access_token");
        const res = await axios.get(
          `${IMAGES_API}/api/radiology/series/${encodeURIComponent(series.orthanc_series_id)}/instances`,
          token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
        );

        if (cancelled) return;

        const list = (res.data?.instances || []).map((item: SeriesInstance) => ({
          ...item,
          image_id: item.image_id || `wadouri:${IMAGES_API}${item.file_url}`,
        }));

        setInstances(list);
      } catch (e) {
        if (cancelled) return;
        console.error("Error loading radiology instances", e);
        setError("Impossible de charger la série radiologique.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [series?.orthanc_series_id]);

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        const core = await import("@cornerstonejs/core");
        const dicomImageLoader = await import("@cornerstonejs/dicom-image-loader");
        const csTools = await import("@cornerstonejs/tools");

        const cornerstone = core as any;
        const loader = dicomImageLoader as any;
        const tools = csTools as any;

        loader.init();

        const {
          addTool,
          PanTool,
          ZoomTool,
          WindowLevelTool,
          LengthTool,
          RectangleROITool,
          EllipticalROITool,
          StackScrollMouseWheelTool,
          ToolGroupManager,
        } = tools;

        const { imageLoader } = cornerstone;

        if (loader?.wadouri?.loadImage) {
          imageLoader.registerImageLoader("wadouri", loader.wadouri.loadImage);
        }

        const safeAddTool = (toolClass: any) => {
          try {
            addTool(toolClass);
          } catch {}
        };

        safeAddTool(PanTool);
        safeAddTool(ZoomTool);
        safeAddTool(WindowLevelTool);
        safeAddTool(LengthTool);
        safeAddTool(RectangleROITool);
        safeAddTool(EllipticalROITool);
        safeAddTool(StackScrollMouseWheelTool);

        let toolGroup = ToolGroupManager.getToolGroup(TOOL_GROUP_ID);
        if (!toolGroup) {
          toolGroup = ToolGroupManager.createToolGroup(TOOL_GROUP_ID);
        }

        [
          PanTool.toolName,
          ZoomTool.toolName,
          WindowLevelTool.toolName,
          LengthTool.toolName,
          RectangleROITool.toolName,
          EllipticalROITool.toolName,
          StackScrollMouseWheelTool.toolName,
        ].forEach((toolName) => {
          try {
            toolGroup.addTool(toolName);
          } catch {}
        });

        runtimeRef.current = {
          cornerstone,
          csTools: tools,
          toolGroup,
          toolNames: {
            pan: PanTool.toolName,
            zoom: ZoomTool.toolName,
            windowLevel: WindowLevelTool.toolName,
            length: LengthTool.toolName,
            rectangleRoi: RectangleROITool.toolName,
            ellipticalRoi: EllipticalROITool.toolName,
            stackScrollMouseWheel: StackScrollMouseWheelTool.toolName,
          },
          renderingEngine: null,
        };

        if (mounted) {
          setCornerstoneReady(true);
          setFallbackPreviewMode(false);
        }
      } catch (e) {
        console.warn("Cornerstone indisponible, fallback preview activé.", e);
        if (mounted) {
          setCornerstoneReady(false);
          setFallbackPreviewMode(true);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!cornerstoneReady || !runtime || !viewportRef.current || !instances.length) return;

    let disposed = false;

    (async () => {
      try {
        const { cornerstone, toolGroup } = runtime;
        const { RenderingEngine, Enums } = cornerstone;

        let renderingEngine = cornerstone.getRenderingEngine?.(RENDERING_ENGINE_ID);
        if (!renderingEngine) {
          renderingEngine = new RenderingEngine(RENDERING_ENGINE_ID);
        }
        runtime.renderingEngine = renderingEngine;

        try {
          renderingEngine.enableElement({
            viewportId: VIEWPORT_ID,
            type: Enums.ViewportType.STACK,
            element: viewportRef.current,
          });
        } catch {}

        try {
          toolGroup.addViewport(VIEWPORT_ID, RENDERING_ENGINE_ID);
        } catch {}

        const viewport = renderingEngine.getViewport(VIEWPORT_ID);
        await viewport.setStack(
          instances.map((item) => item.image_id),
          0
        );

        activateTool(activeTool);
        viewport.render();

        if (disposed) return;
      } catch (e) {
        console.error("Cornerstone stack render error", e);
        if (!disposed) {
          setFallbackPreviewMode(true);
        }
      }
    })();

    return () => {
      disposed = true;
    };
  }, [cornerstoneReady, instances]);

  useEffect(() => {
    if (!cornerstoneReady) return;
    activateTool(activeTool);
  }, [activeTool, cornerstoneReady]);

  function activateTool(
    tool: "windowLevel" | "pan" | "zoom" | "length" | "rectangleRoi" | "ellipticalRoi"
  ) {
    const runtime = runtimeRef.current;
    if (!runtime?.toolGroup || !runtime?.csTools) return;

    const { toolGroup, csTools, toolNames } = runtime;
    const { Enums } = csTools;
    const mouseBindings = Enums.MouseBindings;

    [
      toolNames.pan,
      toolNames.zoom,
      toolNames.windowLevel,
      toolNames.length,
      toolNames.rectangleRoi,
      toolNames.ellipticalRoi,
    ].forEach((toolName: string) => {
      try {
        toolGroup.setToolPassive(toolName);
      } catch {}
    });

    try {
      toolGroup.setToolActive(toolNames.stackScrollMouseWheel);
    } catch {}

    const map: Record<string, string> = {
      pan: toolNames.pan,
      zoom: toolNames.zoom,
      windowLevel: toolNames.windowLevel,
      length: toolNames.length,
      rectangleRoi: toolNames.rectangleRoi,
      ellipticalRoi: toolNames.ellipticalRoi,
    };

    try {
      toolGroup.setToolActive(map[tool], {
        bindings: [{ mouseButton: mouseBindings.Primary }],
      });
    } catch (e) {
      console.error("Tool activation error", e);
    }
  }

  function handleReset() {
    const runtime = runtimeRef.current;
    if (!runtime?.renderingEngine) return;

    const viewport = runtime.renderingEngine.getViewport(VIEWPORT_ID);
    if (!viewport) return;

    try {
      viewport.resetCamera();
      viewport.resetProperties();
      viewport.render();
    } catch {}
  }

  const fallbackPreviewUrl = useMemo(() => {
    const first = instances[0];
    return first ? `${IMAGES_API}${first.preview_url}` : null;
  }, [instances]);

  if (!series) {
    return (
      <div className="h-full flex items-center justify-center text-slate-500">
        Sélectionnez une série radiologique.
      </div>
    );
  }

  const ToolButton = ({
    id,
    label,
    icon,
  }: {
    id: typeof activeTool;
    label: string;
    icon: React.ReactNode;
  }) => (
    <button
      onClick={() => setActiveTool(id)}
      className={`px-3 py-2 rounded-md border text-sm flex items-center gap-2 ${
        activeTool === id
          ? "bg-blue-600 text-white border-blue-600"
          : "bg-white text-slate-700 border-slate-200"
      }`}
      title={label}
    >
      {icon}
      <span>{label}</span>
    </button>
  );

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4 h-full">
      <div className="border border-slate-200 rounded-lg overflow-hidden bg-black">
        <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 bg-white border-b border-slate-200">
          <div className="text-sm">
            <div className="font-medium text-slate-900">
              {series.series_description || "Série radiologique"}
            </div>
            <div className="text-slate-500">
              {series.modality || "N/A"} · {series.instances_count} coupe(s)
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <ToolButton id="windowLevel" label="W/L" icon={<Contrast className="w-4 h-4" />} />
            <ToolButton id="pan" label="Pan" icon={<Move className="w-4 h-4" />} />
            <ToolButton id="zoom" label="Zoom" icon={<Search className="w-4 h-4" />} />
            <ToolButton id="length" label="Length" icon={<Ruler className="w-4 h-4" />} />
            <ToolButton id="rectangleRoi" label="Rect ROI" icon={<Square className="w-4 h-4" />} />
            <ToolButton id="ellipticalRoi" label="Ellipse ROI" icon={<Circle className="w-4 h-4" />} />

            <button
              onClick={handleReset}
              className="px-3 py-2 rounded-md border text-sm flex items-center gap-2 bg-white text-slate-700 border-slate-200"
              title="Réinitialiser la vue"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Reset</span>
            </button>

            {instances[0] && (
              <a
                href={`${IMAGES_API}${instances[0].file_url}`}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-2 rounded-md border text-sm flex items-center gap-2 bg-white text-slate-700 border-slate-200"
                title="Télécharger le DICOM"
              >
                <Download className="w-4 h-4" />
                <span>DICOM</span>
              </a>
            )}
          </div>
        </div>

        <div className="p-3 bg-slate-950">
          {loading ? (
            <div className="h-[70vh] min-h-[520px] flex items-center justify-center text-slate-300 text-sm">
              Chargement de la série…
            </div>
          ) : error ? (
            <div className="h-[70vh] min-h-[520px] flex items-center justify-center text-red-400 text-sm">
              {error}
            </div>
          ) : !instances.length ? (
            <div className="h-[70vh] min-h-[520px] flex items-center justify-center text-slate-400 text-sm">
              Aucune coupe disponible.
            </div>
          ) : fallbackPreviewMode || !cornerstoneReady ? (
            <div className="h-[70vh] min-h-[520px] flex items-center justify-center bg-black">
              {!fallbackPreviewUrl ? (
                <div className="text-slate-400 text-sm">Aucune prévisualisation disponible.</div>
              ) : (
                <img
                  src={fallbackPreviewUrl}
                  alt="fallback-preview"
                  className="max-h-full max-w-full object-contain"
                  draggable={false}
                />
              )}
            </div>
          ) : (
            <div ref={viewportRef} className="h-[70vh] min-h-[520px] w-full bg-black" />
          )}
        </div>
      </div>

      <aside className="border border-slate-200 rounded-lg bg-white overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-200 font-medium">Métadonnées</div>
        <div className="p-4 space-y-3 text-sm">
          <InfoRow label="Patient app" value={series.app_patient_id} />
          <InfoRow label="Patient DICOM" value={series.dicom_patient_id} />
          <InfoRow label="Nom DICOM" value={series.patient_name} />
          <InfoRow label="Modalité" value={series.modality} />
          <InfoRow label="Date étude" value={series.study_date} />
          <InfoRow label="Étude" value={series.study_description} />
          <InfoRow label="Série" value={series.series_description} />
          <InfoRow label="Coupes" value={String(series.instances_count)} />
          <InfoRow label="Mode" value={fallbackPreviewMode ? "Fallback preview" : "Cornerstone Stack"} />
          <InfoRow label="Outil actif" value={activeTool} />
        </div>
      </aside>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <div className="text-slate-500">{label}</div>
      <div className="text-slate-900 break-all">{value || "—"}</div>
    </div>
  );
}