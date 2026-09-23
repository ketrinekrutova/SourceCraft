import type { Metrics, RepositoryDetail, RepositorySummary, UserRepository } from "../api/types";

// Числа — с макета Repo Health Score_без_авторизации.png (ряды рейтинга) и с примера в самом
// ТЗ (раздел 3.4, репозиторий на 74/100) — не придуманы, а перенесены как есть, чтобы вёрстка
// сразу проверялась на "правильных" данных.

export const ratingFixture: RepositorySummary[] = [
  { id: "repo-1", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib", health_score: 92, likes: 1200, language: "Python", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
  { id: "repo-2", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib-2", health_score: 72, likes: 14032, language: "React", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
  { id: "repo-3", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib-3", health_score: 63, likes: 2143, language: "C++", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
  { id: "repo-4", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib-4", health_score: 55, likes: 999, language: "Go", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
  { id: "repo-5", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib-5", health_score: 32, likes: 637, language: "Java", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
  { id: "repo-6", name: "awesome-lib", url: "https://sourcecraft.dev/org/awesome-lib-6", health_score: 10, likes: 23, language: "Паскаль", last_activity_at: daysAgo(2), last_analyzed_at: daysAgo(1), status: "COMPLETED" },
];

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

const metricsFixture: Metrics = {
  documentation: { score: 45, status: "OK", summary: "отсутствует инструкция локального запуска", weight: 0.15, details: {} },
  ci_cd: { score: 82, status: "OK", summary: "23% последних прогонов завершились неуспешно", weight: 0.15, details: {} },
  security: { score: 61, status: "OK", summary: "обнаружены две критические уязвимости в зависимостях", weight: 0.2, details: { critical: 2 } },
  activity: { score: 88, status: "OK", summary: "проект активно развивается", weight: 0.15, details: {} },
  issues: { score: 76, status: "OK", summary: "две открытые задачи не обновлялись более 30 дней", weight: 0.15, details: {} },
  code_health: { score: 70, status: "OK", summary: "найдено 47 TODO/FIXME, 12 из них старше шести месяцев", weight: 0.2, details: {} },
};

export function repositoryDetailFixture(id: string): RepositoryDetail {
  return {
    id,
    name: "awesome-project",
    url: "https://sourcecraft.dev/org/awesome-project",
    language: "Python",
    health_score: 74,
    verdict: "Хорошее состояние, есть точки роста",
    status: "COMPLETED",
    last_analyzed_at: daysAgo(1),
    metrics: metricsFixture,
    recommendations: [
      {
        id: "rec-1",
        priority: "HIGH",
        category: "security",
        title: "Обновите зависимости с критическими уязвимостями",
        description: "Найдено 2 критические уязвимости в зависимостях по данным AppSec SourceCraft. Обновите указанные пакеты до безопасных версий.",
        impact: "+8 к Security",
        evidence: [{ type: "vulnerability", ref: "CVE-2025-1234" }],
      },
      {
        id: "rec-2",
        priority: "MEDIUM",
        category: "documentation",
        title: "Добавьте инструкцию локального запуска",
        description: "В README отсутствует раздел с инструкцией установки и запуска проекта.",
        impact: "+10 к Documentation",
        evidence: [],
      },
    ],
  };
}

export const myRepositoriesFixture: UserRepository[] = [
  { id: "repo-my-1", name: "my-private-lib", private: true, health_score: 64, likes: 3, language: "Go", last_activity_at: daysAgo(5) },
  { id: "repo-my-2", name: "internal-tool", private: true, health_score: null, likes: 0, language: "Python", last_activity_at: daysAgo(30) },
];
