import { Select, SelectItem, SelectPopup, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ROLE_LABELS, ROLES, setRole, useRole, type Role } from '@/lib/role'

const ITEMS = ROLES.map((r) => ({ value: r, label: ROLE_LABELS[r] }))

export default function RoleSwitcher() {
  const role = useRole()
  return (
    <div className="flex items-center gap-2">
      <span id="role-label" className="text-muted-foreground text-sm">
        Role
      </span>
      <Select items={ITEMS} value={role} onValueChange={(value) => value && setRole(value as Role)}>
        <SelectTrigger aria-labelledby="role-label" className="min-w-36" size="sm">
          <SelectValue />
        </SelectTrigger>
        <SelectPopup>
          {ITEMS.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              {item.label}
            </SelectItem>
          ))}
        </SelectPopup>
      </Select>
    </div>
  )
}
