<template>
  <div class="q-pa-md">
    <div class="row items-center q-mb-md">
      <h5 class="q-my-none">Medications</h5>
      <q-space />
      <q-btn
        v-if="isCaregiver"
        color="primary"
        label="Add Medication"
        icon="add"
        @click="showAddDialog = true"
      />
    </div>

    <!-- Medications Table -->
    <q-table
      :rows="medications"
      :columns="columns"
      row-key="id"
      flat
      bordered
      class="q-mt-md"
    >
      <template v-slot:body-cell-is_active="props">
        <q-td :props="props">
          <q-badge
            :color="props.row.is_active ? 'green' : 'grey'"
            :label="props.row.is_active ? 'Active' : 'Inactive'"
          />
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
      <q-card style="min-width: 400px">
        <q-card-section class="row items-center q-pb-none">
          <div class="text-h6">
            {{ editingId ? 'Edit Medication' : 'Add Medication' }}
          </div>
          <q-space />
          <q-btn icon="close" flat round dense v-close-popup />
        </q-card-section>

        <q-card-section>
          <div class="q-gutter-md">
            <q-input
              v-model="form.name"
              label="Medication Name"
              outlined
              dense
              :rules="[(val) => !!val || 'Name is required']"
            />
            <q-input
              v-model="form.dosage"
              label="Dosage (e.g., 500mg, 2 tablets)"
              outlined
              dense
              :rules="[(val) => !!val || 'Dosage is required']"
            />
            <q-input
              v-model="form.frequency"
              label="Frequency (e.g., twice daily)"
              outlined
              dense
              :rules="[(val) => !!val || 'Frequency is required']"
            />
            <q-input
              v-model="form.notes"
              label="Notes (optional)"
              outlined
              dense
              type="textarea"
              rows="3"
            />
            <q-checkbox
              v-model="form.is_active"
              label="Active"
            />
          </div>
        </q-card-section>

        <q-card-actions align="right">
          <q-btn label="Cancel" color="grey" v-close-popup />
          <q-btn
            label="Save"
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

const form = ref({
  name: '',
  dosage: '',
  frequency: '',
  notes: '',
  is_active: true
})

const isCaregiver = computed(() => authStore.userRole === 'mantelzorger')

const columns = computed(() => {
  const cols = [
    {
      name: 'name',
      label: 'Medication',
      field: 'name',
      align: 'left'
    },
    {
      name: 'dosage',
      label: 'Dosage',
      field: 'dosage',
      align: 'left'
    },
    {
      name: 'frequency',
      label: 'Frequency',
      field: 'frequency',
      align: 'left'
    },
    {
      name: 'notes',
      label: 'Notes',
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
      label: 'Actions',
      field: 'actions',
      align: 'center'
    })
  }

  return cols
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
  if (!form.value.name || !form.value.dosage || !form.value.frequency) {
    console.warn('Please fill in all required fields')
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
        frequency: form.value.frequency,
        notes: form.value.notes,
        is_active: form.value.is_active
      })
      console.log('Medication updated successfully')
    } else {
      await api.post(`/api/patients/${props.patientId}/medications`, {
        name: form.value.name,
        dosage: form.value.dosage,
        frequency: form.value.frequency,
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
    frequency: medication.frequency,
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
    frequency: '',
    notes: '',
    is_active: true
  }
  editingId.value = null
}

onMounted(() => {
  fetchMedications()
})
</script>
