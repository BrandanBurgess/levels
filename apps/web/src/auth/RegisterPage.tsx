import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { useAuth } from "./context";
import "./auth.css";

function localTimezone() {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || "America/Toronto";
}

export function RegisterPage() {
  const { clearError, error, isSubmitting, register } = useAuth();
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [preferredUnits, setPreferredUnits] = useState<"metric" | "imperial">("metric");
  const [timezone, setTimezone] = useState(localTimezone);

  useEffect(() => {
    clearError?.();
    return () => clearError?.();
  }, [clearError]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (register && await register({ displayName, email, password, preferredUnits, timezone })) {
      navigate("/", { replace: true });
    }
  }

  return (
    <main className="auth-page" id="main-content">
      <Link className="auth-brand" to="/" aria-label="LEVELS home">
        <span aria-hidden="true">L</span>
        LEVELS
      </Link>
      <article className="auth-panel auth-panel--wide">
        <header>
          <p className="auth-eyebrow">START YOUR RUN</p>
          <h1>Create account</h1>
          <p>Build a private training plan, adapt each day, and keep your history yours.</p>
        </header>
        <form className="auth-form auth-form--register" onSubmit={submit}>
          <label htmlFor="display-name">Display name</label>
          <input
            autoComplete="name"
            id="display-name"
            maxLength={80}
            onChange={(event) => setDisplayName(event.target.value)}
            required
            value={displayName}
          />
          <label htmlFor="register-email">Email</label>
          <input
            autoComplete="email"
            id="register-email"
            inputMode="email"
            maxLength={254}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
          <label htmlFor="new-password">Password</label>
          <input
            aria-describedby="password-help"
            autoComplete="new-password"
            id="new-password"
            maxLength={256}
            minLength={10}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          <small id="password-help">Use at least 10 characters. Password managers and paste are supported.</small>
          <label htmlFor="preferred-units">Preferred units</label>
          <select
            id="preferred-units"
            onChange={(event) => setPreferredUnits(event.target.value as "metric" | "imperial")}
            value={preferredUnits}
          >
            <option value="metric">Metric</option>
            <option value="imperial">Imperial</option>
          </select>
          <label htmlFor="timezone">Timezone</label>
          <input
            id="timezone"
            maxLength={100}
            onChange={(event) => setTimezone(event.target.value)}
            required
            value={timezone}
          />
          <label className="auth-consent" htmlFor="terms-accepted">
            <input id="terms-accepted" required type="checkbox" />
            <span>I agree to the basic terms and privacy notice.</span>
          </label>
          {error ? <p className="auth-error auth-form__full" role="alert">{error}</p> : null}
          {isSubmitting ? (
            <p className="auth-progress auth-form__full" role="status">
              Creating your private account and starter plan. This can take a few seconds.
            </p>
          ) : null}
          <button className="auth-button auth-button--primary auth-form__full" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Creating account…" : "Create account"}
          </button>
        </form>
        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
        <p className="auth-limitation">Email verification, OAuth, and password-reset email are not included yet.</p>
      </article>
    </main>
  );
}
