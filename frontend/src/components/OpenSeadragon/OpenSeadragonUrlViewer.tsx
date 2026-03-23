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
  AnnotationCategory,
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

const IMAGES_API =
  process.env.REACT_APP_IMAGES_API?.trim() ||
  `${window.location.protocol}//${window.location.hostname}:8004`;

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
  polygon?: any;
};

type ApiAnnotationRow = {
  id: string;
  image_id: string;
  case_id: string;
  type: AnnotationType;
  label?: string | null;
  severity?: Severity | null;
  category?: AnnotationCategory | null;
  description?: string | null;
  recommendation?: string | null;
  tags?: string[] | null;
  owner_id?: string | null;
  owner_name?: string | null;
  created_at?: string | null;
  createdAt?: string | null;
  updated_at?: string | null;
  updatedAt?: string | null;
  coordinates: Record<string, any>;
};

function inferShapeTypeFromCoordinates(
  coords: Record<string, any> | null | undefined,
): AnnotationType {
  if (!coords || typeof coords !== "object") return "rect";

  if (Array.isArray(coords.points)) return "polygon";
  if (
    typeof coords.cx === "number" &&
    typeof coords.cy === "number" &&
    typeof coords.rx === "number" &&
    typeof coords.ry === "number"
  ) {
    return "circle";
  }
  if (
    typeof coords.x === "number" &&
    typeof coords.y === "number" &&
    typeof coords.w === "number" &&
    typeof coords.h === "number"
  ) {
    return "rect";
  }

  if (coords.shape_type === "polygon") return "polygon";
  if (coords.shape_type === "circle") return "circle";
  return "rect";
}

