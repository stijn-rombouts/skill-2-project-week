import { defineBoot } from '#q-app/wrappers'
import { useAuthStore } from 'stores/auth-store'

export default defineBoot(async () => {
  const authStore = useAuthStore()
  await authStore.checkAuth()
})
