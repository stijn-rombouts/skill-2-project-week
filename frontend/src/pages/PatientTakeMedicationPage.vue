<template>
  <q-page class="q-pa-md">
    <div class="row items-center q-mb-lg">
      <h4 class="q-my-none">Medicatie Innemen</h4>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="flex flex-center q-pa-xl">
      <q-spinner color="primary" size="3em" />
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="text-center q-pa-md">
      <q-icon name="error" color="negative" size="3em" />
      <p class="text-negative">{{ error }}</p>
      <q-btn color="primary" label="Opnieuw proberen" @click="fetchMedications" />
    </div>

    <!-- No medications to take -->
    <div v-else-if="currentMedications.length === 0" class="text-center q-pa-xl">
      <q-icon name="check_circle" color="positive" size="4em" />
      <h5 class="q-mt-md">Geen medicatie om nu in te nemen</h5>
      <p class="text-grey-6">Kom later terug of wanneer u een melding ontvangt</p>
      <p class="text-grey-7 q-mt-md">Huidige tijd: {{ currentTime }}</p>
    </div>

    <!-- Medications to take -->
    <div v-else>
      <div class="row items-center justify-between q-mb-md">
        <p class="text-subtitle1 q-my-none">Tijd nu: {{ currentTime }}</p>
        <!-- <q-btn
          :color="isListening ? 'negative' : 'primary'"
          :icon="isListening ? 'mic_off' : 'mic'"
          :label="isListening ? 'Stop luisteren' : 'Start spraakherkenning'"
          @click="toggleSpeechRecognition"
          :disable="!speechAvailable"
        /> -->
      </div>
      
      <q-banner v-if="isListening" class="bg-primary text-white q-mb-md">
        <template v-slot:avatar>
          <q-icon name="mic" />
        </template>
        Luisteren naar "medicatie ingenomen"...
      </q-banner>

      <q-card v-for="(med, index) in currentMedications" :key="index" class="q-mb-md">
        <q-card-section>
          <div class="row items-center">
            <q-icon name="medication" color="primary" size="2em" class="q-mr-md" />
            <div class="col">
              <div class="text-h6">{{ med.name }}</div>
              <div class="text-subtitle2 text-grey-7">{{ med.dosage }}</div>
              <div class="text-caption text-grey-6">Gepland om: {{ med.scheduledTime }}</div>
              <div v-if="med.notes" class="text-caption text-grey-8 q-mt-sm">
                <q-icon name="info" size="xs" /> {{ med.notes }}
              </div>
            </div>
            <q-btn
              color="positive"
              icon="check"
              label="Ingenomen"
              @click="markAsTaken(med, index)"
              :loading="med.marking"
            />
          </div>
        </q-card-section>
      </q-card>
    </div>
  </q-page>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from 'boot/axios'
import { TextToSpeech } from '@capacitor-community/text-to-speech'
import { SpeechRecognition } from '@capacitor-community/speech-recognition'
// import { useQuasar } from 'quasar'

// const $q = useQuasar()

const loading = ref(true)
const error = ref(null)
const medicationSchedule = ref([])
const currentMedications = ref([])
const currentTime = ref('')
const isListening = ref(false)
const speechAvailable = ref(false)
let speechTimeoutId = null
let matchFound = ref(false)

// Global handler for SpeechRecognition errors that come as unhandled rejections
const handleUnhandledRejection = async (event) => {
  const errorMsg = (event.reason?.message || event.reason?.toString() || '').toLowerCase()
  console.log('Unhandled rejection caught:', errorMsg)
  
  if (errorMsg.includes("no match") || errorMsg.includes("didn't understand") || errorMsg.includes("client side error")) {
    event.preventDefault() // Prevent the error from being logged to console as unhandled
    console.log('SpeechRecognition error caught via unhandled rejection handler')
    
    // Only handle if we're supposed to be listening and have medications
    if (currentMedications.value.length > 0) {
      isListening.value = false
      
      try {
        await TextToSpeech.speak({
          text: 'Ik heb u niet begrepen. Probeer het opnieuw en zeg medicatie ingenomen.',
          lang: 'nl-BE',
          rate: 1.0,
          pitch: 1.0,
          volume: 1.0,
          category: 'ambient'
        })
        
        if (speechAvailable.value) {
          console.log('Restarting speech recognition from global handler')
          await startSpeechRecognition()
        }
      } catch (ttsErr) {
        console.log('Error with TTS from global handler:', ttsErr)
      }
    }
  }
}

