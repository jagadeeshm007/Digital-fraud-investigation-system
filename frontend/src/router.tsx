import { createBrowserRouter } from 'react-router'
import AppShell from '@/components/AppShell'
import AlertsPage from '@/pages/AlertsPage'
import AuditPage from '@/pages/AuditPage'
import DataSafetyPage from '@/pages/DataSafetyPage'
import PlaceholderPage from '@/pages/PlaceholderPage'
import UploadPage from '@/pages/UploadPage'

export const routes = [
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <PlaceholderPage title="Dashboard" bolt="B2" /> },
      { path: 'upload', element: <UploadPage /> },
      { path: 'alerts', element: <AlertsPage /> },
      {
        // React Flow is heavy; load it only when an alert is opened.
        path: 'alerts/:alertId',
        lazy: () => import('@/pages/AlertDetailPage').then((m) => ({ Component: m.default })),
      },
      { path: 'cases', element: <PlaceholderPage title="Cases" bolt="B2" /> },
      { path: 'ai-activity', element: <PlaceholderPage title="AI Activity" bolt="B3" /> },
      { path: 'data-safety', element: <DataSafetyPage /> },
      { path: 'audit', element: <AuditPage /> },
      { path: '*', element: <PlaceholderPage title="Not found" bolt="a later bolt" /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
