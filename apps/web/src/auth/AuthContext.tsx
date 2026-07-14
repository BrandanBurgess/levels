import type { LevelsClient } from "@levels/api-client";
import { useCallback, useMemo, useState, type ReactNode } from "react";

import { apiClient } from "../api/client";
import { clearAccessToken, setAccessToken } from "../api/tokenStore";
import { AuthContext, type Admin, type AuthState } from "./context";

export function AuthProvider({
  children,
  client = apiClient,
}: {
  children: ReactNode;
  client?: LevelsClient;
}) {
  const [admin, setAdmin] = useState<Admin>();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  const login = useCallback(
    async (username: string, password: string) => {
      setIsSubmitting(true);
      setError(undefined);
      try {
        const { data, error: responseError } = await client.POST("/auth/login", {
          body: { username, password },
        });
        if (!data || responseError) {
          setError("Sign in failed. Check your credentials and try again.");
          return false;
        }
        setAccessToken(data.access_token);
        setAdmin({ displayName: data.admin.display_name });
        return true;
      } catch {
        setError("The training API is unavailable. Try again in a moment.");
        return false;
      } finally {
        setIsSubmitting(false);
      }
    },
    [client],
  );

  const logout = useCallback(() => {
    clearAccessToken();
    setAdmin(undefined);
    setError(undefined);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      ...(admin ? { admin } : {}),
      ...(error ? { error } : {}),
      isAuthenticated: Boolean(admin),
      isSubmitting,
      login,
      logout,
    }),
    [admin, error, isSubmitting, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
