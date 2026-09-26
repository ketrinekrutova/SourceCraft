import { isActive, STAGE_LABELS, type JobInfo } from "../api/types";
import { formatDateTime } from "../utils/formatDate";
import styles from "./JobStatus.module.css";

// Статус последней задачи анализа: идёт / в очереди / упала («анализ не обновлён» - при этом
// на странице остаётся предыдущий успешный результат).
export function JobStatus({ job, hasResult }: { job: JobInfo | null; hasResult: boolean }) {
  if (!job) return null;
  if (isActive(job.status)) {
    const label = job.status === "PENDING" ? "Анализ в очереди" : STAGE_LABELS[job.stage ?? ""] ?? "Идёт анализ";
    return (
      <div className={styles.banner}>
        <div className={styles.row}>
          <span className={styles.spinner} />
          <span>{label}…</span>
          <span className={styles.percent}>{Math.round((job.progress ?? 0) * 100)}%</span>
        </div>
        <div className={styles.track}>
          <div className={styles.fill} style={{ width: `${Math.max(4, (job.progress ?? 0) * 100)}%` }} />
        </div>
      </div>
    );
  }
  if (job.status === "FAILED") {
    return (
      <div className={`${styles.banner} ${styles.failed}`}>
        <strong>{hasResult ? "Анализ не обновлён" : "Анализ не удался"}</strong>
        {job.finished_at && <> · {formatDateTime(job.finished_at)}</>}
        {job.error?.message && <div className={styles.error}>{job.error.message}</div>}
        {hasResult && <div className={styles.error}>Показан результат последнего успешного анализа.</div>}
      </div>
    );
  }
  if (job.status === "PARTIAL" && job.error?.message) {
    return (
      <div className={`${styles.banner} ${styles.partial}`}>
        Анализ завершён частично: {job.error.message}
      </div>
    );
  }
  return null;
}
