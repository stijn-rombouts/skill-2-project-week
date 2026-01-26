<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <h4 class="q-my-none">Take Medication</h4>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner color="primary" size="3em" />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center q-pa-md">
      <q-icon name="error" color="negative" size="3em" />
      <p class="text-negative">{{ error }}</p>
      <q-btn color="primary" label="Retry" @click="fetchMedications" />
    </div>

    <!-- No medications to take -->
    <div v-else-if="currentMedications.length === 0" class="text-center q-pa-xl">
      <q-icon name="check_circle" color="positive" size="4em" />
      <h5 class="q-mt-md">No medications to take right now</h5>
      <p class="text-grey-6">Check back later or when you receive a notification</p>
      <p class="text-grey-7 q-mt-md">Current time: {{ currentTime }}</p>
    </div>

    <!-- Medications to take -->
    <div v-else>
      <p class="text-subtitle1 q-mb-md">Time now: {{ currentTime }}</p>
      <q-card v-for="(med, index) in currentMedications" :key="index" class="q-mb-md">
        <q-card-section>
          <div class="row items-center">
            <q-icon name="medication" color="primary" size="2em" class="q-mr-md" />
            <div class="col">
              <div class="text-h6">{{ med.name }}</div>
              <div class="text-subtitle2 text-grey-7">{{ med.dosage }}</div>
              <div class="text-caption text-grey-6">Scheduled at: {{ med.scheduledTime }}</div>
              <div v-if="med.notes" class="text-caption text-grey-8 q-mt-sm">
                <q-icon name="info" size="xs" /> {{ med.notes }}
              </div>
            </div>
            <q-btn
              color="positive"
              icon="check"
              label="Taken"
              @click="markAsTaken(med, index)"
              :loading="med.marking"
            />
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { api } from 'boot/axios'
// import { useQuasar } from 'quasar'

// const $q = useQuasar()

const loading = ref(true)
const error = ref(null)
const medicationSchedule = ref([])
const currentMedications = ref([])
const currentTime = ref('')

onMounted(async () => {
  await fetchMedications()
  updateCurrentTime()
})

function updateCurrentTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false
  })
}

async function fetchMedications() {
  loading.value = true
  error.value = null
  
  try {
    console.log('Fetching medication schedule from API...')
    const response = await api.get('/api/patient_schedule')
    const data = response.data

    console.log('Medication schedule received:', data)

    if (data.medication_schedule && Array.isArray(data.medication_schedule)) {
      medicationSchedule.value = data.medication_schedule
      filterCurrentMedications()
    } else {
      error.value = 'Invalid medication schedule format'
    }
  } catch (err) {
    console.error('Error fetching medication schedule:', err)
    error.value = 'Failed to load medication schedule. Please try again.'
  } finally {
    loading.value = false
  }
}

function filterCurrentMedications() {
  const now = new Date()
  const today = new Date()
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const todayName = dayNames[today.getDay()]
  
  const medications = []
  const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000)
  const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000)

  console.log(`Filtering medications for ${todayName}`)
  console.log(`Time window: ${fiveMinutesAgo.toLocaleTimeString()} to ${fiveMinutesFromNow.toLocaleTimeString()}`)

  for (const medication of medicationSchedule.value) {
    // Check if medication has a schedule for today
    if (medication.schedule && medication.schedule[todayName]) {
      const daySchedule = medication.schedule[todayName]
      
      // Only process if today is enabled
      if (daySchedule.enabled && daySchedule.times && Array.isArray(daySchedule.times)) {
        for (const timeStr of daySchedule.times) {
          // Parse time string (e.g., "08:00" or "14:30")
          const [hours, minutes] = timeStr.split(':').map(Number)
          const scheduledDate = new Date(
            today.getFullYear(), 
            today.getMonth(), 
            today.getDate(), 
            hours, 
            minutes, 
            0
          )

          // Check if the scheduled time is within the 5-minute window
          if (scheduledDate >= fiveMinutesAgo && scheduledDate <= fiveMinutesFromNow) {
            console.log(`Found medication: ${medication.name} at ${timeStr}`)
            medications.push({
              name: medication.name,
              dosage: medication.dosage,
              scheduledTime: timeStr,
              notes: medication.notes || '',
              marking: false
            })
          }
        }
      }
    }
  }

  currentMedications.value = medications
  console.log(`Found ${medications.length} medications to take now`)
}

async function markAsTaken(medication, index) {
  medication.marking = true
  
  try {
    // Call API to record medication intake
    await api.post('/api/medication_intakes', {
      medication_name: medication.name,
      scheduled_time: medication.scheduledTime,
      status: 'taken',
      notes: null
    })
    
    // Remove from the list
    currentMedications.value.splice(index, 1)
  } catch (err) {
    console.error('Error marking medication as taken:', err)
    medication.marking = false
  }
}
</script>
