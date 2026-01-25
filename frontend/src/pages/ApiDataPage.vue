<template>
  <q-page class="q-pa-md">
      <h3>API Data Page</h3>
      <q-btn color="primary" icon="check" label="Fetch Data" @click="onClick" :loading="loading" />
      <div v-if="data" class="q-mt-md">
        <q-card>
          <q-card-section>
            <div class="text-h6">Response from API:</div>
            <pre>{{ data }}</pre>
          </q-card-section>
        </q-card>
      </div>
      <div v-if="error" class="q-mt-md text-negative">
        Error: {{ error }}
      </div>
  </q-page>
</template>

<script setup>
import { ref } from 'vue'
import { api } from 'boot/axios'

const data = ref(null)
const error = ref(null)
const loading = ref(false)

async function onClick() {
  loading.value = true
  error.value = null
  try {
    console.log(api)
    const response = await api.get('/')
    data.value = response.data
    console.log('API Response:', response.data)
  } catch (err) {
    error.value = err.message
    console.error('API Error:', err)
  } finally {
    loading.value = false
  }
}
</script>
