<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <h4 class="q-my-none">Patient Medications</h4>
      <q-space />
      <q-btn
        v-if="selectedPatient"
        icon="download"
        label="Export as PDF"
        color="primary"
        @click="exportToPDF"
        class="q-mr-md"
      />
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
      ref="medicationTableRef"
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
import jsPDF from 'jspdf'
import 'jspdf-autotable'

const authStore = useAuthStore()
const patients = ref([])
const selectedPatient = ref(null)
const medicationTableRef = ref(null)

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

const formatSchedule = (schedule) => {
  const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  const scheduledDays = []
  
  daysOfWeek.forEach(day => {
    if (schedule[day]?.enabled && schedule[day].times.length > 0) {
      scheduledDays.push(`${day}: ${schedule[day].times.join(', ')}`)
    }
  })
  
  return scheduledDays.length > 0 ? scheduledDays.join('\n') : 'No schedule'
}

const exportToPDF = async () => {
  if (!selectedPatient.value) {
    console.warn('Please select a patient first')
    return
  }

  try {
    // Fetch medications for the selected patient
    const response = await api.get(`/api/patients/${selectedPatient.value.id}/medications`)
    const medications = response.data

    // Create PDF document
    const pdf = new jsPDF()
    
    // Add title
    pdf.setFontSize(16)
    pdf.text('MEDICATION PRESCRIPTION', 20, 20)
    
    // Add patient info
    pdf.setFontSize(11)
    pdf.text(`Patient: ${selectedPatient.value.username}`, 20, 35)
    pdf.text(`Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}`, 20, 42)
    
    // Create table data
    const tableData = medications.map(med => [
      med.name,
      med.dosage,
      formatSchedule(med.schedule),
      med.notes || '-',
      med.is_active ? 'Active' : 'Inactive'
    ])

    // Add table
    pdf.autoTable({
      head: [['Medication', 'Dosage', 'Schedule', 'Notes', 'Status']],
      body: tableData,
      startY: 50,
      theme: 'grid',
      headStyles: {
        fillColor: [41, 128, 185],
        textColor: 255,
        fontStyle: 'bold'
      },
      bodyStyles: {
        textColor: 0,
        overflow: 'linebreak'
      },
      columnStyles: {
        0: { cellWidth: 35 },
        1: { cellWidth: 30 },
        2: { cellWidth: 50 },
        3: { cellWidth: 40 },
        4: { cellWidth: 20 }
      },
      margin: { top: 50 }
    })

    // Save PDF
    pdf.save(`${selectedPatient.value.username}_medications.pdf`)
    console.log('PDF exported successfully')
  } catch (error) {
    console.error('Error exporting to PDF:', error)
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
