import OpenSeadragon from "openseadragon";
import type React from "react";
import { useEffect, useMemo, useRef, useState } from "react";

import {
  loadAnnotations,
  saveAnnotations,
  imageRectToViewportRect,
  imageEllipseToViewportRect,
} from "./osdAnnotation";

import type {
  Annotation,
  AnnotationType,
  CircleAnnotation,
  RectAnnotation,
  PolygonAnnotation,
  PolygonPoint,
  BaseAnnotation,
} from "./types";

import {
  drawOnPressRect,
  drawOnDragRect,
  drawOnReleaseRect,
  type DragState as RectDragState,
} from "./drawRect";
import {
  drawOnPressCircle,
  drawOnDragCircle,
  drawOnReleaseCircle,
  type DragState as CircleDragState,
} from "./drawCircle";
import {
  polygonAddPoint,
  polygonMove,
  polygonFinish,
  polygonCancel,
} from "./drawPolygon";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL?.trim() ||
  process.env.REACT_APP_BACKEND_URL?.trim() ||
  `${window.location.protocol}//${window.location.hostname}:8000`;

type SourceType = "dzi" | "image";
type DrawTool = AnnotationType;
type Severity = NonNullable<BaseAnnotation["severity"]>;

export type OpenSeadragonUrlViewerProps = {
  sourceType: SourceType;
  sourceUrl: string;
  imageKey?: string | null;
  imageId?: string | null;
  caseId?: string | null;
};

type DragRefState = (RectDragState | CircleDragState) & {
  // drawPolygon ajoute dragRef.current.polygon de manière dynamique
  polygon?: any;
};

type ApiAnnotationRow = {
  id: string;
  image_id: string;
  case_id: string;
  type: AnnotationType;
  label?: string | null;
  severity?: Severity | null;
  created_at?: string | null;
  createdAt?: string | null;
  coordinates: Record<string, any>;
};

