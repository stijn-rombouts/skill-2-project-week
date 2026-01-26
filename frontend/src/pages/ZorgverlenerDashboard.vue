<template>
  <q-page class="q-pa-md">
    <div class="text-h4 q-mb-md">Zorgverlener Dashboard</div>

    <div class="row q-col-gutter-md">
      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Welcome, {{ username }}</div>
            <div class="text-subtitle2">Role: Zorgverlener</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <p>This is the zorgverlener dashboard. Here you can:</p>
            <ul>
              <li>Monitor patient activities</li>
              <li>View notifications</li>
              <li>Manage care schedules</li>
              <li>Review patient reports</li>
              <li>View patient medication schema</li>
            </ul>
          </q-card-section>
        </q-card>
      </div>

      <div class="col-12 col-md-6">
        <q-card>
          <q-card-section>
            <div class="text-h6">Patient Overview</div>
          </q-card-section>
          <q-separator />
          <q-card-section>
            <q-list bordered separator>
              <q-item>
                <q-item-section>
                  <q-item-label>Active Patients</q-item-label>
                  <q-item-label caption>5 patients under care</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="primary" label="5" />
                </q-item-section>
              </q-item>
              <q-item>
                <q-item-section>
                  <q-item-label>Pending Notifications</q-item-label>
                  <q-item-label caption>Requires attention</q-item-label>
                </q-item-section>
                <q-item-section side>
                  <q-badge color="orange" label="3" />
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
