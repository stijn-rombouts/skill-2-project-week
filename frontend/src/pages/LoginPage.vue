<template>
  <div
    class="fullscreen flex flex-center"
    style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
  >
    <q-card style="width: 400px; max-width: 90vw">
      <q-card-section>
        <div class="text-h6">Login</div>
      </q-card-section>

      <q-card-section>
        <q-form @submit="onSubmit" class="q-gutter-md">
          <q-input
            v-model="username"
            label="Username"
            lazy-rules
            :rules="[(val) => (val && val.length > 0) || 'Username is required']"
            outlined
          >
            <template v-slot:prepend>
              <q-icon name="person" />
            </template>
          </q-input>

          <q-input
            v-model="password"
            label="Password"
            type="password"
            lazy-rules
            :rules="[(val) => (val && val.length > 0) || 'Password is required']"
            outlined
          >
            <template v-slot:prepend>
              <q-icon name="lock" />
            </template>
          </q-input>

          <div class="q-mt-md">
            <q-btn
              label="Login"
              type="submit"
              color="primary"
              class="full-width"
              :loading="loading"
            />
          </div>
        </q-form>
      </q-card-section>

      <q-card-section v-if="errorMessage" class="text-negative">
        {{ errorMessage }}
      </q-card-section>

      <q-card-section>
        <div class="text-caption text-grey-7">
          <div><strong>Test Users:</strong></div>
          <div>Mantelzorger: mantelzorger1 / password123</div>
          <div>Patient: patient1 / password123</div>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth-store'
import { useQuasar } from 'quasar'

const router = useRouter()
const authStore = useAuthStore()
const $q = useQuasar()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMessage = ref('')

async function onSubmit() {
  loading.value = true
  errorMessage.value = ''

  const result = await authStore.login(username.value, password.value)

  loading.value = false

  if (result.success) {
  console.log('Login successful')

  // If backend says 2FA is required, go to verify page first
  if (result.requires_2fa) {
    await router.push({
      path: '/verify-2fa',
      query: { token_2fa: result.token_2fa },
    })
    return
  }

  // Wait a bit for the store to update, then redirect based on role
  await new Promise((resolve) => setTimeout(resolve, 100))

  const role = authStore.userRole
  if (role === 'mantelzorger') {
    await router.push('/mantelzorger/dashboard')
  } else if (role === 'zorgverlener') {
    await router.push('/zorgverlener/dashboard')
  } else if (role === 'patient') {
    await router.push('/home')
  } else {
    await router.push('/home')
  }
} else {
  errorMessage.value = result.message
  $q.notify({
    type: 'negative',
    message: result.message,
    position: 'top',
  })
}

}
</script>
