import { createBrowserRouter } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { KbDetailPage } from '@/features/knowledge/KbDetailPage';
import { KnowledgePage } from '@/features/knowledge/KnowledgePage';
import { AppLayout } from './AppLayout';
import { RequireAuth } from './RequireAuth';
import { OverviewPage } from './placeholders';
import { ChatPlaceholder, ModelOpsPlaceholder } from './placeholders';

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
      { path: 'knowledge', element: <KnowledgePage /> },
      { path: 'knowledge/:kbId', element: <KbDetailPage /> },
      { path: 'chat', element: <ChatPlaceholder /> },
      { path: 'modelops', element: <ModelOpsPlaceholder /> },
    ],
  },
]);
