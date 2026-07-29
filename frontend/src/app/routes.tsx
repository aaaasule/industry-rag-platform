import { createBrowserRouter } from 'react-router-dom';

import { LoginPage } from '@/features/auth/LoginPage';
import { ChatPage } from '@/features/chat/ChatPage';
import { DocumentDetailPage } from '@/features/knowledge/DocumentDetailPage';
import { KbDetailPage } from '@/features/knowledge/KbDetailPage';
import { KnowledgePage } from '@/features/knowledge/KnowledgePage';
import { AppLayout } from './AppLayout';
import { RequireAuth } from './RequireAuth';
import { OverviewPage } from './placeholders';
import { ModelOpsPlaceholder } from './placeholders';

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
      { path: 'knowledge/:kbId/documents/:docId', element: <DocumentDetailPage /> },
      { path: 'documents/:docId', element: <DocumentDetailPage /> },
      { path: 'chat', element: <ChatPage /> },
      { path: 'modelops', element: <ModelOpsPlaceholder /> },
    ],
  },
]);