onMounted(async () => {
  // Add global unhandled rejection handler for SpeechRecognition errors
  window.addEventListener('unhandledrejection', handleUnhandledRejection)
  
  await fetchMedications()
  updateCurrentTime()
  await checkSpeechRecognitionAvailability()
})

onUnmounted(() => {
  // Remove global handler
  window.removeEventListener('unhandledrejection', handleUnhandledRejection)
  
  // Stop speech recognition if still listening when leaving the page
  if (isListening.value) {
    stopSpeechRecognition()
  }
})

function updateCurrentTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: false
  })
}

async function fetchMedications() {
  loading.value = true
  error.value = null
  
  try {
    console.log('Fetching medication schedule from API...')
    const response = await api.get('/api/patient_schedule')
    const data = response.data

    console.log('Medication schedule received:', data)

    if (data.medication_schedule && Array.isArray(data.medication_schedule)) {
      medicationSchedule.value = data.medication_schedule
      filterCurrentMedications()
    } else {
      error.value = 'Ongeldig medicatieschema formaat'
    }
  } catch (err) {
    console.log('Error fetching medication schedule:', err)
    error.value = 'Kan medicatieschema niet laden. Probeer het opnieuw.'
  } finally {
    loading.value = false
  }
}

async function filterCurrentMedications() {
  const now = new Date()
  const today = new Date()
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const todayName = dayNames[today.getDay()]
  
  const medications = []
  const fiveMinutesAgo = new Date(now.getTime() - 5 * 60 * 1000)
  const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000)

  console.log(`Filtering medications for ${todayName}`)
  console.log(`Time window: ${fiveMinutesAgo.toLocaleTimeString()} to ${fiveMinutesFromNow.toLocaleTimeString()}`)

  for (const medication of medicationSchedule.value) {
    // Check if medication has a schedule for today
    if (medication.schedule && medication.schedule[todayName]) {
      const daySchedule = medication.schedule[todayName]
      
      // Only process if today is enabled
      if (daySchedule.enabled && daySchedule.times && Array.isArray(daySchedule.times)) {
        for (const timeStr of daySchedule.times) {
          // Parse time string (e.g., "08:00" or "14:30")
          const [hours, minutes] = timeStr.split(':').map(Number)
          const scheduledDate = new Date(
            today.getFullYear(), 
            today.getMonth(), 
            today.getDate(), 
            hours, 
            minutes, 
            0
          )

          // Check if the scheduled time is within the 5-minute window
          if (scheduledDate >= fiveMinutesAgo && scheduledDate <= fiveMinutesFromNow) {
            console.log(`Found medication: ${medication.name} at ${timeStr}`)
            medications.push({
              name: medication.name,
              dosage: medication.dosage,
              scheduledTime: timeStr,
              notes: medication.notes || '',
              marking: false
            })
            
          }
        }
      }
    }
  }

  currentMedications.value = medications
  
  // Speak each medication one by one and start speech recognition after each
  for (const med of medications) {
    await speakMedicationReminder(med.name, med.dosage, med.scheduledTime)
  }
  
  console.log(`Found ${medications.length} medications to take now`)
}

async function speakMedicationReminder(medicationName, dosage, scheduledTime) {
  try {
    const hours = scheduledTime.split(':')[0]
    const minutes = scheduledTime.split(':')[1]
    
    console.log('Speaking medication reminder for:', medicationName)
    console.log(`Het is tijd om uw medicatie in te nemen: ${medicationName}.  Dosering: ${dosage}. Gepland om ${scheduledTime}.`)
    
    await TextToSpeech.speak({
      text: `Het is tijd om uw medicatie in te nemen: ${medicationName}.  Dosering: ${dosage}. Gepland om ${hours} uur en ${minutes} minuten. Zeg medicatie ingenomen als u de medicatie heeft ingenomen.`,
      lang: 'nl-BE',
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0,
      category: 'ambient'
    })
    // await TextToSpeech.speak({
    //   text: `Zeg medicatie ingenomen als u de medicatie heeft ingenomen.`,
    //   lang: 'nl-BE',
    //   rate: 1.0,
    //   pitch: 1.0,
    //   volume: 1.0,
    //   category: 'ambient'
    // })
    
    console.log('TTS finished for:', medicationName)
    
    // Automatically start speech recognition after TTS finishes if available
    if (speechAvailable.value && !isListening.value) {
      console.log('Starting speech recognition automatically after TTS')
      await startSpeechRecognition()
    }
  } catch (err) {
    console.log('Error with text-to-speech:', err)
  }
}