export default function OpenSeadragonUrlViewer(
  props: OpenSeadragonUrlViewerProps,
) {
  const { sourceType, sourceUrl, imageKey, imageId, caseId } = props;

  type AnnSource = BaseAnnotation["_source"]; // "local" | "api" | "ia"

  function normalizeSource(s: any): AnnSource {
    return s === "local" || s === "api" || s === "ia" ? s : "local";
  }

  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);

  const [pendingAnn, setPendingAnn] = useState<Annotation | null>(null);
  const [labelDraft, setLabelDraft] = useState<string>("");
  const [severityDraft, setSeverityDraft] = useState<Severity>("Moyenne");
  const [draftAnnotations, setDraftAnnotations] = useState<Annotation[]>([]);
  const [labelOpen, setLabelOpen] = useState<boolean>(false);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [annotateMode, setAnnotateMode] = useState<boolean>(false);
  const [drawTool, setDrawTool] = useState<DrawTool>("rect");

  const dragRef = useRef<DragRefState>({
    active: false,
    startImage: null,
    overlayEl: null,
  });

  const canAnnotate = useMemo(() => Boolean(imageKey), [imageKey]);

  async function fetchAnnotationsForImage(
    imgId: string,
  ): Promise<ApiAnnotationRow[]> {
    const res = await fetch(`${API_BASE_URL}/api/annotations/image/${imgId}`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(
        "GET /api/annotations/image/imageID  error:",
        res.status,
        text,
      );
      throw new Error(`GET annotation failed: ${res.status} - ${text}`);
    }
    return (await res.json()) as ApiAnnotationRow[];
  }

  // Load annotations when imageKey changes
  useEffect(() => {
    let cancelled = false;

    async function run() {
      if (!imageKey || !imageId) {
        setAnnotations([]);
        return;
      }

      try {
        const apiAnnotations = await fetchAnnotationsForImage(imageId);
        if (cancelled) return;

        const mapped: Annotation[] = apiAnnotations.map((a) => {
          const base: BaseAnnotation = {
            id: a.id,
            type: a.type,
            label: a.label ?? null,
            severity: (a.severity ?? "Moyenne") as Severity,
            createdAt: (a.created_at ??
              a.createdAt ??
              new Date().toISOString()) as string,
            _source: "api",
          };

          // coordinates ne contient que la géométrie
          if (a.type === "rect") {
            const c = a.coordinates as RectAnnotation;
            return { ...base, type: "rect", x: c.x, y: c.y, w: c.w, h: c.h };
          }
          if (a.type === "circle") {
            const c = a.coordinates as CircleAnnotation;
            return {
              ...base,
              type: "circle",
              cx: c.cx,
              cy: c.cy,
              rx: c.rx,
              ry: c.ry,
            };
          }
          // polygon
          const c = a.coordinates as { points: PolygonPoint[] };
          return {
            ...base,
            type: "polygon",
            points: Array.isArray(c.points) ? c.points : [],
          };
        });

        setAnnotations(mapped);
        saveAnnotations(imageKey, mapped);
      } catch {
        const raw = loadAnnotations(imageKey) as any[];
        const local = (Array.isArray(raw) ? raw : []).map((a) => ({
          ...a,
          _source: normalizeSource(a?._source),
        })) as Annotation[];

        if (!cancelled) setAnnotations(local);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [imageKey, imageId]);

  // Init viewer
  useEffect(() => {
    if (!containerRef.current || !sourceUrl) return;

    if (viewerRef.current) {
      viewerRef.current.destroy();
      viewerRef.current = null;
    }

    const tileSources =
      sourceType === "dzi" ? sourceUrl : [{ type: "image", url: sourceUrl }];

    const viewer = OpenSeadragon({
      element: containerRef.current,
      prefixUrl: "http://127.0.0.1:8000/api/wsi/openseadragon-images/",
      showNavigator: true,
      tileSources,
    });

    viewerRef.current = viewer;

    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, [sourceType, sourceUrl]);

  // Redraw overlays when annotations change
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    if (!viewer.world || viewer.world.getItemCount() === 0) return;
    redrawAll(viewer, [...annotations, ...draftAnnotations]);
  }, [annotations, draftAnnotations]);

  // Disable default OSD gestures while annotating
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    const gs = viewer.gestureSettingsMouse;
    viewer.gestureSettingsMouse = {
      ...gs,
      dragToPan: !annotateMode,
      scrollToZoom: !annotateMode,
      clickToZoom: !annotateMode,
      dblClickToZoom: !annotateMode,
      pinchToZoom: !annotateMode,
    };
  }, [annotateMode]);

  // Handlers annotation
  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !canAnnotate) return;

    let attached = false;

    const attach = () => {
      if (attached) return;
      attached = true;

      const onPress = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode) return;

        evt.preventDefaultAction = true;

        if (drawTool === "rect") {
          const [el, imagePoint] = drawOnPressRect(evt, viewer, dragRef as any);
          el.dataset.kind = "temp";
          viewer.addOverlay({
            element: el,
            location: imageRectToViewportRect(viewer, {
              x: imagePoint.x,
              y: imagePoint.y,
              w: 1,
              h: 1,
            }),
          });
        } else if (drawTool === "circle") {
          const [el, imagePoint] = drawOnPressCircle(
            evt,
            viewer,
            dragRef as any,
          );
          el.dataset.kind = "temp";
          viewer.addOverlay({
            element: el,
            location: imageRectToViewportRect(viewer, {
              x: imagePoint.x,
              y: imagePoint.y,
              w: 1,
              h: 1,
            }),
          });
        } else if (drawTool === "polygon") {
          polygonAddPoint(evt, viewer, dragRef as any);
        }
      };

      const onDrag = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode) return;
        if (!dragRef.current.active) return;

        evt.preventDefaultAction = true;

        if (drawTool === "rect") {
          const [el, x, y, w, h] = drawOnDragRect(evt, viewer, dragRef as any);
          if (el)
            viewer.updateOverlay(
              el,
              imageRectToViewportRect(viewer, { x, y, w, h }),
            );
        } else if (drawTool === "circle") {
          const [el, x, y, w, h] = drawOnDragCircle(
            evt,
            viewer,
            dragRef as any,
          );
          if (el) {
            const cx = x + w / 2;
            const cy = y + h / 2;
            const rx = w / 2;
            const ry = h / 2;
            viewer.updateOverlay(
              el,
              imageRectToViewportRect(viewer, {
                x: cx - rx,
                y: cy - ry,
                w: rx * 2,
                h: ry * 2,
              }),
            );
          }
        }
      };

      const onMove = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode) return;
        if (drawTool !== "polygon") return;
        polygonMove(evt, viewer, dragRef as any);
      };

      const onDblClick = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode) return;
        if (drawTool !== "polygon") return;
        evt.preventDefaultAction = true;
        finalizePolygon();
      };

      const onRelease = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode) return;
        if (!dragRef.current.active) return;

        evt.preventDefaultAction = true;

        let annotation: Annotation | null = null;
        if (drawTool === "rect") {
          annotation = drawOnReleaseRect(
            evt,
            viewer,
            "rect",
            null,
            dragRef as any,
          );
        } else if (drawTool === "circle") {
          annotation = drawOnReleaseCircle(
            evt,
            viewer,
            "circle",
            null,
            dragRef as any,
          );
        } else {
          return;
        }

        if (!annotation) return;

        setPendingAnn(annotation);
        setDraftAnnotations([annotation]);
        setLabelDraft("");
        setSeverityDraft("Moyenne");
        setLabelOpen(true);
      };

      viewer.addHandler("canvas-press", onPress);
      viewer.addHandler("canvas-drag", onDrag);
      viewer.addHandler("canvas-release", onRelease);
      viewer.addHandler("canvas-move", onMove);
      viewer.addHandler("canvas-double-click", onDblClick);

      (attach as any)._cleanup = () => {
        viewer.removeHandler("canvas-press", onPress);
        viewer.removeHandler("canvas-drag", onDrag);
        viewer.removeHandler("canvas-release", onRelease);
        viewer.removeHandler("canvas-move", onMove);
        viewer.removeHandler("canvas-double-click", onDblClick);
      };
    };

    if (viewer.world && viewer.world.getItemCount() > 0) {
      attach();
    } else {
      viewer.addOnceHandler("open", attach);
    }

    return () => {
      try {
        viewer.removeHandler("open", attach);
        const cleanup = (attach as any)._cleanup as undefined | (() => void);
        if (cleanup) cleanup();
      } catch {
        // ignore
      }
    };
  }, [annotateMode, canAnnotate, drawTool]);

  const finalizePolygon = () => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    const [ann] = polygonFinish(viewer, dragRef as any, null);
    if (!ann) return;

    setPendingAnn(ann);
    setDraftAnnotations([ann]);
    setLabelDraft("");
    setSeverityDraft("Moyenne");
    setLabelOpen(true);
  };

  const cancelPolygonUi = () => {
    const viewer = viewerRef.current;
    if (!viewer) return;
    polygonCancel(viewer, dragRef as any);
  };

  const onToggleAnnotate = () => {
    if (!canAnnotate) return;
    setAnnotateMode((v) => !v);
  };

  const onClear = () => {
    if (!imageKey) return;
    setAnnotations([]);
    saveAnnotations(imageKey, []);
  };

  function getToken() {
    return (
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      localStorage.getItem("accessToken") ||
      ""
    );
  }

  function authHeaders(): HeadersInit {
    const token = getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async function postAnnotationToApi(args: {
    imageId: string;
    caseId: string;
    ann: Annotation;
  }): Promise<any> {
    const { imageId: imgId, caseId: cId, ann } = args;

    const payload = {
      image_id: imgId,
      case_id: cId,
      type: "manual",
      label: ann.label ?? null,
      severity: ann.severity ?? "Moyenne",
      coordinates: buildCoordinatesPayload(ann),
    };

    console.log("access_token:", localStorage.getItem("access_token"));
    console.log("authHeaders():", authHeaders());

    const res = await fetch(`${API_BASE_URL}/api/annotations/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error("POST /api/annotations  error:", res.status, text);
      throw new Error(`POST annotation failed: ${res.status} - ${text}`);
    }
    return await res.json();
  }

  function buildCoordinatesPayload(ann: Annotation): Record<string, any> {
    if (ann.type === "rect") return { x: ann.x, y: ann.y, w: ann.w, h: ann.h };
    if (ann.type === "circle")
      return { cx: ann.cx, cy: ann.cy, rx: ann.rx, ry: ann.ry };
    if (ann.type === "polygon") return { points: ann.points };
    return {};
  }

  const commitPendingAnnotation = async () => {
    if (!pendingAnn || !imageKey) return;

    const nextAnn: Annotation = {
      ...pendingAnn,
      _source: normalizeSource((pendingAnn as any)?._source),
      label: labelDraft.trim() || null,
      severity: severityDraft,
    };

    // Optimistic UI
    setAnnotations((prev) => {
      const next = [...prev, nextAnn];
      saveAnnotations(imageKey, next);
      return next;
    });

    setPendingAnn(null);
    setDraftAnnotations([]);
    setLabelOpen(false);

    try {
      console.log("Saving annotation to API...", nextAnn);
      console.log("imageId:", imageId, " | caseId:", caseId);
      if (!imageId || !caseId) return;

      const saved = await postAnnotationToApi({
        imageId,
        caseId,
        ann: nextAnn,
      });

      setAnnotations((prev) => {
        const replaced = prev.map((a) =>
          a.id === nextAnn.id
            ? {
                ...a,
                id: saved.id as string,
                _source: "api" as const,
              }
            : a,
        );
        saveAnnotations(imageKey, replaced);
        return replaced;
      });
    } catch (e) {
      // stratégie: garder local et synchroniser plus tard
      console.error(e);
    }
  };

  const cancelPendingAnnotation = () => {
    setPendingAnn(null);
    setDraftAnnotations([]);
    setLabelOpen(false);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 10,
        height: "100%",
      }}
    >
      <div style={styles.toolbar}>
        <div style={styles.group}>
          <ToolButton
            title={
              annotateMode ? "Mode annotation (ON)" : "Mode annotation (OFF)"
            }
            active={annotateMode}
            disabled={!canAnnotate}
            onClick={onToggleAnnotate}
            icon={IconPencil}
          />
        </div>

        <div style={styles.divider} />

        <div style={styles.group}>
          <ToolButton
            title="Rectangle"
            active={drawTool === "rect"}
            disabled={!canAnnotate}
            onClick={() => setDrawTool("rect")}
            icon={IconRect}
          />
          <ToolButton
            title="Cercle"
            active={drawTool === "circle"}
            disabled={!canAnnotate}
            onClick={() => setDrawTool("circle")}
            icon={IconCircle}
          />
          <ToolButton
            title="Polygone"
            active={drawTool === "polygon"}
            disabled={!canAnnotate}
            onClick={() => setDrawTool("polygon")}
            icon={IconPolygon}
          />
        </div>

        {drawTool === "polygon" && annotateMode && (
          <>
            <div style={styles.divider} />
            <div style={styles.group}>
              <ToolButton
                title="Terminer polygone (double-clic possible)"
                active={false}
                disabled={!canAnnotate}
                onClick={finalizePolygon}
                icon={IconCheck}
              />
              <ToolButton
                title="Annuler polygone"
                active={false}
                disabled={!canAnnotate}
                onClick={cancelPolygonUi}
                icon={IconX}
              />
            </div>
          </>
        )}

        <div style={{ flex: 1 }} />

        <div style={styles.group}>
          <div style={styles.counter}>{annotations.length} annotation(s)</div>
          <ToolButton
            title="Effacer toutes les annotations"
            active={false}
            disabled={!canAnnotate || annotations.length === 0}
            onClick={onClear}
            icon={IconTrash}
          />
        </div>
      </div>

      {labelOpen && (
        <div style={modalStyles.backdrop}>
          <div style={modalStyles.modal}>
            <h3 style={{ margin: "0 0 10px" }}>Décrire l’annotation</h3>

            <label style={modalStyles.label}>
              Label (optionnel)
              <input
                value={labelDraft}
                onChange={(e) => setLabelDraft(e.target.value)}
                style={modalStyles.input}
                placeholder="Ex: zone suspecte…"
              />
            </label>

            <label style={modalStyles.label}>
              Sévérité
              <select
                value={severityDraft}
                onChange={(e) => setSeverityDraft(e.target.value as Severity)}
                style={modalStyles.input}
              >
                <option value="Faible">Faible</option>
                <option value="Moyenne">Moyenne</option>
                <option value="Élevée">Élevée</option>
              </select>
            </label>

            <div
              style={{
                display: "flex",
                justifyContent: "flex-end",
                gap: 8,
                marginTop: 10,
              }}
            >
              <button
                onClick={cancelPendingAnnotation}
                style={modalStyles.secondaryBtn}
              >
                Annuler
              </button>
              <button
                onClick={commitPendingAnnotation}
                style={modalStyles.primaryBtn}
              >
                Enregistrer
              </button>
            </div>
          </div>
        </div>
      )}

      <div
        ref={containerRef}
        style={{
          flex: 1,
          minHeight: 320,
          border: "1px solid #e6e6e6",
          borderRadius: 10,
          overflow: "hidden",
          background: "#fafafa",
          position: "relative",
        }}
      />
    </div>
  );
}

function redrawAll(
  viewer: OpenSeadragon.Viewer,
  annotations: Annotation[],
): void {
  const overlays = (viewer as any).currentOverlays as
    | Array<{ element?: HTMLElement }>
    | undefined;
  (overlays ?? []).forEach((o) => {
    const el = o?.element;
    if (el && (el as any).dataset?.kind === "persisted") {
      viewer.removeOverlay(el);
    }
  });

  annotations.forEach((ann) => {
    if (ann.type === "rect") {
      const el = document.createElement("div");
      el.style.boxSizing = "border-box";
      el.style.pointerEvents = "none";
      el.style.border = "2px solid #ff3b30";
      el.style.background = "rgba(255,59,48,0.08)";
      el.dataset.kind = "persisted";
      viewer.addOverlay({
        element: el,
        location: imageRectToViewportRect(viewer, ann),
      });
      if (ann.label) addLabel(viewer, ann, ann.label, "rect");
      return;
    }

    if (ann.type === "circle") {
      const el = document.createElement("div");
      el.style.boxSizing = "border-box";
      el.style.pointerEvents = "none";
      el.style.border = "2px solid #ff3b30";
      el.style.background = "rgba(255,59,48,0.08)";
      el.style.borderRadius = "9999px";
      el.dataset.kind = "persisted";
      viewer.addOverlay({
        element: el,
        location: imageEllipseToViewportRect(viewer, ann),
      });
      if (ann.label) addLabel(viewer, ann, ann.label, "circle");
      return;
    }

    if (
      ann.type === "polygon" &&
      Array.isArray(ann.points) &&
      ann.points.length >= 3
    ) {
      const vpts = ann.points.map((p) =>
        viewer.viewport.imageToViewportCoordinates(p.x, p.y),
      );

      let vminX = Infinity,
        vminY = Infinity,
        vmaxX = -Infinity,
        vmaxY = -Infinity;
      for (const p of vpts) {
        vminX = Math.min(vminX, p.x);
        vminY = Math.min(vminY, p.y);
        vmaxX = Math.max(vmaxX, p.x);
        vmaxY = Math.max(vmaxY, p.y);
      }

      const pad = 0.0005;
      const vbX = vminX - pad;
      const vbY = vminY - pad;
      const vbW = vmaxX - vminX + pad * 2;
      const vbH = vmaxY - vminY + pad * 2;

      const svgNS = "http://www.w3.org/2000/svg";
      const svg = document.createElementNS(svgNS, "svg");
      svg.style.pointerEvents = "none";
      svg.setAttribute("width", "100%");
      svg.setAttribute("height", "100%");
      svg.setAttribute("viewBox", `${vbX} ${vbY} ${vbW} ${vbH}`);
      svg.style.overflow = "visible";

      const poly = document.createElementNS(svgNS, "polygon");
      poly.setAttribute("fill", "rgba(255,0,0,0.30)");
      poly.setAttribute("stroke", "#ff0000");
      poly.setAttribute("stroke-width", "0.0012");
      poly.setAttribute("stroke-linejoin", "round");
      poly.setAttribute("points", vpts.map((p) => `${p.x},${p.y}`).join(" "));

      svg.appendChild(poly);

      let minX = Infinity,
        minY = Infinity,
        maxX = -Infinity,
        maxY = -Infinity;
      for (const p of ann.points) {
        minX = Math.min(minX, p.x);
        minY = Math.min(minY, p.y);
        maxX = Math.max(maxX, p.x);
        maxY = Math.max(maxY, p.y);
      }
      const rect = imageRectToViewportRect(viewer, {
        x: minX,
        y: minY,
        w: maxX - minX,
        h: maxY - minY,
      } as any);

      (svg as any).dataset.kind = "persisted";
      viewer.addOverlay({ element: svg, location: rect });

      if (ann.label)
        addLabel(
          viewer,
          { x: minX, y: minY, w: maxX - minX, h: maxY - minY },
          ann.label,
          "polygon",
        );
    }
  });
}

function addLabel(
  viewer: OpenSeadragon.Viewer,
  shape:
    | RectAnnotation
    | CircleAnnotation
    | { x: number; y: number; w: number; h: number }
    | PolygonAnnotation,
  text: string,
  kind: "rect" | "circle" | "polygon",
): void {
  const el = document.createElement("div");
  el.textContent = text;
  el.style.fontSize = "12px";
  el.style.padding = "2px 6px";
  el.style.borderRadius = "6px";
  el.style.background = "rgba(255,255,255,0.9)";
  el.style.border = "1px solid #ddd";
  el.style.pointerEvents = "none";
  el.style.whiteSpace = "nowrap";

  const x =
    kind === "circle"
      ? (shape as CircleAnnotation).cx - (shape as CircleAnnotation).rx
      : (shape as any).x;
  const y =
    kind === "circle"
      ? (shape as CircleAnnotation).cy - (shape as CircleAnnotation).ry
      : (shape as any).y;

  el.dataset.kind = "persisted";

  viewer.addOverlay({
    element: el,
    location: viewer.viewport.imageToViewportCoordinates(x, y),
  });
}

function ToolButton(props: {
  title: string;
  icon: React.ComponentType;
  active: boolean;
  disabled: boolean;
  onClick: () => void;
}) {
  const { title, icon: Icon, active, disabled, onClick } = props;
  return (
    <button
      type="button"
      title={title}
      onClick={onClick}
      disabled={disabled}
      style={{
        ...styles.toolBtn,
        ...(active ? styles.toolBtnActive : null),
        ...(disabled ? styles.toolBtnDisabled : null),
      }}
    >
      <Icon />
    </button>
  );
}

const styles: Record<string, React.CSSProperties> = {
  toolbar: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "8px 10px",
    border: "1px solid #e6e6e6",
    borderRadius: 10,
    background: "#fff",
  },
  group: { display: "flex", alignItems: "center", gap: 6 },
  divider: {
    width: 1,
    alignSelf: "stretch",
    background: "#eee",
    margin: "0 4px",
  },
  toolBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    border: "1px solid #ddd",
    background: "#fff",
    cursor: "pointer",
    display: "grid",
    placeItems: "center",
  },
  toolBtnActive: {
    borderColor: "#ff3b30",
    background: "rgba(255,59,48,0.10)",
  },
  toolBtnDisabled: {
    opacity: 0.45,
    cursor: "not-allowed",
  },
  counter: {
    fontSize: 12,
    color: "#666",
    padding: "0 8px",
  },
};

const modalStyles: Record<string, React.CSSProperties> = {
  backdrop: {
    position: "absolute",
    inset: 0,
    background: "rgba(0,0,0,0.25)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 100,
  },
  modal: {
    width: "min(520px, 92vw)",
    background: "#fff",
    borderRadius: 12,
    border: "1px solid #e6e6e6",
    boxShadow: "0 12px 30px rgba(0,0,0,0.18)",
    padding: 14,
  },
  label: {
    fontSize: 12,
    color: "#444",
    display: "grid",
    gap: 6,
    marginBottom: 10,
  },
  input: {
    width: "100%",
    padding: 10,
    borderRadius: 10,
    border: "1px solid #ddd",
  },
  primaryBtn: {
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #111",
    background: "#111",
    color: "#fff",
  },
  secondaryBtn: {
    padding: "10px 12px",
    borderRadius: 10,
    border: "1px solid #ddd",
    background: "#fff",
  },
};

function IconRect() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <rect
        x="3"
        y="4"
        width="12"
        height="10"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}
function IconCircle() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <circle
        cx="9"
        cy="9"
        r="5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}
function IconPolygon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M4 12 L7 4 L14 7 L12 14 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
    </svg>
  );
}
function IconPencil() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M4 12.5V14h1.5l7.6-7.6-1.5-1.5L4 12.5Z" fill="currentColor" />
      <path d="M10.6 3.9l1.5 1.5" stroke="currentColor" strokeWidth="1.6" />
    </svg>
  );
}
function IconCheck() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M4 9.5l3 3L14 5.5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
function IconX() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M5 5l8 8M13 5l-8 8"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
      />
    </svg>
  );
}
function IconTrash() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path
        d="M6 6h8l-1 10H7L6 6Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
      />
      <path
        d="M5 6h10M7 6V4h4v2"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}
