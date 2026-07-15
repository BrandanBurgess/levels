import { HashRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppProviders } from "./app/AppProviders";
import { AppShell } from "./app/AppShell";
import { PlaceholderPage } from "./app/PlaceholderPage";
import { GuestOnly, MemberAccess } from "./auth/MemberAccess";
import { LoginPage } from "./auth/LoginPage";
import { RegisterPage } from "./auth/RegisterPage";
import { CharacterPage } from "./features/character/CharacterPage";
import { DemoPage } from "./features/demo/DemoPage";
import { GrowthPage } from "./features/growth/GrowthPage";
import { JournalPage } from "./features/journal/JournalPage";
import { LibraryPage } from "./features/library/LibraryPage";
import { ProgressPage } from "./features/progress/ProgressPage";
import { SettingsPage } from "./features/settings/SettingsPage";
import { SplitsPage } from "./features/splits/SplitsPage";
import { TodayPage } from "./features/today/TodayPage";

const morePage = {
  eyebrow: "PLAN & PREFERENCES",
  title: "More",
  description: "Open Growth, Splits, Library, or Settings.",
};

export function App() {
  return (
    <AppProviders>
      <HashRouter>
        <Routes>
          <Route path="login" element={<GuestOnly><LoginPage /></GuestOnly>} />
          <Route path="register" element={<GuestOnly><RegisterPage /></GuestOnly>} />
          <Route path="demo/*" element={<DemoPage />} />

          <Route element={<MemberAccess />}>
            <Route element={<AppShell />}>
              <Route index element={<TodayPage />} />
              <Route path="growth" element={<GrowthPage />} />
              <Route path="journal" element={<JournalPage />} />
              <Route path="progress" element={<ProgressPage />} />
              <Route path="character" element={<CharacterPage />} />
              <Route path="library" element={<LibraryPage />} />
              <Route path="splits" element={<SplitsPage />} />
              <Route path="settings" element={<SettingsPage />} />
              <Route path="more" element={<PlaceholderPage {...morePage} />} />
              <Route path="*" element={<Navigate replace to="/" />} />
            </Route>
          </Route>
        </Routes>
      </HashRouter>
    </AppProviders>
  );
}