async function markAsTaken(medication, index) {
  medication.marking = true
  
  try {
    // Call API to record medication intake
    await api.post('/api/medication_intakes', {
      medication_name: medication.name,
      scheduled_time: medication.scheduledTime,
      status: 'taken',
      notes: null
    })
    
    // Remove from the list
    currentMedications.value.splice(index, 1)
    
    // $q.notify({
    //   type: 'positive',
    //   message: `${medication.name} gemarkeerd als ingenomen`,
    //   position: 'top'
    // })
    console.log("Gemarkeerd as ingenomen")
  } catch (err) {
    console.log('Error marking medication as taken:', err)
    medication.marking = false
    
    // $q.notify({
    //   type: 'negative',
    //   message: 'Kon medicatie niet markeren als ingenomen',
    //   position: 'top'
    // })
    console.log("Kon medicatie niet markeren als ingenomen")
  }
}

async function checkSpeechRecognitionAvailability() {
  try {
    const { available } = await SpeechRecognition.available()
    speechAvailable.value = available
    
    if (available) {
      // Request permissions
      const { speechRecognition } = await SpeechRecognition.requestPermissions()
      speechAvailable.value = speechRecognition === 'granted'
    }
  } catch (err) {
    console.log('Error checking speech recognition availability:', err)
    speechAvailable.value = false
  }
}

// async function toggleSpeechRecognition() {
//   if (isListening.value) {
//     await stopSpeechRecognition()
//   } else {
//     await startSpeechRecognition()
//   }
// }

