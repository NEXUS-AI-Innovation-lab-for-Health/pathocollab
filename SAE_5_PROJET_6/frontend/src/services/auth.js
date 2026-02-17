import axios from "axios";

const API_URL = process.env.REACT_APP_BACKEND_URL || "http://127.0.0.1:8000";

export const getCurrentUser = async () => {
  try {
    const token = localStorage.getItem("access_token");
    if (!token) return null;

    // Ici, vous devriez normalement faire un appel API pour récupérer les infos de l'utilisateur
    // Pour l'instant, on va simplement décoder le token pour récupérer l'email
    const payload = JSON.parse(atob(token.split(".")[1]));

    return {
      email: payload.sub,
      // On extrait la première lettre de l'email comme initiale
      initial: payload.sub ? payload.sub.charAt(0).toUpperCase() : "U",
      // On utilise l'email comme nom complet pour l'instant
      // Dans une vraie application, vous devriez stocker le nom complet dans le token
      // ou faire un appel API pour récupérer le profil utilisateur
      fullName: payload.sub.split("@")[0],
    };
  } catch (error) {
    console.error("Error getting current user:", error);
    return null;
  }
};

export const isAuthenticated = () => {
  return !!localStorage.getItem("access_token");
};

export const logout = () => {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
};
