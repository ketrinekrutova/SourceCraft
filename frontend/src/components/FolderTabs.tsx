import type { CSSProperties, ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import styles from "./FolderTabs.module.css";

export interface FolderTabDef {
  to: string;
  label: string;
  end?: boolean;
}

const W = 1280;
const GAP = 28;
const TAB_H = 60;
const R = 16;
const CAP_H = TAB_H + R;
// Насколько далеко продлить боковые края заливки вниз — реальную высоту тела заранее не
// знаем (зависит от контента), а overflow:hidden у .shape всё равно обрежет лишнее по факту.
const EXTEND = 4000;

function isActivePath(pathname: string, to: string, end?: boolean): boolean {
  if (end ?? to === "/") return pathname === to;
  return pathname === to || pathname.startsWith(`${to}/`);
}

// Верхний контур зависит от положения активной вкладки: первая — вырез только справа (панель
// и вкладка делят общий левый край); последняя — вырез только слева (зеркально); посередине —
// вырез с обеих сторон. Сегменты дуг те же, что уже проверены вручную для одиночной вкладки
// (FolderTab.tsx) — левый вырез: sweep=0, центр в (tabStart-R, TAB_H-R); правый вырез: sweep=0,
// центр в (tabEnd+R, TAB_H-R); обычные скругления — sweep=1.
function buildTopPath(tabStart: number, tabEnd: number, bottomY: number): string {
  const leftFlush = tabStart <= 0;
  const rightFlush = tabEnd >= W;

  // Обе ветки стартуют из одной и той же точки (0, bottomY) — иначе при leftFlush=true
  // терялся весь левый край фигуры (был баг: путь начинался сразу с (R,0), без спуска к низу).
  const left = leftFlush
    ? `M 0,${bottomY} V ${R} A ${R},${R} 0 0 1 ${R},0`
    : `M 0,${bottomY} A ${R},${R} 0 0 1 ${R},${TAB_H} H ${tabStart - R} A ${R},${R} 0 0 0 ${tabStart},${TAB_H - R} V ${R} A ${R},${R} 0 0 1 ${tabStart + R},0`;

  const tabTop = `H ${tabEnd - R} A ${R},${R} 0 0 1 ${tabEnd},${R}`;

  const right = rightFlush
    ? ` V ${bottomY}`
    : ` V ${TAB_H - R} A ${R},${R} 0 0 0 ${tabEnd + R},${TAB_H} H ${W - R} A ${R},${R} 0 0 1 ${W},${TAB_H + R} V ${bottomY}`;

  return left + tabTop + right;
}

function buildFillPath(tabStart: number, tabEnd: number): string {
  // Начало и конец пути теперь всегда совпадают в (0, EXTEND) — просто "H 0 Z" замыкает,
  // отдельная обработка leftFlush для замыкания больше не нужна.
  return `${buildTopPath(tabStart, tabEnd, EXTEND)} H 0 Z`;
}

function buildBorderPath(tabStart: number, tabEnd: number): string {
  // Открытый контур (не замыкается) — только видимая верхняя обводка, до высоты капота.
  return buildTopPath(tabStart, tabEnd, CAP_H);
}

export function FolderTabs({ tabs, children }: { tabs: FolderTabDef[]; children: ReactNode }) {
  const location = useLocation();
  const found = tabs.findIndex((t) => isActivePath(location.pathname, t.to, t.end));
  const activeIndex = found === -1 ? 0 : found;

  const tabW = (W - GAP * (tabs.length - 1)) / tabs.length;
  const tabStart = activeIndex * (tabW + GAP);
  const tabEnd = tabStart + tabW;

  const fillPath = buildFillPath(tabStart, tabEnd);
  const borderPath = buildBorderPath(tabStart, tabEnd);

  const vars = { "--folder-cap-height": `${CAP_H}px`, width: `${W}px` } as CSSProperties;

  return (
    <div className={styles.wrapper} style={vars}>
      <div className={styles.shape}>
        <div className={styles.sharedFill} style={{ clipPath: `path('${fillPath}')` }} />
        {tabs.map((tab, i) => {
          const x = i * (tabW + GAP);
          const active = i === activeIndex;
          return (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end ?? tab.to === "/"}
              className={`${styles.label} ${active ? styles.labelActive : styles.labelInactive}`}
              style={{ left: x, width: tabW }}
            >
              <span className={styles.labelText}>{tab.label}</span>
            </NavLink>
          );
        })}
        <div className={styles.sides}>{children}</div>
      </div>
      {/* Обводка — отдельный SVG поверх, не внутри .shape (у него overflow:hidden обрезал бы
          половину штриха неравномерно, см. разбор в FolderTab.tsx). */}
      <svg className={styles.border} viewBox={`0 0 ${W} ${CAP_H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="folderTabsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="55%" stopColor="#8E8E8E" />
            <stop offset="100%" stopColor="#575757" />
          </linearGradient>
        </defs>
        <path d={borderPath} fill="none" stroke="url(#folderTabsGradient)" strokeWidth={5} />
      </svg>
    </div>
  );
}
