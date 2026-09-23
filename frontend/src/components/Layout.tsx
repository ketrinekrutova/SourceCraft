import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import styles from "./Layout.module.css";

export function Layout({ children }: { children: ReactNode }) {
  const { isAuthenticated, login } = useAuth();

  return (
    <div className={styles.page}>
      <div className={styles.frame}>
        <header className={styles.header}>
          <Link to="/" className={styles.logo}>
            SourceCraft <span className={styles.logoDivider}>/</span> Repo Health Score
          </Link>
          <button className={styles.authButton} onClick={() => !isAuthenticated && login()}>
            <span className={styles.authButtonInner}>{isAuthenticated ? "Вошёл в Я ID" : "Войти в Я ID"}</span>
          </button>
        </header>
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  );
}
