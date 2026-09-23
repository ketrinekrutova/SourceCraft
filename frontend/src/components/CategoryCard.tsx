import type { CategoryKey, Metric } from "../api/types";
import { CATEGORY_LABELS } from "../api/types";
import { scoreColor } from "../utils/scoreColor";
import styles from "./CategoryCard.module.css";

export function CategoryCard({ category, metric }: { category: CategoryKey; metric: Metric }) {
  return (
    <div className={styles.card}>
      <div className={styles.title}>{CATEGORY_LABELS[category]}</div>
      {metric.status === "NO_DATA" ? (
        <div className={styles.noData}>Нет данных</div>
      ) : (
        <>
          <div className={styles.barRow}>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{ width: `${metric.score ?? 0}%`, background: scoreColor(metric.score) }}
              />
            </div>
            <div className={styles.barValue}>{metric.score}</div>
          </div>
          {metric.summary && <div className={styles.summary}>{metric.summary}</div>}
        </>
      )}
    </div>
  );
}
