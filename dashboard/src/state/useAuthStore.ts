import { create } from 'zustand';

export type UserRole = 'Administrator' | 'Operator' | 'Research' | 'Audit' | 'Read-only';

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar?: string;
}

interface AuthState {
  token: string | null;
  user: UserProfile | null;
  isAuthenticated: boolean;
  login: (email: string, role: UserRole) => void;
  logout: () => void;
  hasPermission: (requiredRoles: UserRole[]) => boolean;
}

const getSafeStorage = (key: string): string | null => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage.getItem(key);
    }
  } catch {}
  return null;
};

const setSafeStorage = (key: string, val: string): void => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(key, val);
    }
  } catch {}
};

const removeSafeStorage = (key: string): void => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.removeItem(key);
    }
  } catch {}
};

export const useAuthStore = create<AuthState>((set, get) => ({
  token: getSafeStorage('aurika_jwt') || 'mock-enterprise-token',
  user: {
    id: 'usr_001',
    name: 'Elena Vance',
    email: 'elena.vance@aurika.ai',
    role: 'Administrator',
  },
  isAuthenticated: true,

  login: (email: string, role: UserRole) => {
    const token = `jwt_${btoa(email)}_${role}_${Date.now()}`;
    setSafeStorage('aurika_jwt', token);
    set({
      token,
      isAuthenticated: true,
      user: {
        id: `usr_${Math.floor(Math.random() * 1000)}`,
        name: email.split('@')[0].replace('.', ' '),
        email,
        role,
      },
    });
  },

  logout: () => {
    removeSafeStorage('aurika_jwt');
    set({ token: null, user: null, isAuthenticated: false });
  },

  hasPermission: (requiredRoles: UserRole[]) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'Administrator') return true;
    return requiredRoles.includes(user.role);
  },
}));
