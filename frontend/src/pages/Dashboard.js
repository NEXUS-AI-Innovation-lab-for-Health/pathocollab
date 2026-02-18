import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import axios from "axios";
import {
  Bell,
  LogOut,
  FolderOpen,
  Users,
  ChevronDown,
  User,
} from "lucide-react";
import { toast } from "sonner";
import { getCurrentUser } from "@/services/auth";

const AUTH_API = process.env.REACT_APP_AUTH_URL || `${window.location.protocol}//${window.location.hostname}:8001`;
const CASES_API = process.env.REACT_APP_BACKEND_URL || `${window.location.protocol}//${window.location.hostname}:8002`;
const WORKFLOW_API = process.env.REACT_APP_WORKFLOW_URL || `${window.location.protocol}//${window.location.hostname}:8003`;

const Dashboard = () => {
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("Tous les statuts");
  const [specialistsCount, setSpecialistsCount] = useState(0);
  const [loadingSpecialists, setLoadingSpecialists] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showNotifications, setShowNotifications] = useState(false);
  const navigate = useNavigate();

  const getCurrentUserRole = () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      console.log("Aucun token trouvé pour IsAdmin");
      return null;
    }

    console.log("Token trouvé pour IsAdmin:");

    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      // selon ta création de token côté backend, ça peut être payload.role
      console.log("Payload du token:", payload.role);
      return payload.role || null;
    } catch (e) {
      console.error("Erreur lors du décodage du token pour IsAdmin:", e);
      return null;
    }
  };

  const isAdmin = () => getCurrentUserRole() === "admin";

  const statusOptions = [
    "Tous les statuts",
    "En attente",
    "En cours",
    "Terminé",
    "Annulé",
  ];

  useEffect(() => {
    fetchCases();
    fetchSpecialistsCount();
    fetchNotifications();
    // Récupérer les informations de l'utilisateur connecté
    const loadUser = async () => {
      const currentUser = await getCurrentUser();
      setUser(currentUser);
    };
    loadUser();
  }, []);

  const fetchNotifications = async () => {
    try {
      const token = localStorage.getItem("access_token");
      if (!token) {
        console.log("Aucun token trouvé");
        return;
      }

      // Récupérer l'email de l'utilisateur depuis le token
      const tokenData = JSON.parse(atob(token.split(".")[1]));
      const email = tokenData.sub || tokenData.email || "";

      console.log("Token décodé:", tokenData);
      console.log("Email extrait:", email);

      const response = await axios.get(
        `${WORKFLOW_API}/api/notifications/user/${email}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        },
      );

      console.log("Notifications reçues:", response.data);
      setNotifications(response.data);
      setUnreadCount(response.data.filter((n) => !n.is_read).length);
    } catch (error) {
      console.error("Erreur lors de la récupération des notifications:", error);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.patch(
        `${WORKFLOW_API}/api/notifications/${notificationId}/read`,
        {},
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );

      // Mettre à jour l'état local
      setNotifications((prev) =>
        prev.map((n) =>
          n.id === notificationId ? { ...n, is_read: true } : n,
        ),
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch (error) {
      console.error("Erreur lors du marquage comme lu:", error);
    }
  };

  // Rafraîchir les cas quand le composant redevient visible (après navigation)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden) {
        fetchCases();
      }
    };

    // Écouter les changements de focus de la fenêtre
    window.addEventListener("focus", fetchCases);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.removeEventListener("focus", fetchCases);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const fetchCases = async () => {
    try {
      // Récupérer les cas depuis l'API Cases Service
      const response = await axios.get(`${CASES_API}/api/cases/list`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        },
      });
      setCases(response.data);
    } catch (error) {
      console.error("Error fetching cases:", error);
      toast.error("Erreur lors du chargement des cas");
    } finally {
      setLoading(false);
    }
  };

  // Fonction pour supprimer un cas
  const handleDeleteCase = async (caseId, e) => {
    e.stopPropagation(); // Empêche le déclenchement du clic sur la carte
    if (
      window.confirm(
        "Êtes-vous sûr de vouloir supprimer ce cas ? Cette action est irréversible.",
      )
    ) {
      try {
        await axios.delete(`${CASES_API}/api/cases/delete/${caseId}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        });
        toast.success("Cas supprimé avec succès");
        fetchCases(); // Rafraîchir la liste des cas
      } catch (error) {
        console.error("Erreur lors de la suppression du cas:", error);
        toast.error("Erreur lors de la suppression du cas");
      }
    }
  };

  const fetchSpecialistsCount = async () => {
    try {
      const response = await axios.get(
        `${AUTH_API}/api/auth/specialists/count`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token")}`,
          },
        },
      );
      setSpecialistsCount(response.data.count);
    } catch (error) {
      console.error(
        "Erreur lors de la récupération du nombre de spécialistes:",
        error,
      );
      toast.error("Erreur lors du chargement des statistiques");
    } finally {
      setLoadingSpecialists(false);
    }
  };

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: "bg-yellow-100 text-yellow-800",
      in_progress: "bg-blue-100 text-blue-800",
      completed: "bg-green-100 text-green-800",
      cancelled: "bg-red-100 text-red-800",
    };
    return colors[status] || "bg-gray-100 text-gray-800";
  };

  const getStatusLabel = (status) => {
    const labels = {
      pending: "En attente",
      in_progress: "En cours",
      completed: "Terminé",
      cancelled: "Annulé",
    };
    return labels[status] || status;
  };

  const filteredCases = cases.filter((caseItem) => {
    const matchesSearch =
      caseItem.id.toString().includes(searchTerm.toLowerCase()) ||
      (caseItem.patient_id &&
        caseItem.patient_id
          .toString()
          .toLowerCase()
          .includes(searchTerm.toLowerCase())) ||
      (caseItem.title &&
        caseItem.title.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (caseItem.description &&
        caseItem.description.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus =
      statusFilter === "Tous les statuts" ||
      (statusFilter === "En attente" && caseItem.status === "pending") ||
      (statusFilter === "En cours" && caseItem.status === "in_progress") ||
      (statusFilter === "Terminé" && caseItem.status === "completed") ||
      (statusFilter === "Annulé" && caseItem.status === "cancelled");

    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-slate-50" data-testid="dashboard-page">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img
                src="/assets/logo.ico"
                alt="Logo PathoCollab"
                className="h-12 w-auto"
              />
              <h1 className="text-xl font-bold text-slate-900">PathoCollab</h1>
            </div>
            <div className="flex items-center gap-3">
              <DropdownMenu
                open={showNotifications}
                onOpenChange={setShowNotifications}
              >
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    data-testid="notifications-button"
                    className="relative"
                  >
                    <Bell className="h-5 w-5" />
                    {unreadCount > 0 && (
                      <span className="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                        {unreadCount}
                      </span>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-80">
                  <div className="p-2">
                    <h3 className="font-semibold text-sm mb-2">
                      Notifications
                    </h3>
                    {notifications.length === 0 ? (
                      <p className="text-sm text-gray-500 p-2">
                        Aucune notification
                      </p>
                    ) : (
                      <div className="max-h-64 overflow-y-auto">
                        {notifications.map((notification) => (
                          <div
                            key={notification.id}
                            className={`p-3 rounded-lg mb-2 cursor-pointer transition-colors ${
                              notification.is_read
                                ? "bg-gray-50 hover:bg-gray-100"
                                : "bg-blue-50 hover:bg-blue-100 border-l-4 border-blue-500"
                            }`}
                            onClick={() => {
                              markAsRead(notification.id);
                              navigate(`/cases/${notification.case_id}`);
                              setShowNotifications(false);
                            }}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-medium text-sm">
                                  {notification.title}
                                </p>
                                <p className="text-xs text-gray-600 mt-1">
                                  {notification.message}
                                </p>
                                <p className="text-xs text-gray-400 mt-2">
                                  {new Date(
                                    notification.created_at,
                                  ).toLocaleString("fr-FR")}
                                </p>
                              </div>
                              {!notification.is_read && (
                                <div className="w-2 h-2 bg-blue-500 rounded-full mt-1"></div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" className="flex items-center gap-2">
                    {user ? (
                      <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-r from-blue-600 to-cyan-600 flex items-center justify-center text-white font-medium">
                          {user.initial}
                        </div>
                        <span className="hidden sm:inline">
                          {user.fullName}
                        </span>
                        <ChevronDown className="h-4 w-4 opacity-50" />
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <User className="h-4 w-4" />
                        <span>Compte</span>
                      </div>
                    )}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem
                    onClick={handleLogout}
                    className="cursor-pointer"
                  >
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Déconnexion</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>
        <div className="border-t border-slate-100">
          <div className="max-w-7xl mx-auto px-6 py-2">
            <p className="text-sm text-slate-500">Tableau de bord</p>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    Cas en cours
                  </p>
                  <h3 className="text-3xl font-bold text-slate-900 mt-2">
                    {cases.filter((c) => c.status === "in_progress").length}
                  </h3>
                </div>
                <div className="w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                  <FolderOpen className="h-6 w-6 text-blue-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    Cas complétés
                  </p>
                  <h3 className="text-3xl font-bold text-slate-900 mt-2">
                    {cases.filter((c) => c.status === "completed").length}
                  </h3>
                </div>
                <div className="w-12 h-12 rounded-full bg-green-100 flex items-center justify-center">
                  <FolderOpen className="h-6 w-6 text-green-600" />
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">
                    Spécialistes
                  </p>
                  <h3 className="text-3xl font-bold text-slate-900 mt-2">
                    {loadingSpecialists ? "..." : specialistsCount}
                  </h3>
                </div>
                <div className="w-12 h-12 rounded-full bg-purple-100 flex items-center justify-center">
                  <Users className="h-6 w-6 text-purple-600" />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Search and Filter */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg
                className="h-5 w-5 text-gray-400"
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z"
                  clipRule="evenodd"
                />
              </svg>
            </div>
            <input
              type="text"
              className="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              placeholder="Rechercher par numéro de cas, patient, description"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
          <div className="w-full md:w-64">
            <select
              className="block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Cases List */}
        <Card data-testid="cases-list">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Mes cas assignés</CardTitle>
                <CardDescription>
                  Liste de tous vos cas en cours et terminés
                </CardDescription>
              </div>
              {isAdmin() && (
                <Button
                  onClick={() => navigate("/cases/new")}
                  data-testid="new-case-button"
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  Nouveau cas
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {loading ? (
              <p className="text-center py-8 text-slate-500">Chargement...</p>
            ) : filteredCases.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-slate-500 mb-4">
                  Aucun cas ne correspond à votre recherche
                </p>
                <Button
                  variant="outline"
                  onClick={() => {
                    setSearchTerm("");
                    setStatusFilter("Tous les statuts");
                  }}
                >
                  Réinitialiser les filtres
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {filteredCases.map((caseItem) => (
                  <div
                    key={caseItem.id}
                    className="p-4 border border-slate-200 rounded-lg hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
                    onClick={() => navigate(`/cases/${caseItem.id}`)}
                    data-testid={`case-item-${caseItem.id}`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <h4 className="font-semibold text-slate-900">
                              {caseItem.id}
                            </h4>
                            <Badge className={getStatusColor(caseItem.status)}>
                              {getStatusLabel(caseItem.status)}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e) => {
                                e.stopPropagation();
                                navigate(`/cases/${caseItem.id}`);
                              }}
                            >
                              Voir
                            </Button>
                            {isAdmin() && (
                              <Button
                                variant="outline"
                                size="sm"
                                className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                                onClick={(e) =>
                                  handleDeleteCase(caseItem.id, e)
                                }
                              >
                                Supprimer
                              </Button>
                            )}
                          </div>
                        </div>
                        <p className="text-sm text-slate-600 mb-1">
                          {caseItem.title}
                        </p>
                        <p className="text-xs text-slate-400">
                          Patient: {caseItem.patient_id} • Créé le{" "}
                          {new Date(caseItem.created_at).toLocaleDateString(
                            "fr-FR",
                          )}
                        </p>
                        {caseItem.assigned_specialists &&
                          caseItem.assigned_specialists.length > 0 && (
                            <p className="text-xs text-slate-400 mt-1">
                              Spécialistes:{" "}
                              {caseItem.assigned_specialists.join(", ")}
                            </p>
                          )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
};

export default Dashboard;
