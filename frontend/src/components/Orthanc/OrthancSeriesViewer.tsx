import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ChevronLeft, ChevronRight, Download, Layers } from "lucide-react";

const IMAGES_API =
    process.env.REACT_APP_IMAGES_URL ||
    `${window.location.protocol}//${window.location.hostname}:8004`;

type RadiologySeriesSummary = {
    id: string;
    app_patient_id: string;
    case_id: string;
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
    raw_minio_prefix?: string | null;
};

type SeriesInstance = {
    instance_id: string;
    instance_number?: number | string | null;
    index_in_series?: number | null;
    sop_instance_uid?: string | null;
    preview_url: string;
    file_url: string;
};

type Props = {
    series: RadiologySeriesSummary | null;
};

export default function OrthancSeriesViewer({ series }: Props) {
    const [instances, setInstances] = useState<SeriesInstance[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);

    useEffect(() => {
        if (!series?.orthanc_series_id) {
        setInstances([]);
        setCurrentIndex(0);
        return;
        }

        let cancelled = false;

        (async () => {
            try {
                setLoading(true);
                setError(null);
                setInstances([]);
                setCurrentIndex(0);

                const token = localStorage.getItem("access_token");
                const res = await axios.get(
                `${IMAGES_API}/api/radiology/series/${encodeURIComponent(series.orthanc_series_id)}/instances`,
                token ? { headers: { Authorization: `Bearer ${token}` } } : undefined
                );

                if (cancelled) return;

                const list = res.data?.instances || [];
                setInstances(list);
                setCurrentIndex(0);
            } catch (e: any) {
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

    const current = useMemo(() => {
        if (!instances.length) return null;
        return instances[Math.max(0, Math.min(currentIndex, instances.length - 1))];
    }, [instances, currentIndex]);

    const currentPreviewUrl = current
        ? `${IMAGES_API}${current.preview_url}`
        : null;

    function prevSlice() {
        setCurrentIndex((i) => Math.max(0, i - 1));
    }

    function nextSlice() {
        setCurrentIndex((i) => Math.min(instances.length - 1, i + 1));
    }

    function onWheel(e: React.WheelEvent<HTMLDivElement>) {
        if (!instances.length) return;
        if (e.deltaY > 0) {
            nextSlice();
        } else if (e.deltaY < 0) {
            prevSlice();
        }
    }

    if (!series) {
        return (
        <div className="h-full flex items-center justify-center text-slate-500">
            Sélectionnez une série radiologique.
        </div>
        );
    }

    return (
        <div className="grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_320px] gap-4 h-full">
        <div className="border border-slate-200 rounded-lg overflow-hidden bg-black">
            <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-slate-200">
            <div className="flex items-center gap-3">
                <Layers className="w-4 h-4 text-slate-600" />
                <div className="text-sm">
                <div className="font-medium text-slate-900">
                    {series.series_description || "Série radiologique"}
                </div>
                <div className="text-slate-500">
                    {series.modality || "N/A"} · {series.instances_count} coupe(s)
                </div>
                </div>
            </div>

            <div className="flex items-center gap-2">
                <button
                onClick={prevSlice}
                disabled={!instances.length || currentIndex === 0}
                className="p-2 rounded-md border border-slate-200 bg-white disabled:opacity-50"
                title="Coupe précédente"
                >
                <ChevronLeft className="w-4 h-4" />
                </button>

                <div className="text-sm text-slate-700 min-w-[90px] text-center">
                {instances.length ? `${currentIndex + 1} / ${instances.length}` : "0 / 0"}
                </div>

                <button
                onClick={nextSlice}
                disabled={!instances.length || currentIndex >= instances.length - 1}
                className="p-2 rounded-md border border-slate-200 bg-white disabled:opacity-50"
                title="Coupe suivante"
                >
                <ChevronRight className="w-4 h-4" />
                </button>

                {current && (
                <a
                    href={`${IMAGES_API}${current.file_url}`}
                    target="_blank"
                    rel="noreferrer"
                    className="p-2 rounded-md border border-slate-200 bg-white"
                    title="Télécharger le DICOM"
                >
                    <Download className="w-4 h-4" />
                </a>
                )}
            </div>
            </div>

            <div
            className="h-[70vh] min-h-[520px] flex items-center justify-center bg-black select-none"
            onWheel={onWheel}
            >
            {loading ? (
                <div className="text-slate-300 text-sm">Chargement de la série…</div>
            ) : error ? (
                <div className="text-red-400 text-sm">{error}</div>
            ) : !currentPreviewUrl ? (
                <div className="text-slate-400 text-sm">Aucune coupe disponible.</div>
            ) : (
                <img
                src={currentPreviewUrl}
                alt={`Instance ${current?.instance_id}`}
                className="max-h-full max-w-full object-contain"
                draggable={false}
                />
            )}
            </div>
        </div>

        <aside className="border border-slate-200 rounded-lg bg-white overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 font-medium">
            Métadonnées
            </div>

            <div className="p-4 space-y-3 text-sm">
            <InfoRow label="Patient app" value={series.app_patient_id} />
            <InfoRow label="Patient DICOM" value={series.dicom_patient_id} />
            <InfoRow label="Nom DICOM" value={series.patient_name} />
            <InfoRow label="Case" value={series.case_id} />
            <InfoRow label="Modalité" value={series.modality} />
            <InfoRow label="Date étude" value={series.study_date} />
            <InfoRow label="Étude" value={series.study_description} />
            <InfoRow label="Série" value={series.series_description} />
            <InfoRow label="Coupes" value={String(series.instances_count)} />
            </div>

            <div className="border-t border-slate-200 px-4 py-3">
            <div className="text-sm font-medium mb-2">Miniatures</div>
            <div className="grid grid-cols-3 gap-2 max-h-[360px] overflow-auto">
                {instances.map((inst, idx) => (
                <button
                    key={inst.instance_id}
                    onClick={() => setCurrentIndex(idx)}
                    className={`border rounded-md overflow-hidden ${
                    idx === currentIndex
                        ? "border-blue-500 ring-1 ring-blue-500"
                        : "border-slate-200"
                    }`}
                    title={`Coupe ${idx + 1}`}
                >
                    <img
                    src={`${IMAGES_API}${inst.preview_url}`}
                    alt={`thumbnail-${inst.instance_id}`}
                    className="w-full h-20 object-cover bg-black"
                    draggable={false}
                    />
                </button>
                ))}
            </div>
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