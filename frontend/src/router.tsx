import { createBrowserRouter } from 'react-router'
import AppShell from '@/components/AppShell'
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
      { path: 'alerts', element: <PlaceholderPage title="Alerts" bolt="B2" /> },
      { path: 'cases', element: <PlaceholderPage title="Cases" bolt="B2" /> },
      { path: 'ai-activity', element: <PlaceholderPage title="AI Activity" bolt="B3" /> },
      { path: 'data-safety', element: <DataSafetyPage /> },
      { path: 'audit', element: <AuditPage /> },
      { path: '*', element: <PlaceholderPage title="Not found" bolt="a later bolt" /> },
    ],
  },
]

export const router = createBrowserRouter(routes)
