import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AdminPage } from '@/features/admin/AdminPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { ChatPage } from '@/features/chat/ChatPage';
import { DocumentDetailPage } from '@/features/knowledge/DocumentDetailPage';
import { KbDetailPage } from '@/features/knowledge/KbDetailPage';
import { KnowledgePage } from '@/features/knowledge/KnowledgePage';
import { UsageDashboardPage } from '@/features/usages/UsageDashboardPage';
import { AppLayout } from './AppLayout';
import { OverviewPage } from './placeholders';
import { RequireAuth } from './RequireAuth';

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
      { path: 'usages', element: <UsageDashboardPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: 'modelops', element: <Navigate to="/admin?tab=connections" replace /> },
    ],
  },
]);
