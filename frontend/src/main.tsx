import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Пока бэкенд не готов (см. backend/CHECK.md), все запросы перехватывает MSW по контракту
// backend/openapi.yaml. Когда бэкенд заработает — убрать этот блок, компоненты не меняются.
async function enableMocking() {
  if (import.meta.env.PROD) return;
  const { worker } = await import("./mocks/browser");
  return worker.start({ onUnhandledRequest: "bypass" });
}

enableMocking().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
