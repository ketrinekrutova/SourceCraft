import { CATEGORY_LABELS, type Recommendation } from "../api/types";
import { EvidenceList } from "./EvidenceList";
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
          <div className={styles.side}>
            <span className={`${styles.priority} ${PRIORITY_CLASS[rec.priority]}`}>{PRIORITY_LABEL[rec.priority]}</span>
            <span className={styles.category}>{CATEGORY_LABELS[rec.category]}</span>
          </div>
          <div className={styles.body}>
            <div className={styles.itemTitle}>{rec.title}</div>
            <dl className={styles.fields}>
              <dt>Почему важно</dt>
              <dd>{rec.why_it_matters}</dd>
              <dt>Что сделать</dt>
              <dd>{rec.action}</dd>
              {rec.facts && (
                <>
                  <dt>Факты</dt>
                  <dd>{rec.facts}</dd>
                </>
              )}
            </dl>
            <EvidenceList items={rec.evidence} limit={5} />
            {rec.impact && <div className={styles.itemImpact}>Эффект: {rec.impact}</div>}
          </div>
        </div>
      ))}
    </div>
  );
}
