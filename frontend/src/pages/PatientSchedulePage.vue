<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Mijn Medicatie Schema</div>
    
    <div class="row q-col-gutter-md">
      <div class="col">
        <q-card>
          <q-card-section>
            <div class="text-h6">Welkom, {{ username }}</div>
            <div class="text-subtitle2">Rol: Patiënt</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <div v-if="medicationSchedule.length === 0" class="text-grey-6 q-pa-md">
              Geen medicatie schema beschikbaar
            </div>
            <div v-else>
              <template v-for="(daySchedule, dutchDay) in groupedByDay" :key="dutchDay">
                <div v-if="daySchedule.length > 0">
                  <div class="text-h6 q-mt-md q-mb-sm text-primary">{{ dutchDay }}</div>
                  <q-list bordered separator>
                    <q-item v-for="item in daySchedule" :key="`${item.medication.name}-${item.time}`">
                      <q-item-section avatar>
                        <q-icon name="medication" color="primary" />
                      </q-item-section>
                      <q-item-section>
                        <q-item-label><strong>{{ item.medication.name }}</strong> - {{ item.medication.dosage }}</q-item-label>
                        <q-item-label caption>{{ item.time }}</q-item-label>
                        <q-item-label caption v-if="item.medication.notes" class="text-grey-7 q-mt-xs">{{ item.medication.notes }}</q-item-label>
                      </q-item-section>
                    </q-item>
                  </q-list>
                </div>
              </template>
            </div>
          </q-card-section>
        </q-card>
      </div>

      <!-- <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Vandaag's Schema</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <q-list bordered separator>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="medication" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Morning Medication</q-item-label>
                  <q-item-label caption>8:00 AM</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="positive" label="Done" />
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="medication" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Afternoon Medication</q-item-label>
                  <q-item-label caption>2:00 PM</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="orange" label="Pending" />
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section avatar>
                  <q-icon name="fitness_center" color="primary" />
                </q-item-section>
                <q-item-section>
                  <q-item-label>Exercise</q-item-label>
                  <q-item-label caption>4:00 PM</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="grey" label="Upcoming" />
                </q-item-section>
              </q-item>
            </q-list>
          </q-card-section>
        </q-card>
      </div> -->
    </div>
  </q-page>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useAuthStore } from 'stores/auth-store'
import { api } from 'boot/axios'

const authStore = useAuthStore()
const username = computed(() => authStore.user?.username || 'User')
const medicationSchedule = ref([])

const dayTranslations = {
  'Monday': 'Maandag',
  'Tuesday': 'Dinsdag',
  'Wednesday': 'Woensdag',
  'Thursday': 'Donderdag',
  'Friday': 'Vrijdag',
  'Saturday': 'Zaterdag',
  'Sunday': 'Zondag'
}

const dayOrder = ['Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag', 'Zondag']

const groupedByDay = computed(() => {
  const groups = {}
  
  // Initialize all days
  dayOrder.forEach(day => {
    groups[day] = []
  })
  
  // Group medications by day
  medicationSchedule.value.forEach(medication => {
    Object.entries(medication.schedule).forEach(([englishDay, dayData]) => {
      const dutchDay = dayTranslations[englishDay]
      if (dayData.enabled && dayData.times.length > 0 && dutchDay) {
        dayData.times.forEach(time => {
          groups[dutchDay].push({
            medication,
            time
          })
        })
      }
    })
  })
  
  // Sort times within each day
  Object.keys(groups).forEach(day => {
    groups[day].sort((a, b) => {
      const timeA = a.time.split(':').map(Number)
      const timeB = b.time.split(':').map(Number)
      return timeA[0] - timeB[0] || timeA[1] - timeB[1]
    })
  })
  
  return groups
})

const fetchSchedule = async () => {
  try {
    const response = await api.get('/api/patient_schedule')
    medicationSchedule.value = response.data.medication_schedule || []
  } catch (error) {
    console.error('Error fetching schedule:', error)
    medicationSchedule.value = []
  }
}

onMounted(() => {
  fetchSchedule()
})
</script>
