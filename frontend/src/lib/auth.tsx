import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { api, tokens } from './api'
import type { User } from './types'

interface AuthCtx {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (data: RegisterData) => Promise<void>
  logout: () => void
}

interface RegisterData {
  name: string
  email: string
  password: string
  org_name?: string
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tokens.access) {
      setLoading(false)
      return
    }
    api
      .get<User>('/auth/me')
      .then((r) => setUser(r.data))
      .catch(() => tokens.clear())
      .finally(() => setLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const r = await api.post('/auth/login', { email, password })
    tokens.set(r.data.access_token, r.data.refresh_token)
    const me = await api.get<User>('/auth/me')
    setUser(me.data)
  }

  async function register(data: RegisterData) {
    const r = await api.post('/auth/register', data)
    tokens.set(r.data.access_token, r.data.refresh_token)
    const me = await api.get<User>('/auth/me')
    setUser(me.data)
  }

  function logout() {
    tokens.clear()
    setUser(null)
  }

  return <Ctx.Provider value={{ user, loading, login, register, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
