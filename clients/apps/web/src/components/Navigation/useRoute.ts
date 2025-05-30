import { OrganizationContext } from '@/providers/maintainerOrganization'
import { useContext } from 'react'
import { useDashboardRoutes } from '../Dashboard/navigation'

export const useRoute = () => {
  const orgContext = useContext(OrganizationContext)
  const org = orgContext?.organization

  const dashboardRoutes = useDashboardRoutes(org, true)

  const currentRoute = dashboardRoutes.find((r) => r.isActive)

  const currentSubRoute = currentRoute?.subs?.find(
    (r) => 'isActive' in r && r.isActive,
  )

  return {
    currentRoute,
    currentSubRoute,
  }
}
