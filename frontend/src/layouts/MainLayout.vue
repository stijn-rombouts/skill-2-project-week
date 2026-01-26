<template>
  <q-layout view="hHh lpR fFf">
    <q-header reveal bordered>
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />

        <q-toolbar-title> Quasar App </q-toolbar-title>

        <div class="q-mr-md" v-if="user">
          <q-chip color="primary" text-color="white" icon="person">
            {{ user.username }} ({{ user.role }})
          </q-chip>
        </div>

        <q-btn v-if="isAuthenticated" flat icon="logout" label="Logout" @click="handleLogout" />
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <!-- Common Links
        <q-item-label header> Navigation </q-item-label>
        <q-item clickable v-ripple to="/home">
          <q-item-section avatar>
            <q-avatar color="teal" text-color="white" icon="home" />
          </q-item-section>
          <q-item-section>Home</q-item-section>
        </q-item> -->

        <!-- Mantelzorger specific links -->
        <template v-if="userRole === 'mantelzorger'">
          <q-item-label header> Mantelzorger </q-item-label>
          <q-item clickable v-ripple to="/mantelzorger/dashboard">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" icon="dashboard" />
            </q-item-section>
            <q-item-section>Dashboard</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/api-data">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" icon="people" />
            </q-item-section>
            <q-item-section>Patient Overview</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/medications">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" icon="medical_information" />
            </q-item-section>
            <q-item-section>Medications</q-item-section>
          </q-item>
        </template>

        <!-- Zorgverlener specific links -->
        <template v-if="userRole === 'zorgverlener'">
          <q-item-label header> Zorgverlener </q-item-label>
          <q-item clickable v-ripple to="/zorgverlener/dashboard">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" icon="dashboard" />
            </q-item-section>
            <q-item-section>Dashboard</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/api-data">
            <q-item-section avatar>
              <q-avatar color="primary" text-color="white" icon="people" />
            </q-item-section>
            <q-item-section>Patient Overview</q-item-section>
          </q-item>
        </template>

        <!-- Patient specific links -->
        <template v-if="userRole === 'patient'">
          <q-item-label header> Patient </q-item-label>
          <q-item clickable v-ripple to="/home">
            <q-item-section avatar>
              <q-avatar color="teal" text-color="white" icon="home" />
            </q-item-section>
            <q-item-section>Home</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/patient/dashboard">
            <q-item-section avatar>
              <q-avatar color="secondary" text-color="white" icon="dashboard" />
            </q-item-section>
            <q-item-section>My Dashboard</q-item-section>
          </q-item>
          <q-item clickable v-ripple to="/capacitor">
            <q-item-section avatar>
              <q-avatar color="secondary" text-color="white" icon="medication" />
            </q-item-section>
            <q-item-section>My Medications</q-item-section>
          </q-item>
        </template>

        <!-- Common test links -->
        <q-item-label header> Development </q-item-label>
        <q-item clickable v-ripple to="/api-data">
          <q-item-section avatar>
            <q-avatar color="teal" text-color="white" icon="webhook" />
          </q-item-section>
          <q-item-section>API Test</q-item-section>
        </q-item>

        <q-item-label header> External Links </q-item-label>
        <EssentialLink title="Docs" caption="quasar.dev" icon="school" link="https://quasar.dev" />
      </q-list>
    </q-drawer>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from 'stores/auth-store'
import EssentialLink from 'components/EssentialLink.vue'

const router = useRouter()
const authStore = useAuthStore()

const leftDrawerOpen = ref(false)

const isAuthenticated = computed(() => authStore.isAuthenticated)
const user = computed(() => authStore.user)
const userRole = computed(() => authStore.userRole)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}

async function handleLogout() {
  await authStore.logout()
  await router.push('/login')
  // Force page reload to clear state
  window.location.reload()
}
</script>
