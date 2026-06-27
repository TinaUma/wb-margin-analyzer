import { createContext, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface AuthCtx {
  token: string | null
  setToken: (t: string | null) => void
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(
    () => localStorage.getItem('token'),
  )

  function setToken(t: string | null) {
    if (t) {
      localStorage.setItem('token', t)
    } else {
      localStorage.removeItem('token')
    }
    setTokenState(t)
  }

  function logout() {
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ token, setToken, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
