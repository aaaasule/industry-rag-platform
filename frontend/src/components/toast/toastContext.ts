import { createContext } from 'react';

export type ToastTone = 'info' | 'success' | 'error';

export type ToastOptions = {
  tone?: ToastTone;
  durationMs?: number;
};

export type ToastApi = {
  toast: (message: string, options?: ToastOptions) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
};

export const ToastContext = createContext<ToastApi | null>(null);
