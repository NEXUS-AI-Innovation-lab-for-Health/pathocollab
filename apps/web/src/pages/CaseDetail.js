import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import axios from 'axios';
import { ArrowLeft, User, FileText, Image, Users, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';

const CASES_API = process.env.REACT_APP_BACKEND_URL?.replace('8001', '8002') || 'http://localhost:8002';
const WORKFLOW_API = process.env.REACT_APP_BACKEND_URL?.replace('8001', '8003') || 'http://localhost:8003';

const CaseDetail = () => {
  const { caseId } = useParams();
  const navigate = useNavigate();
  const [caseData, setCase] = useState(null);
  const [patient, setPatient] = useState(null);
  const [workflow, setWorkflow] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchCaseDetails();
  }, [caseId]);

  const fetchCaseDetails = async () => {
    try {
      // Fetch case
      const caseResponse = await axios.get(`${CASES_API}/api/cases/${caseId}`);
      setCase(caseResponse.data);

      // Fetch patient
      const patientResponse = await axios.get(
        `${CASES_API}/api/patients/${caseResponse.data.patient_id}`
      );
      setPatient(patientResponse.data);

      // Fetch workflow
      try {
        const workflowResponse = await axios.get(
          `${WORKFLOW_API}/api/workflows/case/${caseId}`
        );
        setWorkflow(workflowResponse.data);
      } catch (err) {
        console.log('No workflow found for this case');
      }
    } catch (error) {
      console.error('Error fetching case details:', error);
      toast.error('Erreur lors du chargement du cas');
    } finally {
      setLoading(false);
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
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/dashboard')}
              data-testid="back-button"
            >
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">{caseData.id}</h1>
                <Badge className={`bg-${caseData.status === 'completed' ? 'green' : 'blue'}-100`}>
                  {caseData.status}
                </Badge>
              </div>
              <p className="text-sm text-slate-500 mt-1">{caseData.title}</p>
            </div>
            <Button data-testid="start-analysis-button">Commencer mon rapport</Button>
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

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
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
                        <p className="text-sm font-medium text-slate-500">Antécédents</p>
                        <p className="text-base text-slate-900">{patient.medical_history}</p>
                      </div>
                    )}
                    {patient.symptoms && (
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-slate-500">Symptômes</p>
                        <p className="text-base text-slate-900">{patient.symptoms}</p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}

            {workflow && (
              <Card data-testid="workflow-card">
                <CardHeader>
                  <CardTitle>Workflow Collaboratif</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {workflow.specialists_order.map((specialist, index) => (
                      <div
                        key={index}
                        className={`flex items-center gap-3 p-3 rounded-lg border ${
                          index === workflow.current_step
                            ? 'border-blue-300 bg-blue-50'
                            : index < workflow.current_step
                            ? 'border-green-300 bg-green-50'
                            : 'border-slate-200 bg-slate-50'
                        }`}
                        data-testid={`workflow-step-${index}`}
                      >
                        <div
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                            index === workflow.current_step
                              ? 'bg-blue-600 text-white'
                              : index < workflow.current_step
                              ? 'bg-green-600 text-white'
                              : 'bg-slate-300 text-slate-600'
                          }`}
                        >
                          {index + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-medium text-slate-900">Spécialiste {specialist}</p>
                          <p className="text-sm text-slate-500">
                            {index === workflow.current_step
                              ? "En cours d'analyse"
                              : index < workflow.current_step
                              ? 'Terminé'
                              : 'En attente'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Images Tab */}
          <TabsContent value="images">
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-slate-500 py-8">
                  Visualiseur d'images WSI avec OpenSeadragon (à implémenter)
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Reports Tab */}
          <TabsContent value="reports">
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-slate-500 py-8">
                  Liste des rapports des spécialistes (à implémenter)
                </p>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Team Tab */}
          <TabsContent value="team">
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-3">
                  {caseData.assigned_specialists?.map((specialist, index) => (
                    <div
                      key={index}
                      className="flex items-center gap-3 p-3 border border-slate-200 rounded-lg"
                    >
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-600 to-cyan-600 flex items-center justify-center text-white font-bold">
                        {specialist.substring(0, 2).toUpperCase()}
                      </div>
                      <div>
                        <p className="font-medium text-slate-900">{specialist}</p>
                        <p className="text-sm text-slate-500">Spécialiste</p>
                      </div>
                    </div>
                  )) || <p className="text-center text-slate-500">Aucun spécialiste assigné</p>}
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Discussion Tab */}
          <TabsContent value="discussion">
            <Card>
              <CardContent className="pt-6">
                <p className="text-center text-slate-500 py-8">
                  Chat collaboratif entre spécialistes (à implémenter)
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
};

export default CaseDetail;
