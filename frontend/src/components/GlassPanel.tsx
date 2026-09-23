import type { HTMLAttributes } from "react";
import styles from "./GlassPanel.module.css";

export function GlassPanel({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`${styles.panel} ${className ?? ""}`} {...props} />;
}
