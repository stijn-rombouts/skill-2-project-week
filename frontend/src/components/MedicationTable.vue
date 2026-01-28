<template>
  <div class="q-pa-md">
    <div class="row items-center q-mb-md">
      <h5 class="q-my-none">Medicatie</h5>
      <q-space />
      <q-btn
        v-if="isCaregiver"
        color="primary"
        label="Medicatie Toevoegen"
        icon="add"
        @click="showAddDialog = true"
      />
    </div>

    <!-- Medications Table -->
    <q-table
      :rows="medications"
      :columns="columns"
      :pagination="pagination"
      row-key="id"
      flat
      bordered
      class="q-mt-md"
      hide-bottom
    >
      <template v-slot:body-cell-is_active="props">
        <q-td :props="props">
          <q-badge
            :color="props.row.is_active ? 'green' : 'grey'"
            :label="props.row.is_active ? 'Actief' : 'Inactief'"
          />
        </q-td>
      </template>

      <template v-slot:body-cell-schedule="props">
        <q-td :props="props">
          <div class="text-caption">
            <div v-for="day in daysOfWeek" :key="day">
              <span v-if="props.row.schedule[day]?.enabled" class="text-weight-bold">
                {{ getDutchDayName(day).substring(0, 3) }}: {{ props.row.schedule[day].times.join(', ') }}
              </span>
            </div>
          </div>
        </q-td>
      </template>

      <template v-slot:body-cell-actions="props">
        <q-td :props="props" v-if="isCaregiver">
          <q-btn
            flat
            dense
            round
            icon="edit"
            color="blue"
            size="sm"
            @click="editMedication(props.row)"
          />
          <q-btn
            flat
            dense
            round
            icon="delete"
            color="red"
            size="sm"
            @click="deleteMedication(props.row.id)"
          />
        </q-td>
      </template>
    </q-table>

    <!-- Add/Edit Dialog -->
    <q-dialog v-model="showAddDialog" @hide="resetForm">
      <q-card style="width: 85%; max-width: 900px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            {{ editingId ? 'Medicatie Bewerken' : 'Medicatie Toevoegen' }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="q-gutter-md">
            <q-input
              v-model="form.name"
              label="Medicatie Naam"
              outlined
              dense
              :rules="[(val) => !!val || 'Naam is verplicht']"
            />
            <q-input
              v-model="form.dosage"
              label="Dosering (bijv. 500mg, 2 tabletten)"
              outlined
              dense
              :rules="[(val) => !!val || 'Dosering is verplicht']"
            />
            
            <!-- Weekly Schedule Section -->
            <div class="text-subtitle2 q-mt-md">Wekelijks Schema</div>
            <div class="row q-gutter-md">
              <!-- Column 1: Monday to Thursday -->
              <div class="col">
                <div class="q-gutter-md">
                  <div v-for="day in daysOfWeek.slice(0, 4)" :key="day" class="q-pa-md bg-grey-2 rounded-borders">
                    <div class="row items-center q-mb-sm">
                      <q-checkbox
                        v-model="form.schedule[day].enabled"
                        :label="getDutchDayName(day)"
                      />
                    </div>
                    
                    <div v-if="form.schedule[day].enabled" class="q-ml-lg q-gutter-md">
                      <div v-for="(time, idx) in form.schedule[day].times" :key="idx" class="row items-center q-gutter-md">
                        <q-input
                          v-model="form.schedule[day].times[idx]"
                          type="time"
                          outlined
                          dense
                          style="min-width: 150px"
                        />
                        <q-btn
                          icon="close"
                          flat
                          round
                          dense
                          color="negative"
                          size="sm"
                          @click="removeTime(day, idx)"
                        />
                      </div>
                      
                      <q-btn
                        icon="add"
                        label="Voeg Tijd Toe"
                        size="sm"
                        color="primary"
                        flat
                        @click="addTime(day)"
                      />
                    </div>
                  </div>
                </div>
              </div>

              <!-- Column 2: Friday to Sunday -->
              <div class="col">
                <div class="q-gutter-md">
                  <div v-for="day in daysOfWeek.slice(4, 7)" :key="day" class="q-pa-md bg-grey-2 rounded-borders">
                    <div class="row items-center q-mb-sm">
                      <q-checkbox
                        v-model="form.schedule[day].enabled"
                        :label="getDutchDayName(day)"
                      />
                    </div>
                    
                    <div v-if="form.schedule[day].enabled" class="q-ml-lg q-gutter-md">
                      <div v-for="(time, idx) in form.schedule[day].times" :key="idx" class="row items-center q-gutter-md">
                        <q-input
                          v-model="form.schedule[day].times[idx]"
                          type="time"
                          outlined
                          dense
                          style="min-width: 150px"
                        />
                        <q-btn
                          icon="close"
                          flat
                          round
                          dense
                          color="negative"
                          size="sm"
                          @click="removeTime(day, idx)"
                        />
                      </div>
                      
                      <q-btn
                        icon="add"
                        label="Voeg Tijd Toe"
                        size="sm"
                        color="primary"
                        flat
                        @click="addTime(day)"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            <q-input
              v-model="form.notes"
              label="Notities (optioneel)"
              outlined
              dense
              type="textarea"
              rows="3"
            />
            <q-checkbox
              v-model="form.is_active"
              label="Actief"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="Annuleren" color="grey" v-close-popup />
          <q-btn
            label="Opslaan"
            color="primary"
            @click="saveMedication"
            :loading="loading"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>

    <!-- Delete Confirmation Dialog -->
    <q-dialog v-model="showDeleteDialog">
      <q-card style="min-width: 300px">
        <q-card-section class="row items-center">
          <q-icon name="warning" color="negative" size="md" class="q-mr-md" />
          <span>Delete this medication?</span>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="Cancel" color="grey" v-close-popup />
          <q-btn
            label="Delete"
            color="negative"
            @click="confirmDelete"
            :loading="deleteLoading"
          />
        </q-card-actions>
      </q-card>
    </q-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from 'boot/axios'
