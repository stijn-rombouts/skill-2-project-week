<template>
  <q-page class="flex flex-center column">
    <img
      alt="Quasar logo"
      src="~assets/quasar-logo-vertical.svg"
      style="width: 200px; height: 200px"
    />

    <div class="q-mt-lg">
      <q-btn
        color="primary"
        label="Enable Notifications"
        @click="enableNotifications"
        :loading="isLoading"
        :disable="isEnabled"
      />
    </div>
    <div class="q-mt-lg">
      <q-btn color="secondary" label="Test Notification Now" @click="testNotification" />
    </div>

    <div v-if="statusMessage" class="q-mt-md text-center">
      {{ statusMessage }}
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { LocalNotifications } from '@capacitor/local-notifications'
import { Capacitor } from '@capacitor/core'
import { BackgroundRunner } from '@capacitor/background-runner'

const isLoading = ref(false)
const isEnabled = ref(false)
const statusMessage = ref('')

onMounted(async () => {
  if (Capacitor.isNativePlatform()) {
    console.log('App mounted on native platform')
    // Check if permissions are already granted
    try {
      const permission = await LocalNotifications.checkPermissions()
      console.log('Notification permission status:', permission)
      if (permission.display === 'granted') {
        // Cancel all previously scheduled notifications
        try {
          const pending = await LocalNotifications.getPending()
          console.log(`Canceling ${pending.notifications.length} pending notifications`)
          if (pending.notifications.length > 0) {
            await LocalNotifications.cancel({ notifications: pending.notifications })
          }
        } catch (cancelError) {
          console.error('Error canceling old notifications:', cancelError)
        }

        // Fetch schedule and schedule notifications
        await scheduleNotificationsFromAPI()
        statusMessage.value = 'Notifications scheduled successfully!'
      } else {
        statusMessage.value = 'Click "Enable" to grant permissions and start notifications.'
      }

      // Check if BackgroundRunner is available
      console.log('Checking BackgroundRunner availability...')
      const bgCheck = await BackgroundRunner.checkPermissions()
      console.log('BackgroundRunner check:', bgCheck)
    } catch (error) {
      console.error('Error checking permissions:', error)
    }
  } else {
    console.log('App not running on native platform')
  }
})

async function scheduleNotificationsFromAPI() {
  try {
    console.log('Fetching notification schedule from API...')
    const response = await fetch('http://172.16.222.33:8000/api/schedule_notification')
    const data = await response.json()

    console.log('Schedule received:', data)

    if (data.schedule && Array.isArray(data.schedule)) {
      const notifications = []

      for (const item of data.schedule) {
        // Parse ISO timestamp from API
        const scheduledDate = new Date(item.timestamp)

        // Only schedule if the time is in the future
        if (scheduledDate > new Date()) {
          notifications.push({
            id: Math.floor(Math.random() * 1000000),
            title: 'Scheduled Notification',
            body: item.message,
            schedule: { at: scheduledDate },
          })
        }
      }

      if (notifications.length > 0) {
        await LocalNotifications.schedule({ notifications })
        console.log(`Scheduled ${notifications.length} notifications`)
      } else {
        console.log('No future notifications to schedule for today')
      }
    }
  } catch (error) {
    console.error('Error scheduling notifications from API:', error)
  }
}

async function enableNotifications() {
  if (!Capacitor.isNativePlatform()) {
    statusMessage.value = 'Notifications only work on mobile devices'
    return
  }

  isLoading.value = true

  try {
    // Request permission for notifications
    const permission = await LocalNotifications.requestPermissions()

    if (permission.display === 'granted') {
      // Fetch schedule and schedule notifications
      await scheduleNotificationsFromAPI()
      statusMessage.value = 'Notifications scheduled successfully!'
      isEnabled.value = true
    } else {
      statusMessage.value = 'Notification permission denied. Please enable it in settings.'
    }
  } catch (error) {
    console.error('Error enabling notifications:', error)
    statusMessage.value = 'Error enabling notifications: ' + error.message
  } finally {
    isLoading.value = false
  }
}

async function testNotification() {
  if (!Capacitor.isNativePlatform()) {
    statusMessage.value = 'Notifications only work on mobile devices'
    return
  }

  try {
    // Check/request permission first
    let permission = await LocalNotifications.checkPermissions()
    if (permission.display !== 'granted') {
      permission = await LocalNotifications.requestPermissions()
    }

    if (permission.display === 'granted') {
      const now = new Date()
      await LocalNotifications.schedule({
        notifications: [
          {
            id: Math.floor(Math.random() * 10000),
            title: 'Test Notification',
            body: `Sent at ${now.toLocaleTimeString()}`,
            schedule: { at: new Date(Date.now() + 1000) },
            sound: undefined,
            attachments: undefined,
            actionTypeId: '',
            extra: null,
          },
        ],
      })
      statusMessage.value = 'Test notification scheduled!'
      console.log('Test notification sent')
    } else {
      statusMessage.value = 'Permission denied'
    }
  } catch (error) {
    console.error('Error sending test notification:', error)
    statusMessage.value = 'Error: ' + error.message
  }
}
</script>
