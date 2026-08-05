import { useContext } from 'react';

import { ToastContext, type ToastApi } from '@/components/toast/toastContext';

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast 必须在 ToastProvider 内使用');
  }
  return ctx;
}
