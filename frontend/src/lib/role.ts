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

// Who is acting (sent as X-User). Two named users per role so maker-checker can be shown:
// a hold recommended by one Supervisor must be approved by the other.
export const USERS: Record<Role, string[]> = {
  analyst: ['analyst-1', 'analyst-2'],
  investigator: ['investigator-1', 'investigator-2'],
  supervisor: ['supervisor-1', 'supervisor-2'],
}

const USER_KEY = 'dfis.user'

function readUser(role: Role): string {
  try {
    const value = localStorage.getItem(USER_KEY)
    return value && USERS[role].includes(value) ? value : USERS[role][0]
  } catch {
    return USERS[role][0]
  }
}

let currentUser: string = readUser(current)

export function getUser(): string {
  return USERS[current].includes(currentUser) ? currentUser : USERS[current][0]
}

export function setUser(user: string): void {
  currentUser = user
  try {
    localStorage.setItem(USER_KEY, user)
  } catch {
    // storage unavailable: the user still applies for this session
  }
  listeners.forEach((notify) => notify())
}

export function useUser(): string {
  return useSyncExternalStore(subscribe, getUser)
}
