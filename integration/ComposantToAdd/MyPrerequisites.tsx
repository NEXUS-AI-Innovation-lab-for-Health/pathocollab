import { useState, useEffect } from 'react';
import { Page, UserRole } from '../App';
import {
  CheckCircle2,
  Circle,
  Clock,
  Video,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  AlertCircle,
  Loader2,
  Users,
  Plus,
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Alert, AlertDescription } from './ui/alert';
import type { PrerequisiteFormContext } from './PrerequisiteFormPage';
import { useLanguage } from '../i18n';
import {
  prerequisitesService,
  type MyMeetingPrerequisites,
  type MyPrerequisiteItem,
  type ParticipantPrerequisites,
} from '../services/prerequisites.service';
// Partie PathoCollab //
import PathoCollabCaseModal from './Patho/PathoCollabCaseModal';
import PathoCollabExternalCaseDetail from './Patho/PathoCollabExternalCaseDetail';
////////////////////////

interface Props {
  userRole: UserRole;
  onNavigate: (page: Page) => void;
  onOpenPrerequisiteForm?: (context: PrerequisiteFormContext) => void;
  onOpenScheduleModal?: () => void;
  onOpenPrerequisitePreparation?: (meetingId: string, meetingTitle: string) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusColor(status: MyPrerequisiteItem['status']): string {
  // Medical UI - soft, professional colors
  if (status === 'done') return '#059669'; // soft green
  if (status === 'in_progress') return '#d97706'; // soft orange
  return '#dc2626'; // soft red
}

function StatusIcon({ status }: { status: MyPrerequisiteItem['status'] }) {
  if (status === 'done') return <CheckCircle2 className="w-4 h-4" style={{ color: '#059669' }} />;
  if (status === 'in_progress') return <Clock className="w-4 h-4" style={{ color: '#d97706' }} />;
  return <Circle className="w-4 h-4" style={{ color: '#dc2626' }} />;
}

function MeetingStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; className: string }> = {
    scheduled: { label: 'Planifiée', className: 'bg-blue-50 text-blue-700 border border-blue-200' },
    live: { label: 'En cours', className: 'bg-emerald-50 text-emerald-700 border border-emerald-200' },
    draft: { label: 'Brouillon', className: 'bg-gray-50 text-gray-600 border border-gray-200' },
    finished: { label: 'Terminée', className: 'bg-slate-50 text-slate-600 border border-slate-200' },
    postponed: { label: 'Reportée', className: 'bg-amber-50 text-amber-700 border border-amber-200' },
  };
  const { label, className } = map[status] ?? { label: status, className: 'bg-gray-50 text-gray-600 border border-gray-200' };
  return <Badge className={`text-xs px-3 py-1 rounded-full font-medium ${className}`}>{label}</Badge>;
}

// ── Composant principal ───────────────────────────────────────────────────────

