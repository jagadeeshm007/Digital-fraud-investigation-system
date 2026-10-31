import {
  BotIcon,
  BriefcaseIcon,
  LayoutDashboardIcon,
  ScrollTextIcon,
  ShieldCheckIcon,
  SirenIcon,
  UploadIcon,
} from 'lucide-react'
import { NavLink, Outlet, useLocation } from 'react-router'
import RoleSwitcher from '@/components/RoleSwitcher'
import { Badge } from '@/components/ui/badge'
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarTrigger,
} from '@/components/ui/sidebar'

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboardIcon },
  { to: '/upload', label: 'Data Upload', icon: UploadIcon },
  { to: '/alerts', label: 'Alerts', icon: SirenIcon },
  { to: '/cases', label: 'Cases', icon: BriefcaseIcon },
  { to: '/ai-activity', label: 'AI Activity', icon: BotIcon },
  { to: '/data-safety', label: 'Data Safety', icon: ShieldCheckIcon },
  { to: '/audit', label: 'Audit Trail', icon: ScrollTextIcon },
] as const

export default function AppShell() {
  const { pathname } = useLocation()
  return (
    <SidebarProvider>
      <Sidebar>
        <SidebarHeader className="px-4 py-3">
          <span className="font-heading font-semibold text-base">Fraud Investigation</span>
        </SidebarHeader>
        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupContent>
              <SidebarMenu>
                {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
                  <SidebarMenuItem key={to}>
                    <SidebarMenuButton
                      isActive={to === '/' ? pathname === '/' : pathname.startsWith(to)}
                      render={<NavLink to={to} end={to === '/'} />}
                    >
                      <Icon />
                      <span>{label}</span>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>
      </Sidebar>
      <SidebarInset className="min-w-0">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b px-4 py-2.5">
          <SidebarTrigger />
          <div className="flex items-center gap-3">
            <RoleSwitcher />
            <Badge variant="success">PII masked</Badge>
          </div>
        </header>
        <main className="mx-auto w-full min-w-0 max-w-[1440px] flex-1 p-4 md:p-6">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
