import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRating } from "../api/hooks";
import { useAuth } from "../auth/AuthContext";
import { Dropdown } from "../components/Dropdown";
import { FolderTab } from "../components/FolderTab";
import { formatRelativeDays } from "../utils/formatDate";
import { scoreColorSoft } from "../utils/scoreColor";
import styles from "./RatingPage.module.css";

const LANGUAGES = ["Все языки", "Python", "React", "C++", "Go", "Java", "Паскаль"].map((l) => ({ value: l, label: l }));
const SORT_OPTIONS: { value: "health_score" | "likes" | "last_activity"; label: string }[] = [
  { value: "health_score", label: "Score" },
  { value: "likes", label: "Лайки" },
  { value: "last_activity", label: "Активность" },
];

export function RatingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [language, setLanguage] = useState("Все языки");
  const [sortBy, setSortBy] = useState<"health_score" | "likes" | "last_activity">("health_score");

  const { data, isLoading, isError } = useRating({
    language: language === "Все языки" ? undefined : language,
    sort_by: sortBy,
    order: "desc",
  });

  return (
    <FolderTab
      label="Рейтинг открытых репозиториев"
      extraTabs={isAuthenticated ? [{ to: "/my-repositories", label: "Мои репозитории" }] : []}
    >
      <div className={styles.controls}>
        <div className={styles.controlGroup}>
          Фильтр
          <Dropdown value={language} options={LANGUAGES} onChange={setLanguage} />
        </div>
        <div className={styles.controlGroup}>
          Сортировка
          <Dropdown value={sortBy} options={SORT_OPTIONS} onChange={(v) => setSortBy(v as typeof sortBy)} />
        </div>
      </div>

        {isLoading && <div className={styles.empty}>Загрузка...</div>}
        {isError && <div className={styles.empty}>Не удалось загрузить рейтинг</div>}

        {data && data.items.length === 0 && <div className={styles.empty}>Ничего не найдено</div>}

        {data && data.items.length > 0 && (
          <table className={styles.table}>
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
              {data.items.map((repo, index) => (
                <tr key={repo.id} className={styles.row} onClick={() => navigate(`/repositories/${repo.id}`)} style={{ cursor: "pointer" }}>
                  <td>
                    <span className={styles.rank}>
                      {index + 1} <span>›</span>
                    </span>
                  </td>
                  <td>
                    <span className={styles.projectLink}>{repo.name}</span>
                  </td>
                  <td>
                    <span className={styles.scoreCell} style={{ background: scoreColorSoft(repo.health_score), padding: "6px 14px" }}>
                      {repo.health_score ?? "—"}
                    </span>
                  </td>
                  <td>{repo.likes.toLocaleString("ru-RU")}</td>
                  <td>{repo.language ?? "—"}</td>
                  <td>{formatRelativeDays(repo.last_activity_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
    </FolderTab>
  );
}
