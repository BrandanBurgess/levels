import { NavLink } from "react-router-dom";

export function PlaceholderPage({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  const isMore = title === "More";
  return (
    <article className="page-shell">
      <header className="page-heading">
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>

      {isMore ? (
        <nav aria-label="More destinations" className="destination-grid">
          {([
            ["Growth", "/growth", "Conservative next-step guidance"],
            ["Splits", "/splits", "Training days and templates"],
            ["Library", "/library", "Exercises and variations"],
            ["Settings", "/settings", "Profile and visibility"],
          ] as const).map(([label, to, detail]) => (
            <NavLink className="destination-card" key={to} to={to}>
              <span>{label}</span>
              <small>{detail}</small>
            </NavLink>
          ))}
        </nav>
      ) : (
        <section className="feature-preview" aria-label={`${title} preview`}>
          <div className="feature-preview__glow" aria-hidden="true" />
          <p className="feature-preview__label">LEVEL 01</p>
          <h2>Build the next rep</h2>
          <p>Focused training data will appear here as the experience connects.</p>
        </section>
      )}
    </article>
  );
}
