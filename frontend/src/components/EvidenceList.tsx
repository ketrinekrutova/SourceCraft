import type { Evidence } from "../api/types";
import styles from "./EvidenceList.module.css";

const TYPE_LABELS: Record<Evidence["type"], string> = {
  file: "файл",
  pipeline: "CI",
  vulnerability: "уязвимость",
  commit: "коммит",
  issue: "issue",
  merge_request: "MR",
};

export function EvidenceList({ items, limit = 10 }: { items: Evidence[]; limit?: number }) {
  if (items.length === 0) return null;
  return (
    <ul className={styles.list}>
      {items.slice(0, limit).map((e, i) => (
        <li key={`${e.ref}-${i}`} className={styles.item}>
          <span className={styles.type}>{TYPE_LABELS[e.type]}</span>
          {e.url ? (
            <a href={e.url} target="_blank" rel="noreferrer" className={styles.ref}>
              {e.ref}
            </a>
          ) : (
            <span className={styles.ref}>{e.ref}</span>
          )}
        </li>
      ))}
      {items.length > limit && <li className={styles.more}>и ещё {items.length - limit}</li>}
    </ul>
  );
}
