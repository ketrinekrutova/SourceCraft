import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAnalyzeByUrl, useMyRepositories } from "../api/hooks";
import { useAuth } from "../auth/AuthContext";
import { FolderTabs } from "../components/FolderTabs";
import { scoreColorSoft } from "../utils/scoreColor";
import styles from "./MyRepositoriesPage.module.css";

export function MyRepositoriesPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const { data, isLoading } = useMyRepositories(isAuthenticated);
  const analyzeByUrl = useAnalyzeByUrl();
  const [repoUrl, setRepoUrl] = useState("");

  const handleAnalyzeUrl = () => {
    if (!repoUrl.trim()) return;
    analyzeByUrl.mutate(repoUrl.trim(), {
      onSuccess: (job) => {
        navigate(`/repositories/${job.repository_id}`, { state: { own: true } });
      },
    });
  };

  return (
    <FolderTabs
      tabs={[
        { to: "/", label: "Рейтинг открытых репозиториев" },
        { to: "/my-repositories", label: "Мои репозитории" },
      ]}
    >
      <>
        {!isAuthenticated && (
          <div className={styles.promptBox}>
            <div className={styles.promptText}>Чтобы увидеть свои репозитории, войдите через Я ID</div>
            <button className={styles.loginButton} onClick={() => login()}>
              Войти в Я ID
            </button>
          </div>
        )}

        {isAuthenticated && (
          <div className={styles.urlForm}>
            <input
              className={styles.urlInput}
              type="text"
              placeholder="Ссылка на свой репозиторий в SourceCraft"
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
            />
            <button className={styles.analyzeButton} onClick={handleAnalyzeUrl} disabled={analyzeByUrl.isPending}>
              {analyzeByUrl.isPending ? "Идёт анализ..." : "Анализировать"}
            </button>
          </div>
        )}

        {isAuthenticated && isLoading && <div className={styles.promptBox}>Загрузка...</div>}

        {isAuthenticated && data && (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Проект</th>
                <th>Health Score</th>
                <th>Лайки</th>
                <th>Язык</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.items.map((repo) => (
                <tr key={repo.id}>
                  <td>
                    {repo.name}
                    {repo.private && <span className={styles.privateBadge}>Приватный</span>}
                  </td>
                  <td>
                    {repo.health_score === null ? (
                      "—"
                    ) : (
                      <span style={{ background: scoreColorSoft(repo.health_score), padding: "6px 14px", borderRadius: 12, fontWeight: 700 }}>
                        {repo.health_score}
                      </span>
                    )}
                  </td>
                  <td>{repo.likes}</td>
                  <td>{repo.language ?? "—"}</td>
                  <td>
                    <button
                      className={styles.analyzeButton}
                      onClick={() => navigate(`/repositories/${repo.id}`, { state: { own: true } })}
                    >
                      {repo.health_score === null ? "Анализировать" : "Открыть"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </>
    </FolderTabs>
  );
}
