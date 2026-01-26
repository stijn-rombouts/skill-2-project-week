import { defineStore, acceptHMRUpdate } from 'pinia'
import { api } from 'boot/axios'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: null,
    isAuthenticated: false,
  }),

  getters: {
    getUser: (state) => state.user,
    getToken: (state) => state.token,
    isLoggedIn: (state) => state.isAuthenticated,
    userRole: (state) => state.user?.role || null,
  },

  actions: {
    async login(username, password) {
      try {
        const formData = new FormData()
        formData.append('username', username)
        formData.append('password', password)

        const response = await api.post('/api/login', formData)
        
        this.token = response.data.access_token
        this.user = {
          username: response.data.username,
          role: response.data.role,
        }
        this.isAuthenticated = true

        // Store token in localStorage for persistence
        localStorage.setItem('token', this.token)
        localStorage.setItem('user', JSON.stringify(this.user))

        return { success: true }
      } catch (error) {
        console.error('Login error:', error)
        return { 
          success: false, 
          message: error.response?.data?.detail || 'Login failed' 
        }
      }
    },

    async logout() {
      this.user = null
      this.token = null
      this.isAuthenticated = false
      
      // Clear localStorage
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    async checkAuth() {
      // Check if we have a stored token
      const token = localStorage.getItem('token')
      const userStr = localStorage.getItem('user')

      if (token && userStr) {
        this.token = token
        this.user = JSON.parse(userStr)
        this.isAuthenticated = true

        // Optionally verify token with backend
        try {
          await api.get('/api/me')
        } catch {
          // Token is invalid, clear auth
          this.logout()
        }
      }
    },

    async fetchCurrentUser() {
      try {
        const response = await api.get('/api/me')
        this.user = {
          username: response.data.username,
          role: response.data.role,
        }
        return response.data
      } catch (error) {
        console.error('Error fetching user:', error)
        this.logout()
        throw error
      }
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