export function MyPrerequisites({ onNavigate, onOpenPrerequisiteForm, onOpenScheduleModal, onOpenPrerequisitePreparation }: Props) {
  const { t } = useLanguage();
  const [meetings, setMeetings] = useState<MyMeetingPrerequisites[]>([]);
  const [expandedMeetings, setExpandedMeetings] = useState<Set<string>>(new Set());
  const [adminExpanded, setAdminExpanded] = useState<Set<string>>(new Set());
  const [adminData, setAdminData] = useState<Record<string, ParticipantPrerequisites[]>>({});
  const [adminLoading, setAdminLoading] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Partie PathoCollab //
  const [pathocollabCaseIds, setPathocollabCaseIds] = useState<Record<string, string>>({});
  const [pathocollabCreating, setPathocollabCreating] = useState<Set<string>>(new Set());
  const [pathocollabOpenMeetingId, setPathocollabOpenMeetingId] = useState<string | null>(null);
  ////////////////////////

  useEffect(() => {
    load();
  }, []);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await prerequisitesService.getMyPrerequisites();
      setMeetings(data);
      // Ouvrir la première réunion par défaut
      if (data.length > 0) {
        setExpandedMeetings(new Set([data[0].meeting_id]));
      }
    } catch (err: any) {
      setError(err?.message ?? 'Erreur de chargement');
    } finally {
      setLoading(false);
    }
  };

  const toggleMeeting = (id: string) =>
    setExpandedMeetings((prev) => {
      const s = new Set(prev);
      s.has(id) ? s.delete(id) : s.add(id);
      return s;
    });

  const handleToggle = async (meetingId: string, item: MyPrerequisiteItem) => {
    const newCompleted = !item.completed;
    const newStatus: MyPrerequisiteItem['status'] = newCompleted ? 'done' : 'pending';

    // Optimistic update
    setMeetings((prev) =>
      prev.map((m) =>
        m.meeting_id !== meetingId
          ? m
          : {
              ...m,
              prerequisites: m.prerequisites.map((p) =>
                p.id === item.id ? { ...p, completed: newCompleted, status: newStatus } : p,
              ),
            },
      ),
    );

    try {
      await prerequisitesService.togglePrerequisiteItem(meetingId, item.id, newCompleted);
    } catch (err: any) {
      // Revert on error
      setMeetings((prev) =>
        prev.map((m) =>
          m.meeting_id !== meetingId
            ? m
            : {
                ...m,
                prerequisites: m.prerequisites.map((p) =>
                  p.id === item.id ? { ...p, completed: item.completed, status: item.status } : p,
                ),
              },
        ),
      );
      setError(err?.message ?? 'Impossible de mettre à jour le prérequis');
    }
  };

  const loadAdminView = async (meetingId: string) => {
    // Toggle collapse if already loaded
    if (adminExpanded.has(meetingId)) {
      setAdminExpanded((prev) => { const s = new Set(prev); s.delete(meetingId); return s; });
      return;
    }

    // Load participants
    setAdminLoading((prev) => new Set(prev).add(meetingId));
    try {
      const participants = await prerequisitesService.getAllParticipantsPrerequisites(meetingId);
      setAdminData((prev) => ({ ...prev, [meetingId]: participants }));
      setAdminExpanded((prev) => new Set(prev).add(meetingId));
    } catch (err: any) {
      setError(err?.message ?? 'Impossible de charger les prérequis des participants');
    } finally {
      setAdminLoading((prev) => { const s = new Set(prev); s.delete(meetingId); return s; });
    }
  };

  const openPrerequisiteForm = (meeting: MyMeetingPrerequisites) => {
    if (!onOpenPrerequisiteForm) {
      return;
    }

    const target = meeting.prerequisites.find((item) => item.source === 'form') || meeting.prerequisites[0];
    if (!target) {
      return;
    }

    const resolvedPrerequisiteId = (target.id || '').trim() || (target.key || '').trim() || 'olga_form';

    onOpenPrerequisiteForm({
      meetingId: meeting.meeting_id,
      prerequisiteId: resolvedPrerequisiteId,
      role: meeting.speciality || 'Non spécifié',
      title: `Formulaire Olga - ${meeting.meeting_title}`,
      description: 'Complétez les champs dynamiques liés à votre spécialité.',
      language: 'fr',
      returnPage: 'mes-prerequis',
      items: meeting.prerequisites.map((item) => ({
        key: item.key || item.id,
        label: item.label,
        status: item.status,
        source: item.source,
        reference_id: item.reference_id,
        value: item.value,
      })),
    });
  };

  // Partie PathoCollab //
  const openPathoCollabAnalysis = async (meeting: MyMeetingPrerequisites) => {
    const meetingId = meeting.meeting_id;
    const storageKey = `pathocollab_case_${meetingId}`;
    const existingCaseId = pathocollabCaseIds[meetingId] || localStorage.getItem(storageKey);

    if (existingCaseId) {
      setPathocollabCaseIds((prev) => ({ ...prev, [meetingId]: existingCaseId }));
      setPathocollabOpenMeetingId(meetingId);
      return;
    }

    setPathocollabCreating((prev) => new Set(prev).add(meetingId));
    try {
      const meetingData = await prerequisitesService.getMeetingPrerequisites(meetingId, false);

      const patientId = getPathoCollabPatientId(meeting);

      if (!patientId) {
        setError("Impossible d’ouvrir PathoCollab : aucun identifiant patient n’est lié à cette réunion.");
        return;
      }

      const response = await fetch('http://localhost:18002/api/cases/external', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source: 'oncocollab',
          external_reference: meetingId,

          patient: {
            id: patientId,
            full_name: meeting.patient_name || meeting.patient?.full_name || `Patient ${patientId}`,
            age: meeting.patient_age || meeting.patient?.age || 0,
            gender: meeting.patient_gender || meeting.patient?.gender || "Non renseigné",
          },

          title: `Analyse PathoCollab - ${meeting.meeting_title}`,
          description: `Cas créé depuis les prérequis de la réunion ${meeting.meeting_title}`,

          specialists_order: meetingData.doctors.map((doctor: { doctor_id: string }) => doctor.doctor_id),

          metadata: {
            meeting_id: meetingId,
            meeting_title: meeting.meeting_title,
            prerequisites: meetingData.doctors.map((doctor: { doctor_id: string; speciality: string; items: unknown }) => ({
              doctor_id: doctor.doctor_id,
              speciality: doctor.speciality,
              items: doctor.items,
            })),
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Erreur création cas PathoCollab');
      }

      const data = await response.json();

      localStorage.setItem(storageKey, data.case_id);
      setPathocollabCaseIds((prev) => ({ ...prev, [meetingId]: data.case_id }));
      setPathocollabOpenMeetingId(meetingId);
    } catch (err) {
      console.error(err);
      setError("Impossible de créer ou d'ouvrir l'analyse PathoCollab.");
    } finally {
      setPathocollabCreating((prev) => {
        const s = new Set(prev);
        s.delete(meetingId);
        return s;
      });
    }
  };
  ////////////////////////

  // ── Stats globales ──────────────────────────────────────────────────────────

  const totalDone = meetings.reduce(
    (acc, m) => acc + m.prerequisites.filter((p) => p.status === 'done').length,
    0,
  );
  const totalAll = meetings.reduce((acc, m) => acc + m.prerequisites.length, 0);
  const globalPct = totalAll > 0 ? Math.round((totalDone / totalAll) * 100) : 0;

  // ── Render ──────────────────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-10 h-10 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-gray-600 text-base">Chargement de vos prérequis…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-6xl mx-auto space-y-8">

        {/* En-tête professionnelle */}
        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-4xl font-semibold text-gray-900">{t.myPrerequisites.title}</h1>
            <p className="text-gray-500 text-base mt-2">{t.myPrerequisites.subtitle}</p>
          </div>
          <div className="flex gap-3 items-center">
            {/* Pilotage Button - Admin Only */}
            {meetings.some(m => m.is_admin) && (
              <Button
                onClick={() => {}}
                className="bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 text-white shadow-md"
              >
                <Users className="w-4 h-4 mr-2" />
                Pilotage
              </Button>
            )}
            <Button onClick={() => onNavigate('reunions')} className="bg-blue-600 hover:bg-blue-700 text-white shadow-md" variant="default">
              <Video className="w-4 h-4 mr-2" />
              {t.myPrerequisites.viewMeetings}
            </Button>
            {onOpenScheduleModal && (
              <Button onClick={onOpenScheduleModal} className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md">
                <Plus className="w-4 h-4 mr-2" />
                Programmer une RCP
              </Button>
            )}
          </div>
        </div>

        {/* Erreur */}
        {error && (
          <Alert className="border-red-200 bg-red-50 rounded-xl">
            <AlertCircle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-800 text-sm">
              {error}
              <Button variant="link" className="ml-2 text-red-600 underline p-0 h-auto text-sm" onClick={load}>
                {t.myPrerequisites.retry}
              </Button>
            </AlertDescription>
          </Alert>
        )}

        {/* Carte progression globale - Professional Medical Style */}
        <Card className="bg-white border border-gray-200 shadow-sm rounded-2xl overflow-hidden">
          <CardContent className="p-8">
            <div className="grid grid-cols-3 gap-6">
              <div>
                <p className="text-sm font-semibold text-gray-600 mb-2">{t.myPrerequisites.globalProgress}</p>
                <p className="text-3xl font-semibold text-blue-600">{globalPct}%</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-600 mb-2">Complétés</p>
                <p className="text-3xl font-semibold text-emerald-600">{totalDone} / {totalAll}</p>
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-600 mb-2">Réunions</p>
                <p className="text-3xl font-semibold text-gray-900">{meetings.length}</p>
              </div>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden mt-6">
              <div
                className="h-full bg-gradient-to-r from-blue-500 via-emerald-500 to-blue-600 transition-all duration-500 rounded-full"
                style={{ width: `${globalPct}%` }}
              />
            </div>
          </CardContent>
        </Card>

        {/* Liste des réunions */}
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold text-gray-900">
              Réunions RCP <span className="text-gray-500 font-normal">({meetings.length})</span>
            </h2>
          </div>

          {loading ? (
            <Card className="bg-white border border-gray-200 shadow-sm rounded-2xl">
              <CardContent className="p-12 text-center">
                <Loader2 className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Chargement des données...</p>
              </CardContent>
            </Card>
          ) : meetings.length === 0 ? (
            <Card className="bg-white border border-gray-200 shadow-sm rounded-2xl">
              <CardContent className="p-16 text-center">
                <p className="text-gray-500 text-base">{t.myPrerequisites.noMeetings}</p>
              </CardContent>
            </Card>
          ) : (
            meetings.map((meeting) => {
              const isOpen = expandedMeetings.has(meeting.meeting_id);
              const done = meeting.prerequisites.filter((p) => p.status === 'done').length;
              const total = meeting.prerequisites.length;
              const pct = total > 0 ? Math.round((done / total) * 100) : 0;
              const allDone = total > 0 && done === total;
              const adminOpen = adminExpanded.has(meeting.meeting_id);
              const loadingAdmin = adminLoading.has(meeting.meeting_id);

              return (
                <Card
                  key={meeting.meeting_id}
                  className="bg-white border border-gray-200 shadow-sm rounded-2xl transition-all duration-200 hover:shadow-md hover:border-gray-300"
                >
                  {/* Header réunion */}
                  <CardHeader
                    className="cursor-pointer select-none py-6 hover:bg-gray-50/50 transition-colors px-8"
                    onClick={() => toggleMeeting(meeting.meeting_id)}
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="mb-4">
                          <CardTitle className="text-xl font-semibold text-gray-900">{meeting.meeting_title}</CardTitle>
                        </div>

                        {/* Badges et statuts */}
                        <div className="flex flex-wrap gap-2 items-center mb-4">
                          <MeetingStatusBadge status={meeting.meeting_status} />
                          {meeting.is_admin && (
                            <Badge className="bg-blue-50 text-blue-700 border border-blue-200 text-xs px-3 py-1 rounded-full font-medium">
                              👨‍💼 Admin
                            </Badge>
                          )}
                          {allDone ? (
                            <Badge className="bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs px-3 py-1 rounded-full font-medium">
                              ✓ Complété
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="text-xs text-orange-600 border-orange-200 px-3 py-1 rounded-full font-medium">
                              {done}/{total} en cours
                            </Badge>
                          )}
                        </div>

                        {/* Barre de progression */}
                        {total > 0 && (
                          <div className="flex items-center gap-4">
                            <div className="flex-1">
                              <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                                <div
                                  className={`h-1.5 rounded-full transition-all duration-500 ${
                                    allDone ? 'bg-emerald-500' : 'bg-blue-500'
                                  }`}
                                  style={{ width: `${pct}%` }}
                                />
                              </div>
                            </div>
                            <span className="text-sm font-semibold text-gray-700 whitespace-nowrap">{pct}%</span>
                          </div>
                        )}
                      </div>

                      <div className="flex-shrink-0">
                        {isOpen
                          ? <ChevronUp className="w-5 h-5 text-gray-400" />
                          : <ChevronDown className="w-5 h-5 text-gray-400" />}
                      </div>
                    </div>
                  </CardHeader>

                  {/* Corps expandable */}
                  {isOpen && (
                    <CardContent className="px-8 py-6 space-y-6 border-t border-gray-200 bg-gray-50/30">

                      {/* Mes prérequis */}
                      {total === 0 ? (
                        <p className="text-sm text-gray-500 italic py-4">
                          Aucun prérequis défini pour cette réunion.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          <p className="text-sm font-semibold text-gray-700 mb-3">Vos tâches</p>
                          {meeting.prerequisites.map((item) => (
                            <button
                              key={item.id}
                              type="button"
                              onClick={(e) => { e.stopPropagation(); handleToggle(meeting.meeting_id, item); }}
                              className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition-all duration-200 hover:bg-white active:bg-gray-100"
                              style={{
                                cursor: 'pointer',
                                backgroundColor:
                                  item.status === 'done'
                                    ? '#ecfdf5'
                                    : item.status === 'in_progress'
                                    ? '#fffbeb'
                                    : '#fef2f2',
                              }}
                            >
                              <StatusIcon status={item.status} />
                              <span className="text-sm font-medium flex-1 text-gray-900">
                                {item.label}
                              </span>
                              {item.status === 'done' && (
                                <span className="text-xs font-semibold text-emerald-700">Fait</span>
                              )}
                              {item.status === 'in_progress' && (
                                <span className="text-xs font-semibold text-orange-700">En cours</span>
                              )}
                              {item.status === 'pending' && (
                                <span className="text-xs font-semibold text-red-700">À faire</span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}

                      {/* Bouton admin - Voir les participants */}
                      {meeting.is_admin && (
                        <div className="pt-4 border-t border-gray-200">
                          <Button
                            variant="outline"
                            size="sm"
                            className="w-full text-blue-600 border-blue-200 hover:bg-blue-50 transition-colors"
                            onClick={(e) => {
                              e.stopPropagation();
                              loadAdminView(meeting.meeting_id);
                            }}
                            disabled={loadingAdmin}
                          >
                            {loadingAdmin ? (
                              <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            ) : (
                              <Users className="w-4 h-4 mr-2" />
                            )}
                            {adminOpen
                              ? 'Masquer les participants'
                              : '👥 Voir les participants'}
                            {!loadingAdmin && (
                              adminOpen
                                ? <ChevronUp className="w-4 h-4 ml-auto" />
                                : <ChevronRight className="w-4 h-4 ml-auto" />
                            )}
                          </Button>

                          {/* Vue participants - Professional monitoring */}
                          {adminOpen && adminData[meeting.meeting_id] && (
                            <div className="mt-4 space-y-3">
                              {adminData[meeting.meeting_id].length === 0 ? (
                                <p className="text-sm text-gray-500 text-center py-4">
                                  Aucun participant trouvé.
                                </p>
                              ) : (
                                <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                                  {adminData[meeting.meeting_id].map((participant, pIdx) => {
                                    const pDone = participant.prerequisites.filter((x) => x.status === 'done').length;
                                    const pTotal = participant.prerequisites.length;
                                    const pPct = pTotal > 0 ? Math.round((pDone / pTotal) * 100) : 0;

                                    return (
                                      <div
                                        key={pIdx}
                                        className={`p-4 ${
                                          pIdx > 0 ? 'border-t border-gray-200' : ''
                                        } hover:bg-gray-50/50 transition-colors`}
                                      >
                                        <div className="flex items-center justify-between mb-3">
                                          <div>
                                            <p className="text-sm font-semibold text-gray-900">
                                              {participant.doctor_name}
                                            </p>
                                            <p className="text-xs text-gray-500">{participant.doctor_email}</p>
                                          </div>
                                          <div className="text-right">
                                            <p className="text-sm font-semibold text-blue-600">{pPct}%</p>
                                            <p className="text-xs text-gray-500">{pDone}/{pTotal}</p>
                                          </div>
                                        </div>

                                        {pTotal === 0 ? (
                                          <p className="text-xs text-gray-400 italic">
                                            Aucun prérequis défini.
                                          </p>
                                        ) : (
                                          <div className="space-y-1">
                                            {participant.prerequisites.map((item, iIdx) => (
                                              <div
                                                key={iIdx}
                                                className="flex items-center gap-2 text-xs"
                                              >
                                                <StatusIcon status={item.status} />
                                                <span
                                                  className="flex-1 font-medium"
                                                  style={{ color: statusColor(item.status) }}
                                                >
                                                  {item.label}
                                                </span>
                                              </div>
                                            ))}
                                          </div>
                                        )}
                                      </div>
                                    );
                                  })}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex gap-3 pt-3 border-t border-gray-200">
                        <Button
                          size="sm"
                          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-medium shadow-sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            if (onOpenPrerequisitePreparation) {
                              onOpenPrerequisitePreparation(meeting.meeting_id, meeting.meeting_title);
                            }
                          }}
                        >
                          ✓ Préparer les tâches
                        </Button>

                        {/* Partie PathoCollab */}
                        <Button
                          size="sm"
                          className="flex-1 bg-purple-600 hover:bg-purple-700 text-white font-medium shadow-sm"
                          disabled={!allDone || pathocollabCreating.has(meeting.meeting_id)}
                          onClick={(e) => {
                            e.stopPropagation();
                            openPathoCollabAnalysis(meeting);
                          }}
                        >
                          {pathocollabCreating.has(meeting.meeting_id) ? 'Création du cas...' : 'Analyse PathoCollab'}
                        </Button>

                        <Button
                          variant="outline"
                          size="sm"
                          className="flex-1 text-gray-700 border-gray-200 hover:bg-gray-50"
                          onClick={(e) => { e.stopPropagation(); onNavigate('reunions'); }}
                        >
                          {t.myPrerequisites.viewDetails}
                        </Button>
                      </div>

                    </CardContent>
                  )}
                </Card>
              );
            })
          )}
        </div>

        {/* Partie PathoCollab */}
        <PathoCollabCaseModal
          open={!!pathocollabOpenMeetingId}
          title="Analyse PathoCollab"
          onClose={() => setPathocollabOpenMeetingId(null)}
        >
          {pathocollabOpenMeetingId && pathocollabCaseIds[pathocollabOpenMeetingId] && (
            <PathoCollabExternalCaseDetail
              caseId={pathocollabCaseIds[pathocollabOpenMeetingId]}
              apiBaseUrls={{
                cases: 'http://localhost:18002',
                workflow: 'http://localhost:18003',
                images: 'http://localhost:18004',
                reports: 'http://localhost:18005',
              }}
              currentUserId={myDoctor.doctor_id}
            />
          )}
        </PathoCollabCaseModal>

        {/* Tip Section - Professional Help */}
        <Card className="bg-blue-50 border border-blue-200 rounded-2xl shadow-sm">
          <CardContent className="p-6">
            <p className="text-sm text-blue-900">
              <span className="mr-3 text-lg">💡</span>
              <strong className="font-semibold">{t.myPrerequisites.tip} :</strong> <span className="text-blue-800">{t.myPrerequisites.tipText}</span>
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
