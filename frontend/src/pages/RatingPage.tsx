import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAnalyzeByUrl, useLanguages, useRating } from "../api/hooks";
import type { AnalysisStatus } from "../api/types";
import { useAuth } from "../auth/AuthContext";
import { Dropdown } from "../components/Dropdown";
import { FolderTab } from "../components/FolderTab";
import { PillButton } from "../components/PillButton";
import { formatDateTime, formatRelativeDays } from "../utils/formatDate";
import { scoreColorSoft } from "../utils/scoreColor";
import styles from "./RatingPage.module.css";

type SortKey = "health_score" | "likes" | "last_activity";
const ALL = "__all__";
const PAGE_SIZE = 20;
const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "health_score", label: "Score" },
  { value: "likes", label: "Лайки" },
  { value: "last_activity", label: "Активность" },
];
const ORDER_OPTIONS = [
  { value: "desc", label: "По убыванию" },
  { value: "asc", label: "По возрастанию" },
];

function statusHint(status: AnalysisStatus, score: number | null): string | null {
  if (status === "FAILED") return score === null ? "анализ не удался" : "не обновлён";
  if (status === "PARTIAL") return "частично";
  if (score === null) return status === "IN_PROGRESS" ? "анализ идёт" : "ожидает анализа";
  return null;
}

export function RatingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [language, setLanguage] = useState(ALL);
  const [sortBy, setSortBy] = useState<SortKey>("health_score");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState(1);
  const [repoUrl, setRepoUrl] = useState("");
  const analyze = useAnalyzeByUrl("public");
  const languages = useLanguages();

  const { data, isLoading, isError, isFetching } = useRating({
    language: language === ALL ? undefined : language,
    sort_by: sortBy,
    order,
    page,
    limit: PAGE_SIZE,
  });
  const totalPages = data ? Math.max(1, Math.ceil(data.total / PAGE_SIZE)) : 1;
  const languageOptions = [{ value: ALL, label: "Все языки" }, ...(languages.data ?? []).map((l) => ({ value: l, label: l }))];

  const submitUrl = () => {
    if (!repoUrl.trim()) return;
    analyze.mutate(repoUrl.trim(), {
      onSuccess: (job) => navigate(`/repositories/${encodeURIComponent(job.repository_id)}`),
    });
  };

  return (
    <FolderTab
      label="Рейтинг открытых репозиториев"
      extraTabs={isAuthenticated ? [{ to: "/my-repositories", label: "Мои репозитории" }] : []}
    >
      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          Язык
          <Dropdown
            value={language}
            options={languageOptions}
            onChange={(v) => {
              setLanguage(v);
              setPage(1);
            }}
          />
        </div>
        <div className={styles.controlGroup}>
          Сортировка
          <Dropdown
            value={sortBy}
            options={SORT_OPTIONS}
            onChange={(v) => {
              setSortBy(v as SortKey);
              setPage(1);
            }}
          />
          <Dropdown
            value={order}
            options={ORDER_OPTIONS}
            onChange={(v) => {
              setOrder(v as "asc" | "desc");
              setPage(1);
            }}
          />
        </div>
      </div>

      <div className={styles.analyzeForm}>
        <input
          className={styles.urlInput}
          placeholder="Проанализировать открытый репозиторий: https://sourcecraft.dev/org/repo"
          value={repoUrl}
          onChange={(e) => setRepoUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submitUrl()}
        />
        <PillButton onClick={submitUrl} disabled={analyze.isPending}>
          {analyze.isPending ? "Запуск..." : "Анализировать"}
        </PillButton>
      </div>
      {analyze.error && <div className={styles.error}>{(analyze.error as Error).message}</div>}

      {data && (
        <div className={styles.summary}>
          В каталоге {data.summary.catalog_total.toLocaleString("ru-RU")} открытых репозиториев, рассчитано{" "}
          {data.summary.analyzed_total.toLocaleString("ru-RU")}. Последний пересчёт: {formatDateTime(data.summary.last_analyzed_at)}.
          Рейтинг строится по Repo Health Score - лайки не влияют на оценку.
        </div>
      )}

      {isLoading && <div className={styles.empty}>Загрузка...</div>}
      {isError && <div className={styles.empty}>Не удалось загрузить рейтинг</div>}
      {data && data.items.length === 0 && <div className={styles.empty}>Ничего не найдено</div>}

      {data && data.items.length > 0 && (
        <table className={`${styles.table} ${isFetching ? styles.fetching : ""}`}>
          <thead>
            <tr>
              <th>#</th>
              <th>Проект</th>
              <th>Health Score</th>
              <th>Лайки</th>
              <th>Язык</th>
              <th>Активность</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((repo, index) => {
              const hint = statusHint(repo.status, repo.health_score);
              return (
                <tr
                  key={repo.id}
                  className={styles.row}
                  onClick={() => navigate(`/repositories/${encodeURIComponent(repo.id)}`)}
                >
                  <td>
                    <span className={styles.rank}>
                      {(page - 1) * PAGE_SIZE + index + 1} <span>›</span>
                    </span>
                  </td>
                  <td>
                    <span className={styles.projectLink}>{repo.name}</span>
                    <div className={styles.org}>
                      {repo.full_name.split("/")[0]} ·{" "}
                      <a href={repo.url} target="_blank" rel="noreferrer" onClick={(e) => e.stopPropagation()}>
                        открыть в SourceCraft ↗
                      </a>
                    </div>
                  </td>
                  <td>
                    <span className={styles.scoreCell} style={{ background: scoreColorSoft(repo.health_score) }}>
                      {repo.health_score ?? "-"}
                    </span>
                    {hint && <div className={styles.statusHint}>{hint}</div>}
                    {repo.coverage !== null && repo.coverage < 1 && repo.health_score !== null && (
                      <div className={styles.statusHint} title="Доля веса методики, по которой есть данные">
                        данные: {Math.round(repo.coverage * 100)}%
                      </div>
                    )}
                  </td>
                  <td>{repo.likes.toLocaleString("ru-RU")}</td>
                  <td>{repo.language ?? "-"}</td>
                  <td>{formatRelativeDays(repo.last_activity_at)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      {data && totalPages > 1 && (
        <div className={styles.pager}>
          <PillButton light disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            ‹ Назад
          </PillButton>
          <span>
            Страница {page} из {totalPages}
          </span>
          <PillButton light disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            Вперёд ›
          </PillButton>
        </div>
      )}
    </FolderTab>
  );
}
