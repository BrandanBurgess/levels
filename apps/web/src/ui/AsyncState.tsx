import type { ReactNode } from "react";

export function LoadingState({ message = "Waking up your training data…" }: { message?: string }) {
  return (
    <div aria-live="polite" className="state-card" role="status">
      <span aria-hidden="true" className="state-card__spinner" />
      <p>{message}</p>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="state-card state-card--error" role="alert">
      <p>{message}</p>
      {onRetry ? (
        <button className="button button--secondary" onClick={onRetry} type="button">
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="state-card">
      <h2>{title}</h2>
      <div>{children}</div>
    </div>
  );
}
