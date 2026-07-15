import { Link } from "react-router-dom";

import "./landing.css";

const benefits = [
  ["Train with structure", "Build a split that gives every session a clear purpose."],
  ["Adapt without losing progress", "Change today, skip, or swap forward while history stays intact."],
  ["See the work add up", "Your character, streak, and records reflect consistent training."],
] as const;

export function LandingPage() {
  return (
    <main className="landing-page" id="main-content">
      <header className="landing-header">
        <Link className="landing-brand" to="/" aria-label="LEVELS home">
          <span aria-hidden="true">L</span>
          LEVELS
        </Link>
        <nav aria-label="Account navigation">
          <Link to="/login">Sign in</Link>
          <Link className="landing-header__create" to="/register">Create account</Link>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-hero__copy">
          <p className="landing-eyebrow">YOUR TRAINING, YOUR RUN</p>
          <h1>Progress feels better when the plan can move with you.</h1>
          <p>LEVELS turns structured workouts into a private character-progression journey—flexible enough for real life, precise enough to trust.</p>
          <div className="landing-actions">
            <Link className="landing-button landing-button--primary" to="/demo">Try demo</Link>
            <Link className="landing-button" to="/register">Create account</Link>
            <Link className="landing-text-link" to="/login">Sign in</Link>
          </div>
          <small>No public profile. No social feed. Your training data stays private.</small>
        </div>
        <div className="landing-visual" aria-label="A training path progressing through five levels">
          <div className="landing-visual__aura" aria-hidden="true" />
          {[1, 2, 3, 4, 5].map((level) => (
            <div className={`landing-level landing-level--${level}`} key={level}>
              <span>LEVEL</span>
              <strong>{level}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-benefits" aria-label="Why LEVELS">
        {benefits.map(([title, description], index) => (
          <article key={title}>
            <span aria-hidden="true">0{index + 1}</span>
            <h2>{title}</h2>
            <p>{description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
