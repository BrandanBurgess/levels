import { NavLink, Outlet } from "react-router-dom";

import { useAuth } from "../auth/context";

type NavItem = { label: string; to: string; icon: string; end?: boolean };

const primaryNavigation: NavItem[] = [
  { label: "Today", to: "/", icon: "◉", end: true },
  { label: "Journal", to: "/journal", icon: "▤" },
  { label: "Character", to: "/character", icon: "◇" },
  { label: "Progress", to: "/progress", icon: "↗" },
  { label: "More", to: "/more", icon: "•••" },
];

const secondaryNavigation: NavItem[] = [
  { label: "Growth", to: "/growth", icon: "✦" },
  { label: "Splits", to: "/splits", icon: "⑂" },
  { label: "Library", to: "/library", icon: "⌕" },
  { label: "Settings", to: "/settings", icon: "⚙" },
];

function NavigationLink({ item, mobile = false }: { item: NavItem; mobile?: boolean }) {
  return (
    <NavLink
      aria-label={item.label}
      className={({ isActive }) =>
        `${mobile ? "mobile-nav__link" : "side-nav__link"}${isActive ? " is-active" : ""}`
      }
      end={item.end ?? false}
      to={item.to}
    >
      <span aria-hidden="true" className="nav-icon">
        {item.icon}
      </span>
      <span>{item.label}</span>
    </NavLink>
  );
}

export function AppShell() {
  const { admin, isAuthenticated, logout } = useAuth();
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main-content">
        Skip to main content
      </a>

      <aside className="desktop-sidebar">
        <NavLink aria-label="LEVELS home" className="brand" to="/">
          <span className="brand__mark" aria-hidden="true">
            L
          </span>
          <span>LEVELS</span>
        </NavLink>
        <p className="mode-label">{isAuthenticated ? `Owner · ${admin?.displayName}` : "Public showcase"}</p>
        <nav aria-label="Primary navigation" className="side-nav">
          {primaryNavigation.slice(0, 4).map((item) => (
            <NavigationLink item={item} key={item.to} />
          ))}
        </nav>
        <p className="side-nav__section-label">Plan</p>
        <nav aria-label="Planning navigation" className="side-nav">
          {secondaryNavigation.map((item) => (
            <NavigationLink item={item} key={item.to} />
          ))}
        </nav>
        {isAuthenticated ? (
          <button className="owner-link owner-link--button" onClick={logout} type="button">Sign out</button>
        ) : (
          <NavLink className="owner-link" to="/login">Owner sign in</NavLink>
        )}
      </aside>

      <div className="shell-center">
        <header className="mobile-header">
          <NavLink aria-label="LEVELS home" className="brand" to="/">
            <span className="brand__mark" aria-hidden="true">
              L
            </span>
            <span>LEVELS</span>
          </NavLink>
          <span className="public-badge">{isAuthenticated ? "Owner" : "Public"}</span>
        </header>
        <main id="main-content" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <aside aria-label="Today at a glance" className="context-rail">
        <section className="rail-card">
          <p className="rail-card__label">Hydration</p>
          <p className="rail-card__value">Private</p>
          <p className="rail-card__hint">Visible only when the owner enables it.</p>
        </section>
        <section className="rail-card rail-card--accent">
          <p className="rail-card__label">Latest milestone</p>
          <p className="rail-card__value">Training data is waking up</p>
        </section>
      </aside>

      <nav aria-label="Mobile navigation" className="mobile-nav">
        {primaryNavigation.map((item) => (
          <NavigationLink item={item} key={item.to} mobile />
        ))}
      </nav>
    </div>
  );
}
