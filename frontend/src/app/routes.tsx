import { createBrowserRouter, Navigate } from 'react-router-dom';

import { AdminPage } from '@/features/admin/AdminPage';
import { LoginPage } from '@/features/auth/LoginPage';
import { ProfilePage } from '@/features/auth/ProfilePage';
import { ChatPage } from '@/features/chat/ChatPage';
import { DocumentDetailPage } from '@/features/knowledge/DocumentDetailPage';
import { KbWorkspaceLayout } from '@/features/knowledge/KbWorkspaceLayout';
import { KnowledgePage } from '@/features/knowledge/KnowledgePage';
import { KbFilesPanel } from '@/features/knowledge/panels/KbFilesPanel';
import { KbLogsPanel } from '@/features/knowledge/panels/KbLogsPanel';
import { KbRetrievalPanel } from '@/features/knowledge/panels/KbRetrievalPanel';
import { KbSettingsPanel } from '@/features/knowledge/panels/KbSettingsPanel';
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
      {
        path: 'knowledge/:kbId',
        element: <KbWorkspaceLayout />,
        children: [
          { index: true, element: <Navigate to="files" replace /> },
          { path: 'files', element: <KbFilesPanel /> },
          { path: 'retrieval', element: <KbRetrievalPanel /> },
          { path: 'logs', element: <KbLogsPanel /> },
          { path: 'settings', element: <KbSettingsPanel /> },
        ],
      },
      { path: 'knowledge/:kbId/documents/:docId', element: <DocumentDetailPage /> },
      { path: 'documents/:docId', element: <DocumentDetailPage /> },
      { path: 'chat', element: <ChatPage /> },
      { path: 'usages', element: <UsageDashboardPage /> },
      { path: 'admin', element: <AdminPage /> },
      { path: 'settings/profile', element: <ProfilePage /> },
      { path: 'modelops', element: <Navigate to="/admin?tab=connections" replace /> },
    ],
  },
]);
