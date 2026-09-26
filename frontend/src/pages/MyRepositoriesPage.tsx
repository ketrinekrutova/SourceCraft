import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAnalyzeByUrl, useDeleteToken, useMyRepositories, useSaveOrgs, useSaveToken } from "../api/hooks";
import { useAuth } from "../auth/AuthContext";
import { FolderTabs } from "../components/FolderTabs";
import { PillButton } from "../components/PillButton";
import { formatDateTime } from "../utils/formatDate";
import { scoreColorSoft } from "../utils/scoreColor";
import styles from "./MyRepositoriesPage.module.css";

const AUTH_ERRORS: Record<string, string> = {
  denied: "Вход через Я ID отменён",
  state: "Сессия входа устарела, попробуйте ещё раз",
  token: "Я ID не выдал токен - проверьте настройки OAuth-приложения",
  profile: "Не удалось получить профиль Я ID",
};

export function MyRepositoriesPage() {
  const { isAuthenticated, isLoading: authLoading, user, login, canLogin } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const hasToken = Boolean(user?.has_token);
  const repos = useMyRepositories(isAuthenticated && hasToken);
  const analyze = useAnalyzeByUrl("personal");
  const saveToken = useSaveToken();
  const removeToken = useDeleteToken();
  const saveOrgs = useSaveOrgs();

  const [token, setToken] = useState("");
  // null - поле не редактировалось, показываем сохранённые организации.
  const [orgsDraft, setOrgsDraft] = useState<string | null>(null);
  const orgs = orgsDraft ?? (user?.orgs ?? []).join(", ");
  const [repoUrl, setRepoUrl] = useState("");
  const [pendingId, setPendingId] = useState<string | null>(null);

  const authError = params.get("auth_error");

  const runAnalysis = (ref: string, key: string) => {
    setPendingId(key);
    analyze.mutate(ref, {
      onSuccess: (job) => navigate(`/repositories/${encodeURIComponent(job.repository_id)}?scope=personal`),
      onSettled: () => setPendingId(null),
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
        {authError && <div className={styles.errorBox}>{AUTH_ERRORS[authError] ?? "Ошибка входа"}</div>}

        {!authLoading && !isAuthenticated && (
          <div className={styles.promptBox}>
            <div className={styles.promptText}>
              Войдите через Я ID, чтобы проанализировать свои репозитории, в том числе приватные. Результаты личного
              анализа видите только вы и никогда не попадают в публичный рейтинг.
            </div>
            <PillButton onClick={() => login()} disabled={!canLogin}>
              Войти в Я ID
            </PillButton>
            {!canLogin && <div className={styles.hint}>Вход через Я ID не настроен на сервере</div>}
          </div>
        )}

        {isAuthenticated && (
          <div className={styles.panel}>
            <div className={styles.panelTitle}>Доступ к SourceCraft</div>
            {hasToken ? (
              <div className={styles.tokenRow}>
                <span>
                  PAT подключён{user?.sourcecraft_username ? ` · аккаунт SourceCraft @${user.sourcecraft_username}` : ""}
                </span>
                <PillButton onClick={() => removeToken.mutate()} disabled={removeToken.isPending}>
                  Отключить токен
                </PillButton>
              </div>
            ) : (
              <>
                <div className={styles.hint}>
                  Я ID подтверждает вашу личность, а доступ к данным SourceCraft (приватные репозитории, CI, issues, AppSec)
                  даёт персональный токен (PAT). Создайте его в настройках профиля SourceCraft. Токен проверяется запросом к
                  SourceCraft, хранится только в зашифрованном виде и используется лишь для ваших анализов.
                </div>
                <div className={styles.urlForm}>
                  <input
                    className={styles.urlInput}
                    type="password"
                    autoComplete="off"
                    placeholder="Personal access token SourceCraft"
                    value={token}
                    onChange={(e) => setToken(e.target.value)}
                  />
                  <PillButton
                    disabled={!token.trim() || saveToken.isPending}
                    onClick={() => saveToken.mutate(token.trim(), { onSuccess: () => setToken("") })}
                  >
                    {saveToken.isPending ? "Проверка..." : "Сохранить токен"}
                  </PillButton>
                </div>
                {saveToken.error && <div className={styles.errorText}>{(saveToken.error as Error).message}</div>}
              </>
            )}
          </div>
        )}

        {isAuthenticated && hasToken && (
          <>
            <div className={styles.panel}>
              <div className={styles.panelTitle}>Организации</div>
              <div className={styles.hint}>
                Репозитории вашего личного пространства показываются автоматически. Добавьте slug организаций, в которых вы
                работаете, - через запятую.
              </div>
              <div className={styles.urlForm}>
                <input
                  className={styles.urlInput}
                  placeholder="например: my-team, my-company"
                  value={orgs}
                  onChange={(e) => setOrgsDraft(e.target.value)}
                />
                <PillButton
                  disabled={saveOrgs.isPending}
                  onClick={() =>
                    saveOrgs.mutate(orgs.split(",").map((o) => o.trim()).filter(Boolean), {
                      onSuccess: () => setOrgsDraft(null),
                    })
                  }
                >
                  Сохранить
                </PillButton>
              </div>
              {saveOrgs.error && <div className={styles.errorText}>{(saveOrgs.error as Error).message}</div>}
            </div>

            <div className={styles.urlForm}>
              <input
                className={styles.urlInput}
                type="text"
                placeholder="Любой доступный вам репозиторий: https://sourcecraft.dev/org/repo"
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && repoUrl.trim() && runAnalysis(repoUrl.trim(), "url")}
              />
              <PillButton
                onClick={() => repoUrl.trim() && runAnalysis(repoUrl.trim(), "url")}
                disabled={analyze.isPending}
              >
                {pendingId === "url" ? "Запуск..." : "Анализировать"}
              </PillButton>
            </div>
            {analyze.error && <div className={styles.errorText}>{(analyze.error as Error).message}</div>}

            {repos.isLoading && <div className={styles.promptBox}>Загрузка репозиториев...</div>}
            {repos.error && <div className={styles.errorBox}>{(repos.error as Error).message}</div>}
            {repos.data && repos.data.errors.length > 0 && (
              <div className={styles.hint}>Не удалось прочитать: {repos.data.errors.join("; ")}</div>
            )}
            {repos.data && repos.data.items.length === 0 && (
              <div className={styles.promptBox}>
                В {repos.data.orgs_checked.join(", ") || "указанных организациях"} репозиториев не найдено. Добавьте
                организации или вставьте ссылку на репозиторий выше.
              </div>
            )}

            {repos.data && repos.data.items.length > 0 && (
              <table className={styles.table}>
                <thead>
                  <tr>
                    <th>Проект</th>
                    <th>Health Score</th>
                    <th>Язык</th>
                    <th>Последний анализ</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {repos.data.items.map((repo) => (
                    <tr key={repo.id}>
                      <td>
                        {repo.full_name}
                        {repo.private && <span className={styles.privateBadge}>{repo.visibility === "internal" ? "Внутренний" : "Приватный"}</span>}
                      </td>
                      <td>
                        {repo.health_score === null ? (
                          "-"
                        ) : (
                          <span className={styles.score} style={{ background: scoreColorSoft(repo.health_score) }}>
                            {repo.health_score}
                          </span>
                        )}
                      </td>
                      <td>{repo.language ?? "-"}</td>
                      <td>{formatDateTime(repo.last_analyzed_at)}</td>
                      <td className={styles.rowActions}>
                        {repo.analyzed && (
                          <PillButton
                            onClick={() => navigate(`/repositories/${encodeURIComponent(repo.id)}?scope=personal`)}
                          >
                            Открыть
                          </PillButton>
                        )}
                        <PillButton
                          disabled={analyze.isPending}
                          onClick={() => runAnalysis(repo.full_name, repo.id)}
                        >
                          {pendingId === repo.id ? "Запуск..." : repo.analyzed ? "Повторить ↻" : "Анализировать"}
                        </PillButton>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </>
        )}
      </>
    </FolderTabs>
  );
}
