import type { components } from "@levels/api-client";
import { createContext, useContext } from "react";

export type CurrentUser = components["schemas"]["CurrentUser"];

// Kept as a compatibility alias while feature pages migrate from the v1 owner model.
export type Admin = { displayName: string };

export type RegistrationInput = {
  displayName: string;
  email: string;
  password: string;
  preferredUnits: "metric" | "imperial";
  timezone: string;
};

export type AuthState = {
  admin?: Admin;
  user?: CurrentUser;
  isAuthenticated: boolean;
  isRestoring?: boolean;
  isSubmitting: boolean;
  error?: string;
  clearError?: () => void;
  updateCurrentUser?: (updates: Partial<CurrentUser>) => void;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  register?: (input: RegistrationInput) => Promise<boolean>;
};

export const AuthContext = createContext<AuthState | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
