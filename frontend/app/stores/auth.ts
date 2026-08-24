import { defineStore } from 'pinia'
import type { AuthResponse, User } from '~/types'
import { apiFetch } from '~/composables/useApi'

const TOKEN_KEY = 'oscae_token'

interface AuthState {
  token: string
  user: User | null
  loading: boolean
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: '',
    user: null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => Boolean(state.token && state.user),
  },

  actions: {
    setAuth(token: string, user: User) {
      this.token = token
      this.user = user
      if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, token)
      }
    },

    async hydrate() {
      if (typeof window === 'undefined') return
      const token = localStorage.getItem(TOKEN_KEY)
      if (!token) return

      this.token = token
      try {
        const data = await apiFetch<{ user: User }>('/auth/me')
        this.user = data.user
      } catch {
        this.clearAuth()
      }
    },

    async login(username: string, password: string) {
      this.loading = true
      try {
        const data = await apiFetch<AuthResponse>('/auth/login', {
          method: 'POST',
          body: { username, password },
        })
        this.setAuth(data.token, data.user)
      } finally {
        this.loading = false
      }
    },

    async register(payload: {
      username: string
      password: string
      email?: string
      phone?: string
      realName?: string
    }) {
      this.loading = true
      try {
        const data = await apiFetch<AuthResponse>('/auth/register', {
          method: 'POST',
          body: payload,
        })
        this.setAuth(data.token, data.user)
      } finally {
        this.loading = false
      }
    },

    async updateProfile(payload: {
      email?: string
      phone?: string
      realName?: string
      avatar?: string
    }) {
      const data = await apiFetch<{ user: User }>('/auth/me', {
        method: 'PUT',
        body: payload,
      })
      this.user = data.user
      return data.user
    },

    async changePassword(oldPassword: string, newPassword: string) {
      await apiFetch<{ message: string }>('/auth/password', {
        method: 'PUT',
        body: { oldPassword, newPassword },
      })
    },

    clearAuth() {
      this.token = ''
      this.user = null
      if (typeof window !== 'undefined') {
        localStorage.removeItem(TOKEN_KEY)
      }
    },

    logout() {
      this.clearAuth()
      navigateTo('/')
    },
  },
})
