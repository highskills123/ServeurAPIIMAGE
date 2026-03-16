import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import * as api from "../api";

const TOKEN_KEY = "pixelforge_token";

interface AuthState {
  token: string | null;
  user: api.MeOut | null;
  loading: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    token: null,
    user: null,
    loading: true,
  });

  // Restore session on start
  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(TOKEN_KEY);
        if (saved) {
          const user = await api.getMe(saved);
          setState({ token: saved, user, loading: false });
        } else {
          setState((s) => ({ ...s, loading: false }));
        }
      } catch {
        await AsyncStorage.removeItem(TOKEN_KEY);
        setState({ token: null, user: null, loading: false });
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await api.login(email, password);
    const user = await api.getMe(access_token);
    await AsyncStorage.setItem(TOKEN_KEY, access_token);
    setState({ token: access_token, user, loading: false });
  }, []);

  const signup = useCallback(async (email: string, password: string) => {
    await api.signup(email, password);
    await login(email, password);
  }, [login]);

  const logout = useCallback(async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setState({ token: null, user: null, loading: false });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
