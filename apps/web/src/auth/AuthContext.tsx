import type { LevelsClient } from "@levels/api-client";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { apiClient } from "../api/client";
import {
  clearAccessToken,
  getAccessToken,
  setAccessToken,
} from "../api/tokenStore";
import {
  AuthContext,
  type AuthState,
  type CurrentUser,
  type RegistrationInput,
} from "./context";

const GENERIC_LOGIN_ERROR = "Sign in failed. Check your credentials and try again.";

function registrationError(status: number | undefined) {
  if (status === 403) return "Account creation is not available right now.";
  if (status === 409) return "Account creation could not be completed. If you already submitted this form, try signing in.";
  if (status === 429) return "Too many attempts. Please wait a moment and try again.";
  return "Account creation failed. Check your details and try again.";
}

export function AuthProvider({
  children,
  client = apiClient,
}: {
  children: ReactNode;
  client?: LevelsClient;
}) {
  const [user, setUser] = useState<CurrentUser>();
  const [isRestoring, setIsRestoring] = useState(Boolean(getAccessToken()));
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string>();

  const clearLocalAuth = useCallback(() => {
    clearAccessToken();
    setUser(undefined);
  }, []);

  useEffect(() => {
    if (!getAccessToken()) {
      setIsRestoring(false);
      return;
    }

    let active = true;
    void client
      .GET("/auth/me")
      .then(({ data, error: responseError }) => {
        if (!active) return;
        if (data && !responseError) {
          setUser(data);
          return;
        }
        clearLocalAuth();
      })
      .catch(() => {
        if (active) clearLocalAuth();
      })
      .finally(() => {
        if (active) setIsRestoring(false);
      });

    return () => {
      active = false;
    };
  }, [clearLocalAuth, client]);

  const login = useCallback(
    async (email: string, password: string) => {
      setIsSubmitting(true);
      setError(undefined);
      try {
        const { data, error: responseError, response } = await client.POST("/auth/login", {
          body: { email: email.trim(), password },
        });
        if (!data || responseError) {
          setError(
            response.status === 429
              ? "Too many attempts. Please wait a moment and try again."
              : GENERIC_LOGIN_ERROR,
          );
          return false;
        }
        setAccessToken(data.access_token);
        setUser(data.user);
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

  const register = useCallback(
    async (input: RegistrationInput) => {
      setIsSubmitting(true);
      setError(undefined);
      try {
        const { data, error: responseError, response } = await client.POST("/auth/register", {
          body: {
            display_name: input.displayName.trim(),
            email: input.email.trim(),
            password: input.password,
            preferred_units: input.preferredUnits,
            timezone: input.timezone,
          },
        });
        if (!data || responseError) {
          setError(registrationError(response.status));
          return false;
        }
        setAccessToken(data.access_token);
        setUser(data.user);
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

  const logout = useCallback(async () => {
    setError(undefined);
    try {
      if (getAccessToken()) await client.POST("/auth/logout");
    } catch {
      // Stateless logout is best-effort; local credentials must always be cleared.
    } finally {
      clearLocalAuth();
    }
  }, [clearLocalAuth, client]);

  const clearError = useCallback(() => setError(undefined), []);
  const value = useMemo<AuthState>(
    () => ({
      ...(user ? { admin: { displayName: user.display_name }, user } : {}),
      ...(error ? { error } : {}),
      isAuthenticated: Boolean(user),
      isRestoring,
      isSubmitting,
      clearError,
      login,
      logout,
      register,
    }),
    [clearError, error, isRestoring, isSubmitting, login, logout, register, user],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
