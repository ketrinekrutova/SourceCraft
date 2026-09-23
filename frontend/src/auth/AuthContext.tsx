import { createContext, useContext, useState, type ReactNode } from "react";
import { mockLogin } from "../api/client";

// Мок на время, пока OAuth-приложение Я ID не зарегистрировано (CHECK.md A2) и авторизация
// не в контракте бэкенда (openapi.yaml помечает User-ручки как v0.3). Когда появится реальный
// OAuth — меняется только login() (редирект вместо mockLogin()), компоненты не трогаем.

interface AuthState {
  isAuthenticated: boolean;
  displayName: string | null;
  login: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [displayName, setDisplayName] = useState<string | null>(null);

  const login = async () => {
    const res = await mockLogin();
    setDisplayName(res.display_name);
  };
  const logout = () => setDisplayName(null);

  return (
    <AuthContext.Provider value={{ isAuthenticated: displayName !== null, displayName, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
