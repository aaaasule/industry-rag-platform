import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import { router } from '@/app/routes';
import { ToastProvider } from '@/components/toast/ToastProvider';
import { ApiError } from '@/lib/http';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 401 已由 http.ts 自动刷新处理，重试只会放大真实故障；
      // 4xx 属于确定性失败，重试没有意义
      retry: (failureCount, error) =>
        error instanceof ApiError && error.status >= 500 && failureCount < 2,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
});

const container = document.getElementById('root');
if (!container) throw new Error('缺少 #root 挂载点');

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <RouterProvider router={router} />
      </ToastProvider>
    </QueryClientProvider>
  </StrictMode>,
);
