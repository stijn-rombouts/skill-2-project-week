<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <h4 class="q-my-none">Patient Medications</h4>
      <q-space />
      <q-select
        v-model="selectedPatient"
        :options="patients"
        option-value="id"
        option-label="username"
        label="Select Patient"
        outlined
        dense
        style="min-width: 200px"
        @update:model-value="onPatientChange"
      />
    </div>

    <MedicationTable
      v-if="selectedPatient"
      :key="selectedPatient.id"
      :patientId="selectedPatient.id"
    />
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from 'boot/axios'
import MedicationTable from 'components/MedicationTable.vue'
import { useAuthStore } from 'stores/auth-store'

const authStore = useAuthStore()
const patients = ref([])
const selectedPatient = ref(null)

const fetchPatients = async () => {
  try {
    const response = await api.get('/api/patients')
    patients.value = response.data
    if (patients.value.length > 0) {
      selectedPatient.value = patients.value[0]
    } else {
      console.warn('No patients found. Please create a patient account first.')
    }
  } catch (error) {
    console.error('Error fetching patients:', error)
  }
}

const onPatientChange = () => {
  // Component will re-render when selectedPatient changes
}

onMounted(() => {
  if (authStore.userRole !== 'mantelzorger') {
    console.warn('Only caregivers can access this page')
  }
  fetchPatients()
})
</script>
