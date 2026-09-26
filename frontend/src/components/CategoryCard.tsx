import { useState } from "react";
import type { CategoryKey, Metric } from "../api/types";
import { CATEGORY_LABELS } from "../api/types";
import { scoreColor } from "../utils/scoreColor";
import styles from "./CategoryCard.module.css";
import { EvidenceList } from "./EvidenceList";

function formatPoints(points: number | null, max: number): string {
  if (points === null) return "не измерено";
  if (max === 0) return points === 0 ? "0" : points.toFixed(0);
  return `${points.toFixed(1).replace(".0", "")} / ${max}`;
}

export function CategoryCard({ category, metric }: { category: CategoryKey; metric: Metric }) {
  const [open, setOpen] = useState(false);
  const noData = metric.status === "NO_DATA";

  return (
    <div className={`${styles.card} ${noData ? styles.cardNoData : ""}`}>
      <button type="button" className={styles.header} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <span className={styles.title}>{CATEGORY_LABELS[category]}</span>
        <span className={styles.weight}>
          вес {Math.round(metric.base_weight * 100)}%{!noData && metric.weight !== metric.base_weight && ` → ${Math.round(metric.weight * 100)}%`}
        </span>
      </button>

      {noData ? (
        <div className={styles.noData}>
          <span className={styles.noDataBadge}>Нет данных</span>
          <div className={styles.noDataReason}>{metric.summary}</div>
          <div className={styles.noDataHint}>Категория исключена из расчёта и не снижает Score</div>
        </div>
      ) : (
        <>
          <div className={styles.barRow}>
            <div className={styles.barTrack}>
              <div className={styles.barFill} style={{ width: `${metric.score ?? 0}%`, background: scoreColor(metric.score) }} />
            </div>
            <div className={styles.barValue}>{metric.score}</div>
          </div>
          {metric.summary && <div className={styles.summary}>{metric.summary}</div>}
        </>
      )}

      {!noData && (
        <button type="button" className={styles.toggle} onClick={() => setOpen((v) => !v)}>
          {open ? "Скрыть расчёт" : "Как посчитано →"}
        </button>
      )}

      {open && !noData && (
        <div className={styles.details}>
          {metric.components.length > 0 && (
            <table className={styles.components}>
              <tbody>
                {metric.components.map((c) => (
                  <tr key={c.label}>
                    <td>{c.label}</td>
                    <td className={styles.componentValue}>{c.value}</td>
                    <td className={styles.componentPoints}>{formatPoints(c.points, c.max_points)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className={styles.contribution}>Вклад в итоговый Score: {metric.contribution.toFixed(1)}</div>
          {metric.evidence.length > 0 && (
            <>
              <div className={styles.factsTitle}>Подтверждающие факты</div>
              <EvidenceList items={metric.evidence} limit={6} />
            </>
          )}
        </div>
      )}
    </div>
  );
}