async function startSpeechRecognition() {
  try {
    console.log('Starting speech recognition setup...')
    
    // Remove any existing listeners first
    await SpeechRecognition.removeAllListeners()
    console.log('Removed existing listeners')
    
    // Register ALL possible listeners to debug
    await SpeechRecognition.addListener('partialResults', (data) => {
      console.log('*** Partial results event received ***')
      console.log('Partial results data:', JSON.stringify(data))
      console.log('Partial results matches:', data.matches)
      handleSpeechResult(data.matches, false)  // false = not final
    })
    
    await SpeechRecognition.addListener('results', (data) => {
      console.log('*** Final results event received ***')
      console.log('Final results data:', JSON.stringify(data))
      console.log('Final results matches:', data.matches)
      handleSpeechResult(data.matches, true)  // true = final results
    })
    
    await SpeechRecognition.addListener('error', async (error) => {
      console.log('*** Speech recognition error event ***')
      console.log('Speech recognition error:', JSON.stringify(error))
      isListening.value = false
      console.log(`Spraakherkenningfout: ${error.message || 'Unknown error'}`)
      
      // Handle "Didn't understand" or "No match" errors
      const errorMsg = (error.message || '').toLowerCase()
      if (errorMsg.includes("didn't understand") || errorMsg.includes("no match")) {
        console.log('Speech not understood or no match, notifying user...')
        try {
          await TextToSpeech.speak({
            text: 'Ik heb u niet begrepen. Probeer het opnieuw en zeg medicatie ingenomen.',
            lang: 'nl-BE',
            rate: 1.0,
            pitch: 1.0,
            volume: 1.0,
            category: 'ambient'
          })
          
          // Restart speech recognition after TTS finishes if there are still medications to take
          if (currentMedications.value.length > 0 && speechAvailable.value) {
            console.log('Restarting speech recognition after error')
            await startSpeechRecognition()
          }
        } catch (ttsErr) {
          console.log('Error with TTS for speech error:', ttsErr)
        }
      }
    })
    
    await SpeechRecognition.addListener('start', () => {
      console.log('*** Speech recognition START event ***')
    })
    
    await SpeechRecognition.addListener('end', async () => {
      console.log('*** Speech recognition END event ***')
      const wasListening = isListening.value
      isListening.value = false
      
      // If we were listening and there are still medications, this might be an error case
      // Restart after a small delay to allow error handlers to run first
      if (wasListening && currentMedications.value.length > 0 && speechAvailable.value) {
        console.log('Speech recognition ended unexpectedly, restarting after delay...')
        await new Promise(resolve => setTimeout(resolve, 500))
        
        // Check if we haven't already restarted
        if (!isListening.value && currentMedications.value.length > 0) {
          try {
            await TextToSpeech.speak({
              text: 'Ik heb u niet begrepen. Probeer het opnieuw en zeg medicatie ingenomen.',
              lang: 'nl-BE',
              rate: 1.0,
              pitch: 1.0,
              volume: 1.0,
              category: 'ambient'
            })
            console.log('Restarting speech recognition from end handler')
            await startSpeechRecognition()
          } catch (err) {
            console.log('Error restarting from end handler:', err)
          }
        }
      }
    })
    
    // Add listeningState listener - this is fired by the plugin
    await SpeechRecognition.addListener('listeningState', (state) => {
      console.log('*** Listening state changed ***', state)
    })
    
    console.log('Listeners registered')
    isListening.value = true
    matchFound.value = false
    
    // Clear any existing timeout
    if (speechTimeoutId) {
      clearTimeout(speechTimeoutId)
    }
    
    // Set a timeout - if no match found within 8 seconds, retry
    speechTimeoutId = setTimeout(() => {
      console.log('Speech recognition timeout - no match found in time')
      if (!matchFound.value && currentMedications.value.length > 0 && speechAvailable.value) {
        console.log('Timeout triggered, stopping and restarting...')
        handleTimeoutRetry()
      }
    }, 8000)  // 8 second timeout
    
    // Small delay to ensure listeners are registered
    await new Promise(resolve => setTimeout(resolve, 100))
    
    console.log('Starting SpeechRecognition.start()...')
    
    // Use promise with .catch() to handle async errors that come after initial resolve
    // Store the promise so we can catch errors that come later
    const startPromise = SpeechRecognition.start({
      language: 'nl-NL',
      maxResults: 5,
      prompt: 'Zeg "medicatie ingenomen"',
      partialResults: true,
      popup: false
    })
    
    // Handle promise resolution and any later rejections
    startPromise.then((result) => {
      console.log('SpeechRecognition.start() completed successfully')
      console.log('Start result:', JSON.stringify(result))
      console.log("Spraakherkenning gestart. Zeg 'medicatie ingenomen'")
    })
    
    // This catch handles async errors that come after start() initially resolves
    startPromise.catch(async (err) => {
      console.log('SpeechRecognition.start() async error caught:', err)
      console.log('Error message:', err?.message)
      await handleSpeechError(err)
    })
    
  } catch (err) {
    console.log('Error starting speech recognition:', err)
    await handleSpeechError(err)
  }
}

async function handleSpeechError(err) {
  console.log('*** handleSpeechError called ***')
  console.log('Error object:', err)
  console.log('Error message:', err?.message)
  console.log('Error toString:', err?.toString?.())
  
  isListening.value = false
  
  // Handle "No match", "Client side error", or "Didn't understand" errors - retry
  const errorMsg = (err?.message || err?.toString?.() || '').toLowerCase()
  console.log('Error message lowercase:', errorMsg)
  
  if (errorMsg.includes("no match") || errorMsg.includes("client side error") || errorMsg.includes("didn't understand")) {
    console.log('Speech recognition error (no match/client error), notifying user and retrying...')
    try {
      await TextToSpeech.speak({
        text: 'Ik heb u niet begrepen. Probeer het opnieuw en zeg medicatie ingenomen.',
        lang: 'nl-BE',
        rate: 1.0,
        pitch: 1.0,
        volume: 1.0,
        category: 'ambient'
      })
      
      // Restart speech recognition after TTS finishes if there are still medications to take
      if (currentMedications.value.length > 0 && speechAvailable.value) {
        console.log('Restarting speech recognition after error')
        await startSpeechRecognition()
      } else {
        console.log('Not restarting: medications:', currentMedications.value.length, 'speechAvailable:', speechAvailable.value)
      }
    } catch (ttsErr) {
      console.log('Error with TTS for speech error:', ttsErr)
    }
  } else {
    console.log("Kon spraakherkenning niet starten - error not recognized for retry")
  }
}


