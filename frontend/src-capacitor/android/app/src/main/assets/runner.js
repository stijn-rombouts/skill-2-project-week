addEventListener('notificationLoop', (resolve, reject) => {
  try {
    // Get current time
    const now = new Date()
    const timeString = now.toLocaleTimeString()

    // Generate a unique notification ID
    const notificationId = Math.floor(Math.random() * 10000)

    // Use the correct API for background runner context
    // In background runner, we use the global CapacitorNotifications object
    CapacitorNotifications.schedule({
      notifications: [
        {
          id: notificationId,
          title: 'Background Task Running',
          body: `Notification at ${timeString}`,
        },
      ],
    })

    // Log to system logs (use adb logcat to see these)
    console.log(`Background notification sent at ${timeString}, ID: ${notificationId}`)

    resolve()
  } catch (error) {
    console.error('Error in background task:', error)
    reject(error)
  }
})
