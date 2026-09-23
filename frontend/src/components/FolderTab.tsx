import type { CSSProperties, ReactNode } from "react";
import { NavLink } from "react-router-dom";
import styles from "./FolderTab.module.css";

export interface ExtraTab {
  to: string;
  label: string;
}

// Фиксированные пиксели по ширине (--page-width: 1280px, index.css) — макет нерезиновый.
// Высота — авто по контенту (children), поэтому вырез/обводка считаются отдельно для верхней
// части (капот, фиксированная высота CAP_H) и низа (произвольная высота).
const W = 1280;
const TAB_W = 400;
const TAB_H = 64;
const R = 24;
const CAP_H = TAB_H + R;
// Насколько далеко вниз "продлить" боковые стороны заливки — реальную высоту содержимого
// заранее не знаем, а overflow:hidden на .shape всё равно обрежет лишнее по факту рендера.
const EXTEND = 4000;

// ВАЖНО: раньше блюр считался дважды по отдельности — один раз для капота, второй раз для
// тела снизу, каждый раз отдельно размывая СВОЙ кусок фоновой картинки позади себя. Даже с
// одинаковым цветом заливки текстура размытия на стыке не совпадала (два разных источника
// blur). Правильно — один общий слой (.sharedFill) на всю фигуру сразу, размывающий фон один
// раз целиком; capot и тело — просто разные вырезы этого одного слоя.
const FILL_PATH =
  `M ${R},0 H ${TAB_W - R} A ${R},${R} 0 0 1 ${TAB_W},${R} ` +
  `V ${TAB_H - R} A ${R},${R} 0 0 0 ${TAB_W + R},${TAB_H} ` +
  `H ${W - R} A ${R},${R} 0 0 1 ${W},${TAB_H + R} ` +
  `V ${EXTEND} H 0 V ${R} A ${R},${R} 0 0 1 ${R},0 Z`;

// Обводка рисуется отдельно от заливки: только видимая верхняя часть (капот), без нижнего
// и левого/правого продолжения на всю высоту — те стороны тела ниже капота дорисовываются
// сплошным CSS-бордером того же конечного цвета градиента (.sides), см. FolderTab.module.css.
const BORDER_PATH =
  `M 0,${CAP_H} V ${R} A ${R},${R} 0 0 1 ${R},0 H ${TAB_W - R} A ${R},${R} 0 0 1 ${TAB_W},${R} ` +
  `V ${TAB_H - R} A ${R},${R} 0 0 0 ${TAB_W + R},${TAB_H} ` +
  `H ${W - R} A ${R},${R} 0 0 1 ${W},${TAB_H + R}`;

export function FolderTab({ label, extraTabs, children }: { label: string; extraTabs?: ExtraTab[]; children: ReactNode }) {
  const vars = {
    "--folder-cap-height": `${CAP_H}px`,
    "--folder-tab-width": `${TAB_W}px`,
    width: `${W}px`,
  } as CSSProperties;

  return (
    <div className={styles.wrapper} style={vars}>
      <div className={styles.shape}>
        <div className={styles.sharedFill} style={{ clipPath: `path('${FILL_PATH}')` }} />
        <div className={styles.label}>{label}</div>
        {extraTabs?.map((tab, i) => (
          <NavLink key={tab.to} to={tab.to} className={styles.extraTab} style={{ left: TAB_W + 20 + i * 220 }}>
            {tab.label}
          </NavLink>
        ))}
        <div className={styles.sides}>{children}</div>
      </div>
      {/* Обводка вынесена ЗА пределы .shape (у него overflow:hidden) — иначе половина штриха
          (он идёт по центру контура) обрезается на прямых краях, а на скруглениях/вырезе
          (не лежащих ровно на границе бокса) не обрезается вовсе — итоговая толщина плыла бы
          от 2.5px до 5px в разных местах одной и той же линии. Здесь обводка везде честные 5px. */}
      <svg className={styles.border} viewBox={`0 0 ${W} ${CAP_H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="folderGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#FFFFFF" />
            <stop offset="55%" stopColor="#8E8E8E" />
            <stop offset="100%" stopColor="#575757" />
          </linearGradient>
        </defs>
        <path d={BORDER_PATH} fill="none" stroke="url(#folderGradient)" strokeWidth={5} />
      </svg>
    </div>
  );
}
