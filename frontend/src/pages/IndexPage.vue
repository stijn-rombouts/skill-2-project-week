<template>
  <q-page class="flex flex-center column">
    <!-- <img
      alt="Quasar logo"
      src="~assets/quasar-logo-vertical.svg"
      style="width: 200px; height: 200px"
    /> -->

    <div class="q-mt-lg text-center">
      <h3>Patient Home Pagina</h3>
    </div>
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
    <div class="q-mt-lg">
      <q-btn color="secondary" label="Test Notification 2" @click="testNotification2" />
    </div>

    <div v-if="statusMessage" class="q-mt-md text-center">
      {{ statusMessage }}
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { LocalNotifications } from '@capacitor/local-notifications'
import { Capacitor } from '@capacitor/core'
// import { BackgroundRunner } from '@capacitor/background-runner'
import { api } from 'src/boot/axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const isLoading = ref(false)
const isEnabled = ref(false)
const statusMessage = ref('')

let notificationListener = null

onMounted(async () => {
  if (Capacitor.isNativePlatform()) {
    console.log('App mounted on native platform')
    
    // Add listener for notification actions
    notificationListener = await LocalNotifications.addListener(
      'localNotificationActionPerformed',
      (notification) => {
        console.log('Notification action performed:', notification)
        // Check if the notification has the medication action
        if (notification.notification.extra?.action === 'view_medication') {
          router.push('/patient-take-medication')
        }
      }
    )
    
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
      // console.log('Checking BackgroundRunner availability...')
      // const bgCheck = await BackgroundRunner.checkPermissions()
      // console.log('BackgroundRunner check:', bgCheck)
    } catch (error) {
      console.error('Error checking permissions:', error)
    }
  } else {
    console.log('App not running on native platform')
  }
})

onUnmounted(() => {
  // Remove listener when component is unmounted
  if (notificationListener) {
    notificationListener.remove()
  }
})

async function scheduleNotificationsFromAPI() {
  try {
    console.log('Fetching medication schedule from API...')
    const response = await api.get('/api/patient_schedule')
    const data = response.data

    console.log('Medication schedule received:', data)

    if (data.medication_schedule && Array.isArray(data.medication_schedule)) {
      const notifications = []
      const today = new Date()
      const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
      const todayName = dayNames[today.getDay()]

      for (const medication of data.medication_schedule) {
        // Check if medication has a schedule for today
        if (medication.schedule && medication.schedule[todayName]) {
          const daySchedule = medication.schedule[todayName]
          
          // Only process if today is enabled
          if (daySchedule.enabled && daySchedule.times && Array.isArray(daySchedule.times)) {
            for (const timeStr of daySchedule.times) {
              // Parse time string (e.g., "08:00" or "14:30")
              const [hours, minutes] = timeStr.split(':').map(Number)
              const scheduledDate = new Date(today.getFullYear(), today.getMonth(), today.getDate(), hours, minutes, 0)

              // Only schedule if the time is in the future
              if (scheduledDate > new Date()) {
                console.log(`Scheduling notification for ${medication.name} at ${scheduledDate}`)
                notifications.push({
                  id: Math.floor(Math.random() * 1000000),
                  title: 'Medication Reminder',
                  body: `Time to take ${medication.name} - ${medication.dosage}`,
                  schedule: { at: scheduledDate },
                  extra: { action: 'view_medication' },
                })
              }
            }
          }
        }
      }

      if (notifications.length > 0) {
        await LocalNotifications.schedule({ notifications })
        console.log(`Scheduled ${notifications.length} medication notifications for today (${todayName})`)
      } else {
        console.log(`No future medication notifications to schedule for today (${todayName})`)
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

async function testNotification2() {
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
      await LocalNotifications.schedule({
        notifications: [
          {
            id: Math.floor(Math.random() * 10000),
            title: 'Medication Reminder',
            body: 'It\'s time to take your medication! Tap to view details.',
            schedule: { at: new Date(Date.now() + 1000) },
            sound: undefined,
            attachments: undefined,
            actionTypeId: '',
            extra: { action: 'view_medication' },
          },
        ],
      })
      statusMessage.value = 'Medication notification scheduled! It will appear in 1 second.'
      console.log('Medication notification sent with click action')
    } else {
      statusMessage.value = 'Permission denied'
    }
  } catch (error) {
    console.error('Error sending medication notification:', error)
    statusMessage.value = 'Error: ' + error.message
  }
}
</script>
