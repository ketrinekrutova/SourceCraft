// 3 чётких блока, не плавный градиент — согласуется с verdict() в бэке (README/aggregate.py):
// высокий Score — зелёный, средний — жёлтый, низкий — красный. Пороги подобраны так, чтобы
// пример с макета (92, 72 -> зелёный; 63, 55 -> жёлтый; 32, 10 -> красный) совпадал.
const GREEN = "#C0C960"; // >= 70
const YELLOW = "#EDC74A"; // 40-69
const RED = "#C02B55"; // < 40

export function scoreColor(score: number | null): string {
  if (score === null) return "rgba(0, 0, 0, 0.08)";
  if (score >= 70) return GREEN;
  if (score >= 40) return YELLOW;
  return RED;
}

function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Полупрозрачная версия — для больших заливок (ячейка Score в таблице, бейдж в "Моих
// репозиториях"), где сквозь цвет должен просвечивать размытый фон-картинка, как на макете
// (цвет не сплошной, видно фактуру фото под ним).
export function scoreColorSoft(score: number | null): string {
  if (score === null) return "rgba(0, 0, 0, 0.08)";
  if (score >= 70) return hexToRgba(GREEN, 0.5);
  if (score >= 40) return hexToRgba(YELLOW, 0.5);
  return hexToRgba(RED, 0.5);
}
