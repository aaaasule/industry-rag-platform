import { createBrowserRouter } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { AppLayout } from './AppLayout';
import { RequireAuth } from './RequireAuth';
import { OverviewPage } from './placeholders';
import { ChatPlaceholder, KnowledgePlaceholder, ModelOpsPlaceholder } from './placeholders';

export const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    path: '/',
    element: (
      <RequireAuth>
        <AppLayout />
      </RequireAuth>
    ),
    children: [
      { index: true, element: <OverviewPage /> },
      // 各业务页在 M1-M4 逐个替换，路由结构此时已定型
      { path: 'knowledge', element: <KnowledgePlaceholder /> },
      { path: 'chat', element: <ChatPlaceholder /> },
      { path: 'modelops', element: <ModelOpsPlaceholder /> },
    ],
  },
]);
