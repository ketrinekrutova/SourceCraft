import { useEffect, useRef, useState } from "react";
import styles from "./Dropdown.module.css";

export interface DropdownOption {
  value: string;
  label: string;
}

export function Dropdown({
  value,
  options,
  onChange,
}: {
  value: string;
  options: DropdownOption[];
  onChange: (value: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const current = options.find((o) => o.value === value);

  return (
    <div className={styles.wrapper} ref={wrapperRef}>
      <button type="button" className={styles.trigger} onClick={() => setOpen((prev) => !prev)}>
        <span className={styles.triggerInner}>
          {current?.label ?? value}
          <svg
            className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}
            width="12"
            height="8"
            viewBox="0 0 12 8"
            fill="none"
          >
            <path d="M1.5 1.5L6 6L10.5 1.5" stroke="#2D2D2D" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>
      <div className={`${styles.menu} ${open ? styles.menuOpen : ""}`}>
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`${styles.option} ${option.value === value ? styles.optionActive : ""}`}
            onClick={() => {
              onChange(option.value);
              setOpen(false);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
