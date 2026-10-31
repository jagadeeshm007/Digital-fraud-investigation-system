import { createBrowserRouter } from 'react-router'
import AppShell from '@/components/AppShell'
import AiActivityPage from '@/pages/AiActivityPage'
import AlertsPage from '@/pages/AlertsPage'
import CaseDetailPage from '@/pages/CaseDetailPage'
import CasesPage from '@/pages/CasesPage'
import DashboardPage from '@/pages/DashboardPage'
import AuditPage from '@/pages/AuditPage'
import DataSafetyPage from '@/pages/DataSafetyPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import UploadPage from '@/pages/UploadPage'

export const routes = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'upload', element: <UploadPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      {
        // React Flow is heavy; load it only when an alert is opened.
        path: 'alerts/:alertId',
        lazy: () => import('@/pages/AlertDetailPage').then((m) => ({ Component: m.default })),
      },
      { path: 'cases', element: <CasesPage /> },
      { path: 'cases/:caseId', element: <CaseDetailPage /> },
      { path: 'ai-activity', element: <AiActivityPage /> },
      { path: 'data-safety', element: <DataSafetyPage /> },
      { path: 'audit', element: <AuditPage /> },
      { path: '*', element: <PlaceholderPage title="Not found" bolt="a later bolt" /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