async function stopSpeechRecognition() {
  try {
    // Clear the timeout
    if (speechTimeoutId) {
      clearTimeout(speechTimeoutId)
      speechTimeoutId = null
    }
    
    await SpeechRecognition.stop()
    isListening.value = false
    
    // Remove all listeners
    await SpeechRecognition.removeAllListeners()
    
    // $q.notify({
    //   type: 'info',
    //   message: 'Spraakherkenning gestopt',
    //   position: 'top'
    // })
    console.log("Spraakherkenning gestopt")
  } catch (err) {
    console.log('Error stopping speech recognition:', err)
  }
}

async function handleTimeoutRetry() {
  console.log('handleTimeoutRetry called')
  isListening.value = false
  
  // Don't await stop - it might hang if speech recognition already stopped
  console.log('Stopping speech recognition (non-blocking)...')
  SpeechRecognition.stop().catch(e => console.log('Stop error (ignored):', e))
  
  // Small delay before TTS
  await new Promise(resolve => setTimeout(resolve, 500))
  
  console.log('Starting TTS...')
  try {
    await TextToSpeech.speak({
      text: 'Ik heb u niet begrepen. Probeer het opnieuw en zeg medicatie ingenomen.',
      lang: 'nl-BE',
      rate: 1.0,
      pitch: 1.0,
      volume: 1.0,
      category: 'ambient'
    })
    console.log('TTS finished')
  } catch (ttsErr) {
    console.log('TTS error (ignored):', ttsErr)
  }
  
  // Check again if we should restart
  if (currentMedications.value.length > 0 && speechAvailable.value) {
    console.log('Restarting speech recognition after timeout')
    try {
      await startSpeechRecognition()
      console.log('Speech recognition restarted successfully')
    } catch (startErr) {
      console.log('Error restarting speech recognition:', startErr)
    }
  } else {
    console.log('Not restarting - no medications or speech not available')
  }
}

async function handleSpeechResult(matches, isFinal = false) {
  console.log('handleSpeechResult called with:', matches, 'isFinal:', isFinal)
  
  if (!matches || matches.length === 0) {
    console.log('No matches found or empty matches array')
    return
  }
  
  // Check if any of the matches contains "medicatie ingenomen" (case insensitive)
  const matchText = matches[0].toLowerCase()
  console.log('First match text (lowercased):', matchText)
  
  if (matchText.includes('medicatie ingenomen') || 
      matchText.includes('medicatie ingenome') ||
      matchText.includes('medicijn ingenomen')) {
    console.log('*** Detected "medicatie ingenomen"! ***')
    
    // Set matchFound to prevent timeout from triggering
    matchFound.value = true
    if (speechTimeoutId) {
      clearTimeout(speechTimeoutId)
      speechTimeoutId = null
    }
    
    // Mark the first medication as taken
    if (currentMedications.value.length > 0) {
      console.log('Marking first medication as taken...')
      const firstMed = currentMedications.value[0]
      markAsTaken(firstMed, 0)
      
      // Stop listening after successful recognition
      stopSpeechRecognition()
      
      // Speak confirmation
      try {
        await TextToSpeech.speak({
          text: 'Medicatie gemarkeerd als ingenomen',
          lang: 'nl-BE',
          rate: 1.0,
          pitch: 1.0,
          volume: 1.0,
          category: 'ambient'
        })
      } catch (err) {
        console.log('Error with TTS confirmation:', err)
      }
    } else {
      console.log('No medications available to mark as taken')
    }
  } else if (isFinal) {
    // Only handle unmatched phrases on final results, not partial results
    console.log('Final result did not match expected phrases, will retry')
    
    // Notify user and restart speech recognition
    if (currentMedications.value.length > 0) {
      try {
        // Stop current recognition first
        await SpeechRecognition.stop()
        isListening.value = false
        
        await TextToSpeech.speak({
          text: 'Ik heb u niet begrepen. Zeg alstublieft medicatie ingenomen.',
          lang: 'nl-BE',
          rate: 1.0,
          pitch: 1.0,
          volume: 1.0,
          category: 'ambient'
        })
        
        // Restart speech recognition after TTS
        if (speechAvailable.value) {
          console.log('Restarting speech recognition after unmatched phrase')
          await startSpeechRecognition()
        }
      } catch (err) {
        console.log('Error handling unmatched phrase:', err)
      }
    }
  } else {
    console.log('Partial result did not match, waiting for final result...')
  }
}
</script>
