export type AnnotationType = "rect" | "circle" | "polygon";

export interface BaseAnnotation {
    id: string;
    type: AnnotationType;
    label?: string | null;
    severity?: "Faible" | "Moyenne" | "Élevée";
    createdAt: string;
    _source?: "api" | "local" | "ia";
}

export interface RectAnnotation extends BaseAnnotation {
    type: "rect";
    x: number;
    y: number;
    w: number;
    h: number;
}

export interface CircleAnnotation extends BaseAnnotation {
    type: "circle";
    cx: number;
    cy: number;
    rx: number;
    ry: number;
}

export interface PolygonPoint {
    x: number;
    y: number;
}

export interface PolygonAnnotation extends BaseAnnotation {
    type: "polygon";
    points: PolygonPoint[];
}

export type Annotation =
    | RectAnnotation
    | CircleAnnotation
    | PolygonAnnotation;