export default function OpenSeadragonUrlViewer(
  props: OpenSeadragonUrlViewerProps,
) {
  const { sourceType, sourceUrl, imageKey, imageId, caseId } = props;

  type AnnSource = BaseAnnotation["_source"];

  function normalizeSource(s: any): AnnSource {
    return s === "local" || s === "api" || s === "ia" ? s : "local";
  }

  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewerRef = useRef<OpenSeadragon.Viewer | null>(null);

  const [pendingAnn, setPendingAnn] = useState<Annotation | null>(null);
  const [draftAnnotations, setDraftAnnotations] = useState<Annotation[]>([]);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [annotateMode, setAnnotateMode] = useState<boolean>(false);
  const [drawTool, setDrawTool] = useState<DrawTool>("rect");
  
  const [drawSettingsOpen, setDrawSettingsOpen] = useState(false);
  const [drawStrokeColor, setDrawStrokeColor] = useState("#ff3b30");
  const [drawFillColor, setDrawFillColor] = useState("rgba(255,59,48,0.08)");
  const [drawStrokeWidth, setDrawStrokeWidth] = useState(2);

  const [selectedAnnotation, setSelectedAnnotation] = useState<Annotation | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [formMode, setFormMode] = useState<"create" | "view" | "edit">(
    "create",
  );

  const [formLabel, setFormLabel] = useState("");
  const [formSeverity, setFormSeverity] = useState<Severity>("Moyenne");
  const [formCategory, setFormCategory] = useState<AnnotationCategory | "">("");
  const [formDescription, setFormDescription] = useState("");
  const [formRecommendation, setFormRecommendation] = useState("");
  const [formTags, setFormTags] = useState("");

  const dragRef = useRef<DragRefState>({
    active: false,
    startImage: null,
    overlayEl: null,
  });

  const canAnnotate = useMemo(() => Boolean(imageKey), [imageKey]);

  function getCurrentUser() {
    const token =
      localStorage.getItem("access_token") ||
      localStorage.getItem("token") ||
      localStorage.getItem("accessToken");

    if (!token) {
      return { id: null, name: null };
    }

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      const email = payload.sub || payload.email || null;
      const name = payload.full_name || payload.name || email || null;
      return { id: email, name };
    } catch {
      return { id: null, name: null };
    }
  }

  function canEditAnnotation(ann: Annotation | null) {
    if (!ann) return false;
    const current = getCurrentUser();
    return !!current.id && ann.ownerId === current.id;
  }

  function resetFormFields() {
    setFormLabel("");
    setFormSeverity("Moyenne");
    setFormCategory("");
    setFormDescription("");
    setFormRecommendation("");
    setFormTags("");
  }

  function fillFormFromAnnotation(ann: Annotation) {
    setFormLabel(ann.label || "");
    setFormSeverity(ann.severity || "Moyenne");
    setFormCategory((ann.category as AnnotationCategory) || "");
    setFormDescription(ann.description || "");
    setFormRecommendation(ann.recommendation || "");
    setFormTags((ann.tags || []).join(", "));
  }

  function openAnnotationDetails(ann: Annotation) {
    setSelectedAnnotation(ann);
    setFormMode("view");
    fillFormFromAnnotation(ann);
    setDetailOpen(true);
  }

  function closeDetailModal() {
    setDetailOpen(false);
    setSelectedAnnotation(null);
    setPendingAnn(null);
    setDraftAnnotations([]);
    setFormMode("create");
    resetFormFields();
  }

  async function fetchAnnotationsForImage(
    imgId: string,
  ): Promise<ApiAnnotationRow[]> {
    const res = await fetch(`${IMAGES_API}/api/annotations/image/${imgId}`, {
      headers: {
        ...authHeaders(),
      },
    });
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error(
        "GET /api/annotations/image/imageID error:",
        res.status,
        text,
      );
      throw new Error(`GET annotation failed: ${res.status} - ${text}`);
    }
    return (await res.json()) as ApiAnnotationRow[];
  }

  function inferShapeTypeFromCoordinates(
    coords: Record<string, any> | null | undefined,
  ): AnnotationType {
    if (!coords || typeof coords !== "object") return "rect";

    if (coords.shape_type === "polygon" || Array.isArray(coords.points)) {
      return "polygon";
    }

    if (
      coords.shape_type === "circle" ||
      (
        typeof coords.cx === "number" &&
        typeof coords.cy === "number" &&
        typeof coords.rx === "number" &&
        typeof coords.ry === "number"
      )
    ) {
      return "circle";
    }

    return "rect";
  }

  function mapApiAnnotationToFrontend(a: ApiAnnotationRow): Annotation | null {
    const coords =
      a.coordinates && typeof a.coordinates === "object" ? a.coordinates : {};

    const shapeType = inferShapeTypeFromCoordinates(coords);

    const base: BaseAnnotation = {
      id: a.id,
      type: shapeType,
      label: a.label ?? null,
      category: a.category ?? null,
      severity: (a.severity ?? "Moyenne") as Severity,
      description: a.description ?? null,
      recommendation: a.recommendation ?? null,
      tags: Array.isArray(a.tags) ? a.tags : [],
      ownerId: a.owner_id ?? null,
      ownerName: a.owner_name ?? null,
      strokeColor: (a as any).stroke_color ?? "#ff3b30",
      fillColor: (a as any).fill_color ?? "rgba(255,59,48,0.08)",
      strokeWidth:
        typeof (a as any).stroke_width === "number"
          ? (a as any).stroke_width
          : Number((a as any).stroke_width ?? 2),
      createdAt: (a.created_at ?? a.createdAt ?? new Date().toISOString()) as string,
      updatedAt: (a.updated_at ?? a.updatedAt ?? null) as string | null,
      _source: "api",
      confidence: null,
      notes: null,
    };

    if (shapeType === "rect") {
      if (
        typeof coords.x !== "number" ||
        typeof coords.y !== "number" ||
        typeof coords.w !== "number" ||
        typeof coords.h !== "number"
      ) return null;

      return { ...base, type: "rect", x: coords.x, y: coords.y, w: coords.w, h: coords.h };
    }

    if (shapeType === "circle") {
      if (
        typeof coords.cx !== "number" ||
        typeof coords.cy !== "number" ||
        typeof coords.rx !== "number" ||
        typeof coords.ry !== "number"
      ) return null;

      return {
        ...base,
        type: "circle",
        cx: coords.cx,
        cy: coords.cy,
        rx: coords.rx,
        ry: coords.ry,
      };
    }

    if (!Array.isArray(coords.points)) return null;

    return { ...base, type: "polygon", points: coords.points };
  }

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

        const mapped: Annotation[] = apiAnnotations.map(mapApiAnnotationToFrontend).filter(Boolean) as Annotation[];

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
      prefixUrl: "/assets/openseadragon-images/",
      showNavigator: true,
      tileSources,
    });

    viewerRef.current = viewer;

    return () => {
      viewer.destroy();
      viewerRef.current = null;
    };
  }, [sourceType, sourceUrl]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    const draw = () => {
      redrawAll(viewer, [...annotations, ...draftAnnotations]);
    };

    if (viewer.world && viewer.world.getItemCount() > 0) {
      draw();
    } else {
      viewer.addOnceHandler("open", draw);
    }

    return () => {
      try {
        viewer.removeHandler("open", draw);
      } catch {
        // ignore
      }
    };
  }, [annotations, draftAnnotations, sourceUrl]);

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

  useEffect(() => {
    if (annotateMode) return;

    const viewer = viewerRef.current;
    if (!viewer) return;

    if (dragRef.current.overlayEl) {
      try {
        viewer.removeOverlay(dragRef.current.overlayEl);
      } catch {
        // ignore
      }
    }

    dragRef.current.active = false;
    dragRef.current.startImage = null;
    dragRef.current.overlayEl = null;

    try {
      polygonCancel(viewer, dragRef as any);
    } catch {
      // ignore
    }

    setPendingAnn(null);
    setDraftAnnotations([]);
  }, [annotateMode]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || !canAnnotate) return;

    let attached = false;

    const attach = () => {
      if (attached) return;
      attached = true;

      const onPress = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode || detailOpen) return;

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
        if (!annotateMode || detailOpen) return;
        if (!dragRef.current.active) return;

        evt.preventDefaultAction = true;

        if (drawTool === "rect") {
          const [el, x, y, w, h] = drawOnDragRect(evt, viewer, dragRef as any);
          if (el) {
            viewer.updateOverlay(
              el,
              imageRectToViewportRect(viewer, { x, y, w, h }),
            );
          }
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
        if (!annotateMode || detailOpen) return;
        if (drawTool !== "polygon") return;
        polygonMove(evt, viewer, dragRef as any);
      };

      const onDblClick = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode || detailOpen) return;
        if (drawTool !== "polygon") return;
        evt.preventDefaultAction = true;
        finalizePolygon();
      };

      const onRelease = (evt: OpenSeadragon.OSDEvent<any>) => {
        if (!annotateMode || detailOpen) return;
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
        setSelectedAnnotation(annotation);
        setDraftAnnotations([annotation]);
        setFormMode("create");
        resetFormFields();
        setDetailOpen(true);
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
  }, [annotateMode, canAnnotate, drawTool, detailOpen]);

  const finalizePolygon = () => {
    const viewer = viewerRef.current;
    if (!viewer) return;

    const [ann] = polygonFinish(viewer, dragRef as any, null);
    if (!ann) return;

    setPendingAnn(ann);
    setSelectedAnnotation(ann);
    setDraftAnnotations([ann]);
    setFormMode("create");
    resetFormFields();
    setDetailOpen(true);
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
    setSelectedAnnotation(null);
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
      label: ann.label ?? "",
      severity: ann.severity ?? "Moyenne",
      category: ann.category ?? null,
      description: ann.description ?? null,
      recommendation: ann.recommendation ?? null,
      tags: ann.tags ?? [],
      stroke_color: ann.strokeColor ?? "#ff3b30",
      fill_color: ann.fillColor ?? "rgba(255,59,48,0.08)",
      stroke_width: ann.strokeWidth ?? 2,
      confidence: ann.confidence ?? null,
      notes: ann.notes ?? null,
      coordinates: buildCoordinatesPayload(ann),
    };

    const res = await fetch(`${IMAGES_API}/api/annotations/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text().catch(() => "");
      console.error("POST /api/annotations error:", res.status, text);
      throw new Error(`POST annotation failed: ${res.status} - ${text}`);
    }

    return await res.json();
  }

  function buildCoordinatesPayload(ann: Annotation): Record<string, any> {
    if (ann.type === "rect") {
      return {
        shape_type: "rect",
        x: ann.x,
        y: ann.y,
        w: ann.w,
        h: ann.h,
      };
    }

    if (ann.type === "circle") {
      return {
        shape_type: "circle",
        cx: ann.cx,
        cy: ann.cy,
        rx: ann.rx,
        ry: ann.ry,
      };
    }

    if (ann.type === "polygon") {
      return {
        shape_type: "polygon",
        points: ann.points,
      };
    }

    return {};
  }

  const commitPendingAnnotation = async () => {
    if (!pendingAnn || !imageKey) return;

    const currentUser = getCurrentUser();

    const nextAnn: Annotation = {
      ...pendingAnn,
      _source: normalizeSource((pendingAnn as any)?._source),
      label: formLabel.trim() || null,
      severity: formSeverity,
      category: formCategory || null,
      description: formDescription.trim() || null,
      recommendation: formRecommendation.trim() || null,
      tags: formTags.split(",").map((t) => t.trim()).filter(Boolean),
      notes: formDescription.trim() || null,
      ownerId: currentUser.id,
      ownerName: currentUser.name,
      strokeColor: drawStrokeColor,
      fillColor: drawFillColor,
      strokeWidth: drawStrokeWidth,
      createdAt: pendingAnn.createdAt || new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };

    setAnnotations((prev) => {
      const next = [...prev, nextAnn];
      saveAnnotations(imageKey, next);
      return next;
    });

    setPendingAnn(null);
    setDraftAnnotations([]);
    setSelectedAnnotation(nextAnn);
    setFormMode("view");
    setDetailOpen(false);
    resetFormFields();

    try {
      if (!imageId || !caseId) {
        return;
      }

      const saved = await postAnnotationToApi({
        imageId,
        caseId,
        ann: nextAnn,
      });

      const savedAnn: Annotation = {
        ...nextAnn,
        id: saved.id as string,
        _source: "api",
        ownerId: saved.user_id ?? nextAnn.ownerId,
        ownerName: saved.owner_name ?? nextAnn.ownerName,
        createdAt: saved.created_at ?? nextAnn.createdAt,
        updatedAt: saved.updated_at ?? nextAnn.updatedAt,
        severity: saved.severity ?? nextAnn.severity,
        category: saved.category ?? nextAnn.category,
        description: saved.description ?? nextAnn.description,
        recommendation: saved.recommendation ?? nextAnn.recommendation,
        tags: Array.isArray(saved.tags) ? saved.tags : nextAnn.tags,
        strokeColor: saved.stroke_color ?? nextAnn.strokeColor,
        fillColor: saved.fill_color ?? nextAnn.fillColor,
        strokeWidth:
          typeof saved.stroke_width === "number"
            ? saved.stroke_width
            : nextAnn.strokeWidth,
      };

      setAnnotations((prev) => {
        const replaced = prev.map((a) =>
          a.id === nextAnn.id ? savedAnn : a,
        );
        saveAnnotations(imageKey, replaced);
        return replaced;
      });

      setSelectedAnnotation(savedAnn);
    } catch (e) {
      console.error(e);
    }
  };

  const annotationItems = useMemo(() => {
    return [...annotations]
      .filter((a) => a && (a.type === "rect" || a.type === "circle" || a.type === "polygon"))
      .sort((a, b) => {
        const da = new Date(a.createdAt).getTime();
        const db = new Date(b.createdAt).getTime();
        return db - da;
      });
  }, [annotations]);

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
          <ToolButton
            title="Paramètres de dessin"
            active={drawSettingsOpen}
            disabled={!canAnnotate}
            onClick={() => setDrawSettingsOpen((v) => !v)}
            icon={IconSliders}
          />
        </div>

        {drawTool === "polygon" && annotateMode && (
          <>
            <div style={styles.divider} />
            <div style={styles.group}>
              <ToolButton
                title="Terminer polygone"
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

        {drawSettingsOpen && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr 1fr",
              gap: 12,
              padding: 12,
              border: "1px solid #e6e6e6",
              borderRadius: 10,
              background: "#fff",
            }}
          >
            <label style={modalStyles.label}>
              Couleur ligne
              <input
                type="color"
                value={toColorInput(drawStrokeColor)}
                onChange={(e) => setDrawStrokeColor(e.target.value)}
                style={styles.colorInput}
              />
            </label>

            <label style={modalStyles.label}>
              Couleur fond
              <input
                type="color"
                value={toColorInput(drawFillColor)}
                onChange={(e) => {
                  const hex = e.target.value;
                  setDrawFillColor(hexToRgba(hex, 0.18));
                }}
                style={styles.colorInput}
              />
            </label>

            <label style={modalStyles.label}>
              Épaisseur ligne
              <input
                type="range"
                min={1}
                max={8}
                step={1}
                value={drawStrokeWidth}
                onChange={(e) => setDrawStrokeWidth(Number(e.target.value))}
              />
              <span>{drawStrokeWidth}px</span>
            </label>
          </div>
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

      <div style={styles.contentLayout}>
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

        <div style={styles.sidebar}>
          <div style={styles.sidebarHeader}>Labels / annotations</div>

          {annotationItems.length === 0 ? (
            <div style={styles.emptyState}>Aucune annotation</div>
          ) : (
            <div style={styles.annotationList}>
              {annotationItems.map((ann) => {
                const owner = ann.ownerName || ann.ownerId || "Inconnu";
                const title =
                  ann.label?.trim() ||
                  `${ann.type === "rect"
                    ? "Rectangle"
                    : ann.type === "circle"
                      ? "Cercle"
                      : "Polygone"
                  } sans label`;

                return (
                  <div
                    key={ann.id}
                    style={{
                      ...styles.annotationCard,
                      ...(selectedAnnotation?.id === ann.id
                        ? styles.annotationCardActive
                        : null),
                    }}
                  >
                    <div style={styles.annotationCardTop}>
                      <div style={styles.annotationTitle}>{title}</div>
                      <div style={styles.annotationType}>{ann.type}</div>
                    </div>

                    <div style={styles.annotationMeta}>
                      <div>
                        <strong>Utilisateur :</strong> {owner}
                      </div>
                      <div>
                        <strong>Date :</strong>{" "}
                        {new Date(ann.createdAt).toLocaleString("fr-FR")}
                      </div>
                      {ann.severity && (
                        <div>
                          <strong>Sévérité :</strong> {ann.severity}
                        </div>
                      )}
                    </div>

                    <div style={styles.annotationActions}>
                      <button
                        type="button"
                        style={modalStyles.secondaryBtn}
                        onClick={() => openAnnotationDetails(ann)}
                      >
                        View
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {detailOpen && (
        <div style={modalStyles.backdrop}>
          <div style={modalStyles.modalLarge}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <h3 style={{ margin: 0 }}>
                {formMode === "create"
                  ? "Nouvelle annotation"
                  : formMode === "edit"
                    ? "Modifier l’annotation"
                    : "Détail de l’annotation"}
              </h3>

              <div style={{ display: "flex", gap: 8 }}>
                {selectedAnnotation &&
                  canEditAnnotation(selectedAnnotation) &&
                  formMode === "view" && (
                    <button
                      onClick={() => setFormMode("edit")}
                      style={modalStyles.secondaryBtn}
                    >
                      Modifier
                    </button>
                  )}
                <button onClick={closeDetailModal} style={modalStyles.secondaryBtn}>
                  Fermer
                </button>
              </div>
            </div>

            <div style={formGridStyles.grid}>
              <label style={modalStyles.label}>
                Label
                <input
                  value={formLabel}
                  onChange={(e) => setFormLabel(e.target.value)}
                  style={modalStyles.input}
                  disabled={formMode === "view"}
                  placeholder="Ex: Zone tumorale suspecte"
                />
              </label>

              <label style={modalStyles.label}>
                Catégorie
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value as any)}
                  style={modalStyles.input}
                  disabled={formMode === "view"}
                >
                  <option value="">Sélectionner</option>
                  <option value="Zone suspecte">Zone suspecte</option>
                  <option value="Nécrose">Nécrose</option>
                  <option value="Inflammation">Inflammation</option>
                  <option value="Tumeur">Tumeur</option>
                  <option value="Artefact">Artefact</option>
                  <option value="Autre">Autre</option>
                </select>
              </label>

              <label style={modalStyles.label}>
                Sévérité
                <select
                  value={formSeverity}
                  onChange={(e) => setFormSeverity(e.target.value as Severity)}
                  style={modalStyles.input}
                  disabled={formMode === "view"}
                >
                  <option value="Faible">Faible</option>
                  <option value="Moyenne">Moyenne</option>
                  <option value="Élevée">Élevée</option>
                </select>
              </label>

              <label style={modalStyles.label}>
                Tags
                <input
                  value={formTags}
                  onChange={(e) => setFormTags(e.target.value)}
                  style={modalStyles.input}
                  disabled={formMode === "view"}
                  placeholder="mitose, bordure, suspecte"
                />
              </label>

              <label style={{ ...modalStyles.label, gridColumn: "1 / -1" }}>
                Description
                <textarea
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  style={modalStyles.textarea}
                  disabled={formMode === "view"}
                  placeholder="Description détaillée de l’annotation"
                />
              </label>

              <label style={{ ...modalStyles.label, gridColumn: "1 / -1" }}>
                Recommandation / commentaire
                <textarea
                  value={formRecommendation}
                  onChange={(e) => setFormRecommendation(e.target.value)}
                  style={modalStyles.textarea}
                  disabled={formMode === "view"}
                  placeholder="Commentaire clinique ou recommandation"
                />
              </label>

              {selectedAnnotation && (
                <div style={formGridStyles.metaBox}>
                  <div>
                    <strong>Type :</strong> {selectedAnnotation.type}
                  </div>
                  <div>
                    <strong>Créé le :</strong>{" "}
                    {new Date(selectedAnnotation.createdAt).toLocaleString(
                      "fr-FR",
                    )}
                  </div>
                  <div>
                    <strong>Propriétaire :</strong>{" "}
                    {selectedAnnotation.ownerName ||
                      selectedAnnotation.ownerId ||
                      "Inconnu"}
                  </div>
                </div>
              )}
            </div>

            {(formMode === "create" || formMode === "edit") && (
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: 8,
                  marginTop: 14,
                }}
              >
                <button
                  onClick={() => {
                    closeDetailModal();
                  }}
                  style={modalStyles.secondaryBtn}
                >
                  Annuler
                </button>

                <button
                  onClick={() => {
                    if (formMode === "create") {
                      void commitPendingAnnotation();
                      return;
                    }

                    if (!selectedAnnotation || !imageKey) return;

                    const updated: Annotation = {
                      ...selectedAnnotation,
                      label: formLabel.trim() || null,
                      severity: formSeverity,
                      category: formCategory || null,
                      description: formDescription.trim() || null,
                      recommendation: formRecommendation.trim() || null,
                      tags: formTags
                        .split(",")
                        .map((t) => t.trim())
                        .filter(Boolean),
                      updatedAt: new Date().toISOString(),
                    };

                    setAnnotations((prev) => {
                      const next = prev.map((a) =>
                        a.id === selectedAnnotation.id ? updated : a,
                      );
                      saveAnnotations(imageKey, next);
                      return next;
                    });

                    setSelectedAnnotation(updated);
                    setFormMode("view");
                    setDetailOpen(true);
                  }}
                  style={modalStyles.primaryBtn}
                >
                  Enregistrer
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function redrawAll(
  viewer: OpenSeadragon.Viewer,
  annotations: Annotation[],
): void {
  const overlays = ((viewer as any).currentOverlays ?? []) as Array<{
    element?: HTMLElement;
  }>;

  overlays.forEach((o) => {
    const el = o?.element;
    if (!el) return;

    const kind = (el as any).dataset?.kind;
    if (kind === "persisted" || kind === "label") {
      try {
        viewer.removeOverlay(el);
      } catch {
        // ignore
      }
    }
  });

  annotations.forEach((ann) => {
    if (ann.type === "rect") {
      const el = document.createElement("div");
      el.style.boxSizing = "border-box";
      el.style.pointerEvents = "none";
      el.style.border = `${ann.strokeWidth ?? 2}px solid ${ann.strokeColor ?? "#ff3b30"}`;
      el.style.background = ann.fillColor ?? "rgba(224, 56, 47, 0.76)";
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
      el.style.border = `${ann.strokeWidth ?? 2}px solid ${ann.strokeColor ?? "#ff3b30"}`;
      el.style.background = ann.fillColor ?? "rgba(255,59,48,0.08)";
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

      let vminX = Infinity;
      let vminY = Infinity;
      let vmaxX = -Infinity;
      let vmaxY = -Infinity;

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
      (svg as any).dataset.kind = "persisted";

      const poly = document.createElementNS(svgNS, "polygon");
      poly.setAttribute("fill", "rgba(255,0,0,0.30)");
      poly.setAttribute("fill", ann.fillColor ?? "rgba(255,59,48,0.18)");
      poly.setAttribute("stroke", ann.strokeColor ?? "#ff3b30");
      poly.setAttribute(
        "stroke-width",
        String(Math.max(0.0006, (ann.strokeWidth ?? 2) * 0.0006)),
      );
      poly.setAttribute("stroke-linejoin", "round");
      poly.setAttribute(
        "points",
        vpts.map((p) => `${p.x},${p.y}`).join(" "),
      );

      svg.appendChild(poly);

      let minX = Infinity;
      let minY = Infinity;
      let maxX = -Infinity;
      let maxY = -Infinity;

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
      });

      viewer.addOverlay({ element: svg, location: rect });

      if (ann.label) {
        addLabel(
          viewer,
          { x: minX, y: minY, w: maxX - minX, h: maxY - minY },
          ann.label,
          "polygon",
        );
      }
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
  el.style.background = "rgba(255,255,255,0.92)";
  el.style.border = "1px solid #ddd";
  el.style.pointerEvents = "none";
  el.style.whiteSpace = "nowrap";
  el.dataset.kind = "label";

  const x =
    kind === "circle"
      ? (shape as CircleAnnotation).cx - (shape as CircleAnnotation).rx
      : (shape as any).x;
  const y =
    kind === "circle"
      ? (shape as CircleAnnotation).cy - (shape as CircleAnnotation).ry
      : (shape as any).y;

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
  contentLayout: {
    display: "grid",
    gridTemplateColumns: "minmax(0,1fr) 300px",
    gap: 12,
    flex: 1,
    minHeight: 0,
  },
  sidebar: {
    border: "1px solid #e6e6e6",
    borderRadius: 10,
    background: "#fff",
    display: "flex",
    flexDirection: "column",
    minHeight: 320,
    overflow: "hidden",
  },
  sidebarHeader: {
    padding: "12px 14px",
    borderBottom: "1px solid #eee",
    fontWeight: 600,
    fontSize: 14,
  },
  emptyState: {
    padding: 14,
    color: "#666",
    fontSize: 13,
  },
  annotationList: {
    display: "flex",
    flexDirection: "column",
    gap: 10,
    padding: 10,
    overflowY: "auto",
  },
  annotationCard: {
    border: "1px solid #e5e7eb",
    borderRadius: 10,
    padding: 10,
    display: "grid",
    gap: 8,
    background: "#fff",
  },
  annotationCardActive: {
    borderColor: "#ff3b30",
    boxShadow: "0 0 0 2px rgba(255,59,48,0.08)",
  },
  annotationCardTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  },
  annotationTitle: {
    fontWeight: 600,
    fontSize: 13,
    color: "#111827",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  annotationType: {
    fontSize: 11,
    padding: "2px 6px",
    borderRadius: 999,
    background: "#f3f4f6",
    color: "#374151",
    textTransform: "uppercase",
  },
  annotationMeta: {
    display: "grid",
    gap: 4,
    fontSize: 12,
    color: "#4b5563",
  },
  annotationActions: {
    display: "flex",
    justifyContent: "flex-end",
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
  modalLarge: {
    width: "min(760px, 94vw)",
    background: "#fff",
    borderRadius: 12,
    border: "1px solid #e6e6e6",
    boxShadow: "0 12px 30px rgba(0,0,0,0.18)",
    padding: 16,
  },
  textarea: {
    width: "100%",
    minHeight: 110,
    padding: 10,
    borderRadius: 10,
    border: "1px solid #ddd",
    resize: "vertical",
  },
  colorInput: {
    width: "100%",
    height: 40,
    border: "1px solid #ddd",
    borderRadius: 8,
    padding: 4,
    background: "#fff",
  },
};

const formGridStyles: Record<string, React.CSSProperties> = {
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 12,
  },
  metaBox: {
    gridColumn: "1 / -1",
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 12,
    fontSize: 13,
    color: "#334155",
    display: "grid",
    gap: 6,
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

function IconSliders() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
      <path d="M4 5h10M4 9h10M4 13h10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <circle cx="7" cy="5" r="1.6" fill="currentColor" />
      <circle cx="11" cy="9" r="1.6" fill="currentColor" />
      <circle cx="6" cy="13" r="1.6" fill="currentColor" />
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

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace("#", "");
  const bigint = parseInt(normalized, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r},${g},${b},${alpha})`;
}

function toColorInput(color: string) {
  if (!color) return "#ff3b30";
  if (color.startsWith("#")) return color;

  const match = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
  if (!match) return "#ff3b30";

  const r = Number(match[1]).toString(16).padStart(2, "0");
  const g = Number(match[2]).toString(16).padStart(2, "0");
  const b = Number(match[3]).toString(16).padStart(2, "0");
  return `#${r}${g}${b}`;
}