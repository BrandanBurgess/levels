import { useNavigate } from "react-router-dom";

import { useAuth } from "./context";
import "./auth.css";

export function AccountMenu({ compact = false }: { compact?: boolean }) {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  async function signOut() {
    await logout();
    navigate("/", { replace: true });
  }

  return (
    <details className={`account-menu${compact ? " account-menu--compact" : ""}`}>
      <summary aria-label="Account menu">
        <span aria-hidden="true" className="account-menu__avatar">{user.display_name.slice(0, 1).toUpperCase()}</span>
        <span className="account-menu__summary-copy">
          <strong>{user.display_name}</strong>
          {!compact ? <small>Account</small> : null}
        </span>
      </summary>
      <div className="account-menu__popover">
        <strong>{user.display_name}</strong>
        <span>{user.email}</span>
        <span className="account-menu__status"><i aria-hidden="true" />{user.account_status}</span>
        <button onClick={() => void signOut()} type="button">Sign out</button>
      </div>
    </details>
  );
}
