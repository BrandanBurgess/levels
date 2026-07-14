import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./app/AppShell";
import { AppProviders } from "./app/AppProviders";
import { PlaceholderPage } from "./app/PlaceholderPage";
import { LoginPage } from "./auth/LoginPage";
import { CharacterPage } from "./features/character/CharacterPage";
import { TodayPage } from "./features/today/TodayPage";

const pages = {
  today: {
    eyebrow: "TODAY · MONDAY",
    title: "Ready for Upper A",
    description: "Your training plan, target muscles, hydration, and latest wins live here.",
  },
  journal: {
    eyebrow: "TRAINING LOG",
    title: "Journal",
    description: "Start a workout or revisit a completed training session.",
  },
  character: {
    eyebrow: "YOUR CHARACTER",
    title: "Character",
    description: "See the muscles your current plan is developing, front and back.",
  },
  progress: {
    eyebrow: "TRAINING HISTORY",
    title: "Progress",
    description: "Review personal records, volume, and consistent work over time.",
  },
  more: {
    eyebrow: "PLAN & PREFERENCES",
    title: "More",
    description: "Open Growth, Splits, Library, or Settings.",
  },
  growth: {
    eyebrow: "EXPLAINABLE GUIDANCE",
    title: "Growth",
    description: "See conservative suggestions backed by your recent sessions.",
  },
  splits: {
    eyebrow: "TRAINING PLAN",
    title: "Splits",
    description: "Explore the active Upper / Lower plan and alternative routines.",
  },
  library: {
    eyebrow: "EXERCISE CATALOG",
    title: "Library",
    description: "Search movements, variations, equipment, and muscle targets.",
  },
  settings: {
    eyebrow: "OWNER CONTROLS",
    title: "Settings",
    description: "Manage profile details, units, visibility, and training defaults.",
  },
} as const;

export function App() {
  return (
    <AppProviders>
      <HashRouter>
        <Routes>
        <Route element={<AppShell />}>
          <Route index element={<TodayPage />} />
          <Route path="character" element={<CharacterPage />} />
          {Object.entries(pages)
            .filter(([path]) => path !== "today" && path !== "character")
            .map(([path, page]) => (
              <Route key={path} path={path} element={<PlaceholderPage {...page} />} />
            ))}
          <Route path="*" element={<Navigate replace to="/" />} />
          <Route path="login" element={<LoginPage />} />
        </Route>
        </Routes>
      </HashRouter>
    </AppProviders>
  );
}
