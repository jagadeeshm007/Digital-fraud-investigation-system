import { useSyncExternalStore } from 'react'

// Mirrors app/permissions.py: the server is the authority, the UI only hides what a role cannot do.
export const ROLES = ['analyst', 'investigator', 'supervisor'] as const
export type Role = (typeof ROLES)[number]

export const ROLE_LABELS: Record<Role, string> = {
  analyst: 'Analyst',
  investigator: 'Investigator',
  supervisor: 'Supervisor',
}

const STORAGE_KEY = 'dfis.role'
const listeners = new Set<() => void>()

function readStored(): Role {
  try {
    const value = localStorage.getItem(STORAGE_KEY)
    return ROLES.includes(value as Role) ? (value as Role) : 'analyst'
  } catch {
    return 'analyst'
  }
}

let current: Role = readStored()

export function getRole(): Role {
  return current
}

export function setRole(role: Role): void {
  current = role
  try {
    localStorage.setItem(STORAGE_KEY, role)
  } catch {
    // storage unavailable: the role still applies for this session
  }
  listeners.forEach((notify) => notify())
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function useRole(): Role {
  return useSyncExternalStore(subscribe, getRole)
}
