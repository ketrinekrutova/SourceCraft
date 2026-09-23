import type { Recommendation } from "../api/types";
import styles from "./RecommendationsList.module.css";

const PRIORITY_CLASS: Record<Recommendation["priority"], string> = {
  HIGH: styles.priorityHigh,
  MEDIUM: styles.priorityMedium,
  LOW: styles.priorityLow,
};

const PRIORITY_LABEL: Record<Recommendation["priority"], string> = {
  HIGH: "Высокий",
  MEDIUM: "Средний",
  LOW: "Низкий",
};

export function RecommendationsList({ items }: { items: Recommendation[] }) {
  if (items.length === 0) {
    return <div className={styles.empty}>Критичных рекомендаций нет</div>;
  }

  return (
    <div className={styles.list}>
      {items.map((rec) => (
        <div key={rec.id} className={styles.item}>
          <span className={`${styles.priority} ${PRIORITY_CLASS[rec.priority]}`}>{PRIORITY_LABEL[rec.priority]}</span>
          <div className={styles.body}>
            <div className={styles.itemTitle}>{rec.title}</div>
            <div className={styles.itemDescription}>{rec.description}</div>
            {rec.impact && <div className={styles.itemImpact}>{rec.impact}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