import { useAuthStore } from 'stores/auth-store'

const props = defineProps({
  patientId: {
    type: Number,
    required: true
  }
})

const authStore = useAuthStore()
const medications = ref([])
const showAddDialog = ref(false)
const showDeleteDialog = ref(false)
const loading = ref(false)
const deleteLoading = ref(false)
const editingId = ref(null)
const deletingId = ref(null)

const daysOfWeek = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

const createEmptySchedule = () => {
  const schedule = {}
  daysOfWeek.forEach(day => {
    schedule[day] = {
      enabled: false,
      times: []
    }
  })
  return schedule
}

const form = ref({
  name: '',
  dosage: '',
  notes: '',
  schedule: createEmptySchedule(),
  is_active: true
})

const isCaregiver = computed(() => authStore.userRole === 'mantelzorger')

const columns = computed(() => {
  const cols = [
    {
      name: 'name',
      label: 'Medicatie Naam',
      field: 'name',
      align: 'left'
    },
    {
      name: 'dosage',
      label: 'Dosering',
      field: 'dosage',
      align: 'left'
    },
    {
      name: 'schedule',
      label: 'Schema',
      field: 'schedule',
      align: 'left'
    },
    {
      name: 'notes',
      label: 'Notities',
      field: 'notes',
      align: 'left'
    },
    {
      name: 'is_active',
      label: 'Status',
      field: 'is_active',
      align: 'left'
    }
  ]

  if (isCaregiver.value) {
    cols.push({
      name: 'actions',
      label: 'Acties',
      field: 'actions',
      align: 'center'
    })
  }

  return cols
})

const pagination = ref({
  page: 1,
  rowsPerPage: 50,
})

const fetchMedications = async () => {
  try {
    console.log('Fetching medications for patient:', props.patientId)
    const response = await api.get(`/api/patients/${props.patientId}/medications`)
    console.log('Medications fetched:', response.data)
    medications.value = response.data
  } catch (error) {
    console.error('Error fetching medications:', error)
  }
}

const saveMedication = async () => {
  if (!form.value.name || !form.value.dosage) {
    console.warn('Please fill in all required fields')
    return
  }

  // Check if at least one day is selected
  const hasSchedule = Object.values(form.value.schedule).some(day => day.enabled && day.times.length > 0)
  if (!hasSchedule) {
    console.warn('Please select at least one day and time for the medication')
    return
  }

  if (!props.patientId) {
    console.warn('Please select a patient first')
    return
  }

  loading.value = true
  try {
    if (editingId.value) {
      await api.put(`/api/medications/${editingId.value}`, {
        name: form.value.name,
        dosage: form.value.dosage,
        schedule: form.value.schedule,
        notes: form.value.notes,
        is_active: form.value.is_active
      })
      console.log('Medication updated successfully')
    } else {
      await api.post(`/api/patients/${props.patientId}/medications`, {
        name: form.value.name,
        dosage: form.value.dosage,
        schedule: form.value.schedule,
        notes: form.value.notes
      })
      console.log('Medication added successfully')
    }
    showAddDialog.value = false
    fetchMedications()
  } catch (error) {
    console.error('Error saving medication:', error)
  } finally {
    loading.value = false
  }
}

const editMedication = (medication) => {
  editingId.value = medication.id
  form.value = {
    name: medication.name,
    dosage: medication.dosage,
    schedule: medication.schedule || createEmptySchedule(),
    notes: medication.notes,
    is_active: medication.is_active
  }
  showAddDialog.value = true
}

const deleteMedication = (id) => {
  deletingId.value = id
  showDeleteDialog.value = true
}

const confirmDelete = async () => {
  deleteLoading.value = true
  try {
    await api.delete(`/api/medications/${deletingId.value}`)
    console.log('Medication deleted successfully')
    showDeleteDialog.value = false
    fetchMedications()
  } catch (error) {
    console.error('Error deleting medication:', error)
  } finally {
    deleteLoading.value = false
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    dosage: '',
    notes: '',
    schedule: createEmptySchedule(),
    is_active: true
  }
  editingId.value = null
}

const addTime = (day) => {
  form.value.schedule[day].times.push('09:00')
}

const removeTime = (day, index) => {
  form.value.schedule[day].times.splice(index, 1)
}

const getDutchDayName = (englishDay) => {
  const dutchDays = {
    'Monday': 'Maandag',
    'Tuesday': 'Dinsdag',
    'Wednesday': 'Woensdag',
    'Thursday': 'Donderdag',
    'Friday': 'Vrijdag',
    'Saturday': 'Zaterdag',
    'Sunday': 'Zondag'
  }
  return dutchDays[englishDay] || englishDay
}

onMounted(() => {
  fetchMedications()
})
</script>
