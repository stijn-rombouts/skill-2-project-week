<template>
  <div class="fullscreen flex flex-center" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)">
    <q-card style="width: 400px; max-width: 90vw">
      <q-card-section>
        <div class="text-h6">Two-Factor Authentication</div>
        <div class="text-caption text-grey-7">Enter the 6-digit code from your authenticator app</div>
      </q-card-section>

      <q-card-section>
        <p>Enter the 6-digit code from your authenticator app:</p>
        <q-input
          v-model="code"
          label="Authentication Code"
          outlined
          maxlength="6"
          input-class="text-center text-h6"
          @keyup.enter="onSubmit"
        />
      </q-card-section>

      <q-card-section>
        <q-btn
          label="Verify"
          color="primary"
          class="full-width"
          :loading="loading"
          @click="onSubmit"
        />
      </q-card-section>

      <q-card-section v-if="error" class="text-negative">
        {{ error }}
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from 'stores/auth-store'
import { api } from 'boot/axios'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const code = ref('')
const loading = ref(false)
const error = ref('')

async function onSubmit() {
  if (!code.value || code.value.length !== 6) {
    error.value = 'Please enter a 6-digit code'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const token_2fa = route.query.token_2fa
    if (!token_2fa) {
      error.value = 'Invalid 2FA session. Please login again.'
      await router.push('/login')
      return
    }

    const response = await api.post('/api/2fa/verify-login', {
      code: code.value,
      token_2fa: token_2fa
    })

    // Update auth store with token and user info
    authStore.setToken(response.data.access_token)
    authStore.setUser({
      username: response.data.username,
      role: response.data.role
    })

    // Redirect based on role
    const role = response.data.role
    if (role === 'mantelzorger') {
      await router.push('/mantelzorger/dashboard')
    } else if (role === 'zorgverlener') {
      await router.push('/zorgverlener/dashboard')
    } else if (role === 'patient') {
      await router.push('/home')
    } else {
      await router.push('/home')
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Invalid code. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>