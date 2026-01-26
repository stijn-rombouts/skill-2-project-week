<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Patient Dashboard</div>
    
    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Welcome, {{ username }}</div>
            <div class="text-subtitle2">Role: Patient</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <p>This is your personal dashboard. Here you can:</p>
            <ul>
              <li>View your health status</li>
              <li>Check medication reminders</li>
              <li>Contact your caregiver</li>
              <li>Track your activities</li>
            </ul>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Today's Schedule</div>
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
      </div>
    </div>
  </q-page>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from 'stores/auth-store'

const authStore = useAuthStore()
const username = computed(() => authStore.user?.username || 'User')
</script>
