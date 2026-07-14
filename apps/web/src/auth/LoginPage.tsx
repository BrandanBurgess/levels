import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "./context";

export function LoginPage() {
  const { error, isSubmitting, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (await login(username, password)) navigate("/");
  }

  return (
    <article className="page-shell login-page">
      <header className="page-heading">
        <p className="eyebrow">OWNER ACCESS</p>
        <h1>Sign in</h1>
        <p>Private training controls stay hidden until the configured owner signs in.</p>
      </header>
      <form className="login-card" onSubmit={submit}>
        <label htmlFor="username">Username</label>
        <input
          autoComplete="username"
          id="username"
          maxLength={100}
          onChange={(event) => setUsername(event.target.value)}
          required
          value={username}
        />
        <label htmlFor="password">Password</label>
        <input
          autoComplete="current-password"
          id="password"
          maxLength={500}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        {error ? <p className="form-error" role="alert">{error}</p> : null}
        <button className="button button--primary" disabled={isSubmitting} type="submit">
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </article>
  );
}
