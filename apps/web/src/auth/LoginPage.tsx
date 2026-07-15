import { useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "./context";
import "./auth.css";

type ReturnState = { from?: string };

export function LoginPage() {
  const { clearError, error, isSubmitting, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  useEffect(() => {
    clearError?.();
    return () => clearError?.();
  }, [clearError]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await login(email, password)) {
      const destination = (location.state as ReturnState | null)?.from ?? "/";
      navigate(destination, { replace: true });
    }
  }

  return (
    <main className="auth-page" id="main-content">
      <Link className="auth-brand" to="/" aria-label="LEVELS home">
        <span aria-hidden="true">L</span>
        LEVELS
      </Link>
      <article className="auth-panel">
        <header>
          <p className="auth-eyebrow">WELCOME BACK</p>
          <h1>Sign in</h1>
          <p>Your training history and plans are private to your account.</p>
        </header>
        <form className="auth-form" onSubmit={submit}>
          <label htmlFor="email">Email</label>
          <input
            autoComplete="email"
            id="email"
            inputMode="email"
            maxLength={254}
            onChange={(event) => setEmail(event.target.value)}
            required
            type="email"
            value={email}
          />
          <label htmlFor="password">Password</label>
          <input
            autoComplete="current-password"
            id="password"
            maxLength={256}
            onChange={(event) => setPassword(event.target.value)}
            required
            type="password"
            value={password}
          />
          {error ? <p className="auth-error" role="alert">{error}</p> : null}
          <button className="auth-button auth-button--primary" disabled={isSubmitting} type="submit">
            {isSubmitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <p className="auth-switch">New to LEVELS? <Link to="/register">Create an account</Link></p>
        <p className="auth-limitation">Password reset by email is not available in this release.</p>
      </article>
    </main>
  );
}
