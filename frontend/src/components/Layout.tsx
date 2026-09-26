import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import styles from "./Layout.module.css";

export function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, user, login, logout } = useAuth();

  return (
    <div className={styles.page}>
      <div className={styles.frame}>
        <header className={styles.header}>
          <Link to="/" className={styles.logo}>
            SourceCraft <span className={styles.logoDivider}>/</span> Repo Health Score
          </Link>
          <button
            className={styles.authButton}
            onClick={() => (isAuthenticated ? logout() : login())}
            title={isAuthenticated ? "Выйти" : "Войти через Я ID"}
          >
            <span className={styles.authButtonInner}>
              {isAuthenticated ? `${user?.display_name ?? user?.login ?? "Я ID"} · выйти` : "Войти в Я ID"}
            </span>
          </button>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
