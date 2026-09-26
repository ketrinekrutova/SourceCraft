import type { ButtonHTMLAttributes } from "react";
import styles from "./PillButton.module.css";

// Кнопка-«пилюля» с той же выпуклой обводкой, что у дропдауна и кнопки входа (Dropdown.module.css,
// Layout.module.css): внешний слой - кольцо-градиент, внутренний - заливка с блюром.
export function PillButton({
  children,
  className,
  light,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { light?: boolean }) {
  return (
    <button type="button" className={`${styles.button} ${className ?? ""}`} {...props}>
      <span className={`${styles.inner} ${light ? styles.light : ""}`}>{children}</span>
    </button>
  );
}
