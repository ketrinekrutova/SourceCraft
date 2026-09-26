import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { reportDownloadUrl } from "../api/client";
import { useAnalyzeByUrl, useReanalyze, useRepository } from "../api/hooks";
import { CATEGORY_LABELS, CATEGORY_ORDER, isActive, type Scope } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CategoryCard } from "../components/CategoryCard";
import { FolderTabs } from "../components/FolderTabs";
import { GlassPanel } from "../components/GlassPanel";
import panelStyles from "../components/GlassPanel.module.css";
import { JobStatus } from "../components/JobStatus";
import { RecommendationsList } from "../components/RecommendationsList";
import { ScoreDonut } from "../components/ScoreDonut";
import { formatDateTime } from "../utils/formatDate";
import styles from "./AnalysisPage.module.css";

export function AnalysisPage() {
  const { id = "" } = useParams<{ id: string }>();
  const [params] = useSearchParams();
  const scope: Scope = params.get("scope") === "personal" ? "personal" : "public";
  const navigate = useNavigate();
  const { isAuthenticated, user } = useAuth();
  const { data: repo, isLoading, error } = useRepository(id, scope);
  const reanalyze = useReanalyze(id, scope);
  const personalAnalyze = useAnalyzeByUrl("personal");

  const jobActive = isActive(repo?.latest_job?.status) || reanalyze.isPending;
  const tabs = [
    { to: "/", label: "Рейтинг открытых репозиториев" },
    ...(isAuthenticated ? [{ to: "/my-repositories", label: "Мои репозитории" }] : []),
    { to: `/repositories/${encodeURIComponent(id)}`, label: `Анализ репозитория / ${repo?.name ?? "..."}`, end: true },
  ];
  const delta =
    repo?.previous && repo.previous.health_score !== null && repo.health_score !== null
      ? repo.health_score - repo.previous.health_score
      : null;

  const runPersonal = () => {
    if (!repo) return;
    personalAnalyze.mutate(repo.full_name, {
      onSuccess: (job) => navigate(`/repositories/${encodeURIComponent(job.repository_id)}?scope=personal`),
    });
  };

  return (
    <FolderTabs tabs={tabs}>
      {isLoading && <div className={styles.message}>Загрузка...</div>}
      {error && <div className={styles.message}>{(error as Error).message}</div>}

      {repo && (
        <>
          <div className={styles.scopeBar}>
            <span className={`${styles.scopeBadge} ${scope === "personal" ? styles.scopePersonal : ""}`}>
              {scope === "personal" ? "Личный анализ по вашему PAT · виден только вам" : "Публичный анализ · открытые данные"}
            </span>
            {scope === "public" && isAuthenticated && user?.has_token && (
              <button className={styles.linkButton} onClick={runPersonal} disabled={personalAnalyze.isPending}>
                Полный анализ с AppSec по моему PAT →
              </button>
            )}
            {scope === "personal" && repo.visibility === "public" && (
              <button className={styles.linkButton} onClick={() => navigate(`/repositories/${encodeURIComponent(id)}`)}>
                Публичная версия →
              </button>
            )}
            {personalAnalyze.error && <span className={styles.errorText}>{(personalAnalyze.error as Error).message}</span>}
          </div>

          <JobStatus job={repo.latest_job} hasResult={repo.metrics !== null} />

          <div className={styles.topRow}>
            <GlassPanel>
              <div className={styles.metaLines}>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Репозиторий</div>
                  <span className={styles.repoName}>{repo.full_name}</span>
                  {repo.visibility !== "public" && <span className={styles.privateBadge}>Приватный</span>}
                </div>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Ссылка в SourceCraft</div>
                  <a href={repo.url} target="_blank" rel="noreferrer">
                    {repo.url}
                  </a>
                </div>
                <div className={styles.metaRow}>
                  <div className={styles.metaLine}>
                    <div className={styles.metaLabel}>Основной язык</div>
                    {repo.language ?? "-"}
                  </div>
                  <div className={styles.metaLine}>
                    <div className={styles.metaLabel}>Лайки</div>
                    {repo.likes.toLocaleString("ru-RU")}
                  </div>
                  <div className={styles.metaLine}>
                    <div className={styles.metaLabel}>Последний анализ</div>
                    {formatDateTime(repo.last_analyzed_at)}
                  </div>
                </div>
              </div>
              <div className={styles.actions}>
                <button className={styles.actionButton} onClick={() => reanalyze.mutate()} disabled={jobActive}>
                  {jobActive ? "Идёт анализ..." : repo.metrics ? "Повторный анализ ↻" : "Запустить анализ ↻"}
                </button>
                {repo.metrics && (
                  <>
                    <a className={styles.actionButton} href={reportDownloadUrl(repo.id, scope, "pdf")} download>
                      Отчёт PDF ⤓
                    </a>
                    <a className={styles.actionButton} href={reportDownloadUrl(repo.id, scope, "markdown")} download>
                      Отчёт Markdown ⤓
                    </a>
                  </>
                )}
              </div>
              {reanalyze.error && <div className={styles.errorText}>{(reanalyze.error as Error).message}</div>}
            </GlassPanel>

            <GlassPanel className={styles.scorePanel}>
              <ScoreDonut score={repo.health_score} />
              <div>
                <div className={styles.verdict}>{repo.verdict}</div>
                {delta !== null && delta !== 0 && (
                  <div className={delta > 0 ? styles.deltaUp : styles.deltaDown}>
                    {delta > 0 ? "▲" : "▼"} {Math.abs(delta)} к прошлому анализу ({formatDateTime(repo.previous?.analyzed_at ?? null)})
                  </div>
                )}
                {delta === 0 && <div className={styles.deltaSame}>Без изменений к прошлому анализу</div>}
                {repo.metrics && (
                  <div className={styles.coverage} title="Доля исходного веса методики, по которой есть данные">
                    Полнота данных: {Math.round(repo.coverage * 100)}%
                  </div>
                )}
              </div>
            </GlassPanel>
          </div>

          {repo.metrics && (
            <>
              <div className={styles.grid}>
                {CATEGORY_ORDER.map((key) => (
                  <CategoryCard key={key} category={key} metric={repo.metrics![key]} />
                ))}
              </div>

              {(repo.strengths.length > 0 || repo.weaknesses.length > 0) && (
                <div className={styles.twoCols}>
                  <GlassPanel className={panelStyles.dark}>
                    <div className={styles.sectionTitle}>Сильные стороны</div>
                    <div className={styles.sectionHint}>Категории с оценкой 80 и выше - то, что в проекте уже хорошо</div>
                    {repo.strengths.length ? (
                      <ul className={styles.bullets}>
                        {repo.strengths.map((s) => (
                          <li key={s}>{s}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className={styles.muted}>Категорий с оценкой 80+ нет</div>
                    )}
                  </GlassPanel>
                  <GlassPanel className={panelStyles.dark}>
                    <div className={styles.sectionTitle}>Слабые стороны</div>
                    <div className={styles.sectionHint}>Категории с оценкой ниже 60 - что тянет Score вниз; как исправить - в рекомендациях</div>
                    {repo.weaknesses.length ? (
                      <ul className={styles.bullets}>
                        {repo.weaknesses.map((w) => (
                          <li key={w}>{w}</li>
                        ))}
                      </ul>
                    ) : (
                      <div className={styles.muted}>Категорий с оценкой ниже 60 нет</div>
                    )}
                  </GlassPanel>
                </div>
              )}

              <GlassPanel className={`${panelStyles.dark} ${styles.section}`}>
                <div className={styles.sectionTitle}>Рекомендации</div>
                <RecommendationsList items={repo.recommendations} />
              </GlassPanel>

              <GlassPanel className={styles.section}>
                <div className={styles.sectionTitle}>Как рассчитан Score</div>
                <p className={styles.formula}>
                  Repo Health Score = Σ (оценка категории × вес). Категории со статусом «Нет данных» исключаются, а их вес
                  пропорционально распределяется между остальными - отсутствие данных не снижает оценку.
                </p>
                <table className={styles.explainTable}>
                  <thead>
                    <tr>
                      <th>Категория</th>
                      <th>Оценка</th>
                      <th>Вес методики</th>
                      <th>Фактический вес</th>
                      <th>Вклад в Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {CATEGORY_ORDER.map((key) => {
                      const m = repo.metrics![key];
                      const noData = m.status === "NO_DATA";
                      return (
                        <tr key={key}>
                          <td>{CATEGORY_LABELS[key]}</td>
                          <td>{noData ? <span className={styles.noDataText}>Нет данных</span> : m.score}</td>
                          <td>{Math.round(m.base_weight * 100)}%</td>
                          <td>{noData ? "—" : `${Math.round(m.weight * 100)}%`}</td>
                          <td>{noData ? "—" : m.contribution.toFixed(1)}</td>
                        </tr>
                      );
                    })}
                    <tr className={styles.totalRow}>
                      <td>Итого</td>
                      <td colSpan={3} />
                      <td>{repo.health_score ?? "—"}</td>
                    </tr>
                  </tbody>
                </table>
                {repo.methodology_version && <div className={styles.muted}>Методика v{repo.methodology_version}</div>}
              </GlassPanel>
            </>
          )}

          {!repo.metrics && !jobActive && (
            <GlassPanel>
              <div className={styles.message}>Этот репозиторий ещё не анализировался. Нажмите «Запустить анализ».</div>
            </GlassPanel>
          )}
        </>
      )}
    </FolderTabs>
  );
}
