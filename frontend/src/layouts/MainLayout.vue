<template>
  <q-layout view="hHh lpR fFf">
    <q-header reveal bordered>
      <q-toolbar>
        <q-btn flat dense round icon="menu" aria-label="Menu" @click="toggleLeftDrawer" />

        <q-toolbar-title> Quasar App </q-toolbar-title>

        <div>Quasar v{{ $q.version }}</div>
      </q-toolbar>
    </q-header>

    <q-drawer v-model="leftDrawerOpen" show-if-above bordered>
      <q-list>
        <q-item-label header> Internal Links </q-item-label>
        <q-item clickable v-ripple to="/home">
          <q-item-section avatar>
            <q-avatar color="teal" text-color="white" icon="home" />
          </q-item-section>
          <q-item-section>Home</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/api-data">
          <q-item-section avatar>
            <q-avatar color="teal" text-color="white" icon="webhook" />
          </q-item-section>
          <q-item-section>API Test</q-item-section>
        </q-item>
        <q-item clickable v-ripple to="/capacitor">
          <q-item-section avatar>
            <q-avatar color="teal" text-color="white" icon="webhook" />
          </q-item-section>
          <q-item-section>Capacitor Test</q-item-section>
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
import { ref } from 'vue'
import EssentialLink from 'components/EssentialLink.vue'

const leftDrawerOpen = ref(false)

function toggleLeftDrawer() {
  leftDrawerOpen.value = !leftDrawerOpen.value
}
</script>
