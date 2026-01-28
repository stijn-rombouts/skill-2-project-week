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
    
    if (response.data.requires_2fa) {
      // Redirect to 2FA verification
      return {
        success: true,
        requires_2fa: true,
        token_2fa: response.data.token_2fa,
        username: response.data.username
      }
    }

    // Normal login
    this.token = response.data.access_token
    this.user = {
      username: response.data.username,
      role: response.data.role,
    }
    this.isAuthenticated = true

    localStorage.setItem('token', this.token)
    localStorage.setItem('user', JSON.stringify(this.user))

    return { success: true }
  } catch (error) {
    return { 
      success: false, 
      message: error.response?.data?.detail || 'Login failed' 
    }
  }
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
        } catch (error) {
          // Only logout if we get a 401 (unauthorized) response
          // This means the token is invalid or expired
          if (error.response?.status === 401) {
            this.logout()
          }
          // For other errors (network issues, backend down), keep the user logged in
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

    logout() {
      this.user = null
      this.token = null
      this.isAuthenticated = false
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },

    setToken(token) {
      this.token = token
      localStorage.setItem('token', token)
    },

    setUser(user) {
      this.user = user
      this.isAuthenticated = true
      localStorage.setItem('user', JSON.stringify(user))
    },
  },
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAuthStore, import.meta.hot))
}
