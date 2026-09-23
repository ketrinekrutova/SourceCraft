import { useLocation, useParams } from "react-router-dom";
import { reportDownloadUrl } from "../api/client";
import { useReanalyze, useRepository } from "../api/hooks";
import type { CategoryKey } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { CategoryCard } from "../components/CategoryCard";
import { GlassPanel } from "../components/GlassPanel";
import panelStyles from "../components/GlassPanel.module.css";
import { RecommendationsList } from "../components/RecommendationsList";
import { FolderTabs } from "../components/FolderTabs";
import { ScoreDonut } from "../components/ScoreDonut";
import { formatDateTime } from "../utils/formatDate";
import styles from "./AnalysisPage.module.css";

const CATEGORY_ORDER: CategoryKey[] = ["documentation", "ci_cd", "security", "activity", "issues", "code_health"];

export function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const { isAuthenticated } = useAuth();
  const { data: repo, isLoading, isError } = useRepository(id);
  const reanalyze = useReanalyze(id ?? "");

  // "Свой" репозиторий — сюда пришли с "Моих репозиториев" (см. MyRepositoriesPage.tsx,
  // navigate(..., { state: { own: true } })). Security показываем только в этом случае —
  // осознанное правило, не баг: для чужих публичных репозиториев категория скрыта целиком.
  const isOwn = Boolean((location.state as { own?: boolean } | null)?.own);
  const categories = isOwn ? CATEGORY_ORDER : CATEGORY_ORDER.filter((key) => key !== "security");

  // Порядок вкладок фиксированный, не зависит от того, какая активна — раньше "Анализ" всегда
  // становился первым/левым, что было неправильно (ломало порядок при переходах).
  const tabs = [
    { to: "/", label: "Рейтинг открытых репозиториев" },
    ...(isAuthenticated ? [{ to: "/my-repositories", label: "Мои репозитории" }] : []),
    { to: `/repositories/${id}`, label: `Анализ репозитория / ${repo?.name ?? "..."}`, end: true },
  ];

  return (
    <FolderTabs tabs={tabs}>
      {isLoading && <div>Загрузка...</div>}
      {isError && <div>Не удалось загрузить репозиторий</div>}

      {repo && (
        <>
          <div className={styles.topRow}>
            <GlassPanel>
              <div className={styles.metaLines}>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Название репозитория</div>
                  {repo.name}
                </div>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Ссылка на сам репозиторий в SourceCraft</div>
                  <a href={repo.url} target="_blank" rel="noreferrer">
                    {repo.url}
                  </a>
                </div>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Основной язык</div>
                  {repo.language ?? "—"}
                </div>
                <div className={styles.metaLine}>
                  <div className={styles.metaLabel}>Дата последнего анализа (когда пересчитывался score)</div>
                  {formatDateTime(repo.last_analyzed_at)}
                </div>
              </div>
              <div className={styles.actions}>
                <button className={styles.actionButton} onClick={() => reanalyze.mutate()} disabled={reanalyze.isPending}>
                  {reanalyze.isPending ? "Идёт анализ..." : "Повторный анализ ↻"}
                </button>
                <a className={styles.actionButton} href={reportDownloadUrl(repo.id)} download>
                  Скачать отчёт ⤓
                </a>
              </div>
            </GlassPanel>

            <GlassPanel className={styles.scorePanel}>
              <ScoreDonut score={repo.health_score ?? 0} />
              <div className={styles.verdict}>{repo.verdict}</div>
            </GlassPanel>
          </div>

          <div className={styles.grid}>
            {categories.map((key) => (
              <CategoryCard key={key} category={key} metric={repo.metrics[key]} />
            ))}
          </div>

          <GlassPanel className={panelStyles.dark}>
            <div className={styles.sectionTitle}>Рекомендации</div>
            <RecommendationsList items={repo.recommendations} />
          </GlassPanel>
        </>
      )}
    </FolderTabs>
  );
}
