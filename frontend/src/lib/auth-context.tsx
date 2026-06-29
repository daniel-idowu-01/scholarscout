'use client'

import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import type { TokenResponse } from '@/types'

interface AuthContextType {
  accessToken: string | null
  isAuthenticated: boolean
  userEmail: string | null
  login: (tokenResponse: TokenResponse) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

function decodeEmail(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    return (payload.sub as string) ?? null
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(null)

  useEffect(() => {
    const stored = localStorage.getItem('access_token')
    if (stored) setAccessToken(stored)
  }, [])

  function login(tokenResponse: TokenResponse) {
    localStorage.setItem('access_token', tokenResponse.access_token)
    setAccessToken(tokenResponse.access_token)
  }

  function logout() {
    localStorage.removeItem('access_token')
    setAccessToken(null)
  }

  return (
    <AuthContext.Provider
      value={{
        accessToken,
        isAuthenticated: !!accessToken,
        userEmail: accessToken ? decodeEmail(accessToken) : null,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}