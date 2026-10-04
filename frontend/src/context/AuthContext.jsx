/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  getCurrentUser,
  login as loginRequest,
  register as registerRequest,
  updateCurrentUser,
} from "../services/authService";
import { clearSession } from "../services/api";

const AuthContext = createContext(null);
const USER_KEY = "clipcart_user";

function saveSession(payload) {
  localStorage.setItem("clipcart_access_token", payload.access_token);
  localStorage.setItem("clipcart_refresh_token", payload.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(payload.user));
}

function getSavedUser() {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() =>
    localStorage.getItem("clipcart_access_token") ? getSavedUser() : null,
  );
  const [loading, setLoading] = useState(() =>
    Boolean(localStorage.getItem("clipcart_access_token")),
  );

  useEffect(() => {
    let active = true;
    const token = localStorage.getItem("clipcart_access_token");

    if (!token) {
      return () => {
        active = false;
      };
    }

    getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        if (currentUser?.role !== "CUSTOMER") {
          clearSession();
          setUser(null);
          return;
        }
        setUser(currentUser);
        localStorage.setItem(USER_KEY, JSON.stringify(currentUser));
      })
      .catch(() => {
        if (active) {
          clearSession();
          setUser(null);
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, []);

  async function login(email, password) {
    const data = await loginRequest(email, password);
    if (data?.user?.role !== "CUSTOMER") {
      clearSession();
      throw new Error("This account is not a customer account.");
    }
    saveSession(data);
    setUser(data.user);
    return data.user;
  }

  async function register(payload) {
    return registerRequest(payload);
  }

  async function updateProfile(payload) {
    const nextUser = await updateCurrentUser(payload);
    setUser(nextUser);
    localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
    return nextUser;
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      updateProfile,
      logout,
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
