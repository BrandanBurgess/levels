import { createContext, useContext } from "react";

export type Admin = { displayName: string };
export type AuthState = {
  admin?: Admin;
  isAuthenticated: boolean;
  isSubmitting: boolean;
  error?: string;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
};

export const AuthContext = createContext<AuthState | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
