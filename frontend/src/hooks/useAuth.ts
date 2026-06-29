import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi } from '@/lib/api'

interface User {
  id: string
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
}

interface AuthState {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  setUser: (user: User | null) => void
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  fetchUser: () => Promise<void>
}

export const useAuth = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      isLoading: true,
      isAuthenticated: false,
      
      setUser: (user) => set({ user, isAuthenticated: !!user }),
      
      login: async (email, password) => {
        const response = await authApi.login({ email, password })
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)
        set({ user: response.user, isAuthenticated: true })
      },
      
      register: async (email, password, fullName) => {
        const response = await authApi.register({
          email,
          password,
          full_name: fullName,
        })
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)
        set({ user: response.user, isAuthenticated: true })
      },
      
      logout: () => {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        set({ user: null, isAuthenticated: false })
      },
      
      fetchUser: async () => {
        try {
          set({ isLoading: true })
          const token = localStorage.getItem('access_token')
          if (!token) {
            set({ user: null, isAuthenticated: false, isLoading: false })
            return
          }
          
          const user = await authApi.me()
          set({ user, isAuthenticated: true, isLoading: false })
        } catch (error) {
          // Network error or API not available - clear tokens and show login page
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
          set({ user: null, isAuthenticated: false, isLoading: false })
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)

// Initialize auth state on app load (only in browser)
if (typeof window !== 'undefined') {
  // Use setTimeout to ensure React is ready
  setTimeout(() => {
    useAuth.getState().fetchUser()
  }, 0)
}

