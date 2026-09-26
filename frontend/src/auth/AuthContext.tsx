import { useQuery, useQueryClient } from "@tanstack/react-query";
import { createContext, useContext, type ReactNode } from "react";
import { devLogin, fetchAuth, logout as apiLogout, yandexLoginUrl } from "../api/client";
import type { Me } from "../api/types";

// Сессия - httpOnly cookie, выставляемая бэкендом после OAuth-входа через Я ID. Фронтенд только
// спрашивает /auth/me и отправляет пользователя на /auth/yandex/login.

interface AuthValue {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: Me | null;
  canLogin: boolean;
  login: () => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["auth"], queryFn: fetchAuth, staleTime: 30_000 });

  const login = async () => {
    if (data?.yandex_id_configured) {
      window.location.href = yandexLoginUrl();
      return;
    }
    if (data?.dev_login_enabled) {
      await devLogin();
      await queryClient.invalidateQueries({ queryKey: ["auth"] });
      return;
    }
    window.alert("Вход через Я ID не настроен на сервере (YA_ID_CLIENT_ID).");
  };

  const logout = async () => {
    await apiLogout();
    queryClient.removeQueries({ queryKey: ["my-repositories"] });
    await queryClient.invalidateQueries({ queryKey: ["auth"] });
  };

  const value: AuthValue = {
    isLoading,
    isAuthenticated: Boolean(data?.authenticated),
    user: data?.user ?? null,
    canLogin: Boolean(data?.yandex_id_configured || data?.dev_login_enabled),
    login,
    logout,
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
