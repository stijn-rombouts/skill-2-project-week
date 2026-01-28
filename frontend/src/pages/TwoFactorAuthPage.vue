<template>
  <div class="q-pa-md" style="max-width: 600px; margin: 0 auto">
    <q-card>
      <q-card-section>
        <div class="text-h6">Two-Factor Authentication (2FA)</div>
        <div class="text-caption text-grey-7">Secure your account with time-based authentication</div>
      </q-card-section>

      <q-separator />

      <!-- Current Status -->
      <q-card-section>
        <div class="row items-center q-gutter-md">
          <div v-if="is2faEnabled" class="col">
            <q-chip color="positive" text-color="white" icon="check">
              2FA is <strong>ENABLED</strong>
            </q-chip>
          </div>
          <div v-else class="col">
            <q-chip color="warning" text-color="white" icon="warning">
              2FA is <strong>DISABLED</strong>
            </q-chip>
          </div>
        </div>
      </q-card-section>

      <!-- Setup 2FA Section -->
      <q-card-section v-if="!is2faEnabled" class="q-gutter-md">
        <div class="text-subtitle2">Enable Two-Factor Authentication</div>

        <q-stepper v-model="setupStep" ref="stepper" color="primary" animated>
          <!-- Step 1: Generate Secret -->
          <q-step :name="1" title="Generate Secret" :done="setupStep > 1">
            <div class="text-caption q-mb-md">
              Click the button below to generate your TOTP secret.
            </div>

            <q-btn
              label="Generate 2FA Secret"
              color="primary"
              @click="generateSecret"
              :loading="loadingGenerate"
              class="full-width"
            />

            <div v-if="errorMessage" class="q-mt-md text-negative">{{ errorMessage }}</div>
          </q-step>

          <!-- Step 2: Scan QR Code -->
          <q-step
            :name="2"
            title="Scan QR Code"
            :done="setupStep > 2"
            :disable="!secret"
          >
            <div class="text-caption q-mb-md">
              Use Google Authenticator, Microsoft Authenticator, Authy, or any TOTP app to scan this QR code: 
            </div>

            <div class="text-center q-mb-md">
              <canvas
                ref="qrCodeCanvas"
                style="max-width: 300px; border: 2px solid #ddd; padding: 10px; display: block; margin: 0 auto"
              />
            </div>

            <div class="bg-grey-2 q-pa-md q-mb-md rounded-borders">
              <div class="text-caption text-weight-bold">Manual Entry (if QR not working):</div>
              <div class="text-monospace q-mt-sm">{{ secret }}</div>
              <q-btn
                flat
                size="sm"
                icon="content_copy"
                @click="copyToClipboard(secret)"
                class="q-mt-sm"
              />
            </div>

            <q-timeline color="primary">
              <q-timeline-entry
                title="Step 1"
                subtitle="Download authenticator app"
                icon="download"
              />
              <q-timeline-entry
                title="Step 2"
                subtitle="Scan QR code or enter secret manually"
                icon="qr_code"
              />
              <q-timeline-entry
                title="Step 3"
                subtitle="Enter the 6-digit code below"
                icon="numbers"
              />
            </q-timeline>

            <div class="q-mt-md">
              <q-btn
                label="Next: Verify Code"
                color="primary"
                @click="setupStep = 3"
                class="full-width"
              />
            </div>
          </q-step>

          <!-- Step 3: Verify Code -->
          <q-step
            :name="3"
            title="Verify Code"
            :disable="!secret"
          >
            <div class="text-caption q-mb-md">
              Enter the 6-digit code from your authenticator app:
            </div>

            <q-input
              v-model="verificationCode"
              label="6-Digit Code"
              outlined
              maxlength="6"
              input-class="text-center text-h6"
              @keyup.enter="verifyAndEnable2FA"
              :disable="loadingVerify"
            />

            <div v-if="verifyErrorMessage" class="q-mt-md text-negative">
              {{ verifyErrorMessage }}
            </div>

            <q-btn
              label="Verify & Enable 2FA"
              color="positive"
              @click="verifyAndEnable2FA"
              :loading="loadingVerify"
              class="full-width q-mt-md"
            />
          </q-step>
        </q-stepper>

        <q-linear-progress
          v-if="loadingGenerate || loadingVerify"
          indeterminate
          color="primary"
          class="q-mt-md"
        />

        <div v-if="errorMessage" class="q-mt-md text-negative">{{ errorMessage }}</div>
      </q-card-section>

      <!-- Disable 2FA Section -->
      <q-card-section v-else class="q-gutter-md">
        <div class="text-subtitle2">Disable Two-Factor Authentication</div>

        <q-expansion-item
          icon="security"
          label="Disable 2FA"
          header-class="text-negative"
        >
          <div class="q-pa-md bg-negative-1 rounded-borders">
            <div class="text-caption q-mb-md">
              To disable 2FA, enter the 6-digit code from your authenticator app:
            </div>

            <q-input
              v-model="disableCode"
              label="6-Digit Code"
              outlined
              maxlength="6"
              input-class="text-center text-h6"
              @keyup.enter="disable2FA"
              :disable="loadingDisable"
            />

            <div v-if="disableErrorMessage" class="q-mt-md text-negative">
              {{ disableErrorMessage }}
            </div>

            <div class="row q-gutter-md q-mt-md">
              <q-btn
                label="Cancel"
                flat
                @click="disableCode = ''"
                class="col"
              />
              <q-btn
                label="Disable 2FA"
                color="negative"
                @click="disable2FA"
                :loading="loadingDisable"
                class="col"
              />
            </div>
          </div>
        </q-expansion-item>
      </q-card-section>

      <!-- Success Message -->
      <q-card-section v-if="successMessage" class="bg-positive-1 text-positive">
        <q-icon name="check_circle" />
        {{ successMessage }}
      </q-card-section>

      <!-- Info Section -->
      <q-separator />
      <q-card-section>
        <div class="text-subtitle2 q-mb-md">About 2FA</div>
        <div class="text-caption text-grey-7">
          <p>
            Two-Factor Authentication adds an extra layer of security to your account.
            Even if someone has your password, they won't be able to access your account
            without the code from your authenticator app.
          </p>
          <p class="q-mt-md">
            <strong>Recommended authenticator apps:</strong>
          </p>
          <ul>
            <li>Google Authenticator</li>
            <li>Microsoft Authenticator</li>
            <li>Authy</li>
            <li>FreeOTP</li>
          </ul>
        </div>
      </q-card-section>
    </q-card>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useQuasar } from 'quasar'
import { api } from 'boot/axios'
import QRCode from 'qrcode'

const $q = useQuasar()

// UI State
const setupStep = ref(1)
const is2faEnabled = ref(false)

// Generation
const secret = ref('')
const qrCodeCanvas = ref(null)
const loadingGenerate = ref(false)
const errorMessage = ref('')

// Verification
const verificationCode = ref('')
const loadingVerify = ref(false)
const verifyErrorMessage = ref('')

// Disable
const disableCode = ref('')
const loadingDisable = ref(false)
const disableErrorMessage = ref('')

// Messages
const successMessage = ref('')

// Check if 2FA is already enabled
onMounted(async () => {
  try {
    const response = await api.get('/api/me')
    // Assume backend returns is_2fa_enabled field
    is2faEnabled.value = response.data.is_2fa_enabled || false
  } catch (error) {
    console.error('Error checking 2FA status:', error)
  }
})

const generateSecret = async () => {
  loadingGenerate.value = true
  errorMessage.value = ''

  try {
    const response = await api.get('/api/2fa/enable')
    secret.value = response.data.secret
    const provisioning_uri = response.data.provisioning_uri

    // Move to step 2 first to render canvas
    setupStep.value = 2
    
    // Wait for canvas to be rendered
    await nextTick()

    // Generate QR code on canvas
    await QRCode.toCanvas(qrCodeCanvas.value, provisioning_uri, {
      errorCorrectionLevel: 'H',
      type: 'image/png',
      quality: 0.95,
      margin: 1,
      width: 300,
      color: {
        dark: '#000',
        light: '#FFF'
      }
    })
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Failed to generate secret'
    console.error('Error generating secret:', error)
  } finally {
    loadingGenerate.value = false
  }
}

const verifyAndEnable2FA = async () => {
  if (!verificationCode.value || verificationCode.value.length !== 6) {
    verifyErrorMessage.value = 'Please enter a 6-digit code'
    return
  }

  loadingVerify.value = true
  verifyErrorMessage.value = ''

  try {
    await api.post('/api/2fa/verify-setup', {
      code: verificationCode.value,
      secret: secret.value
    })

    is2faEnabled.value = true
    successMessage.value = '✅ 2FA has been successfully enabled!'
    verificationCode.value = ''
    secret.value = ''
    qrCodeCanvas.value = null
    setupStep.value = 1

    // Clear success message after 5 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 5000)
  } catch (error) {
    verifyErrorMessage.value = error.response?.data?.detail || 'Invalid code. Please try again.'
    console.error('Error verifying code:', error)
  } finally {
    loadingVerify.value = false
  }
}

const disable2FA = async () => {
  if (!disableCode.value || disableCode.value.length !== 6) {
    disableErrorMessage.value = 'Please enter a 6-digit code'
    return
  }

  loadingDisable.value = true
  disableErrorMessage.value = ''

  try {
    await api.post('/api/2fa/disable', {
      code: disableCode.value
    })

    is2faEnabled.value = false
    successMessage.value = '✅ 2FA has been successfully disabled.'
    disableCode.value = ''

    // Clear success message after 5 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 5000)
  } catch (error) {
    disableErrorMessage.value = error.response?.data?.detail || 'Invalid code. Please try again.'
    console.error('Error disabling 2FA:', error)
  } finally {
    loadingDisable.value = false
  }
}

const copyToClipboard = (text) => {
  navigator.clipboard.writeText(text)
  $q.notify({
    type: 'positive',
    message: 'Copied to clipboard!',
    position: 'top'
  })
}
</script>

<style scoped>
.rounded-borders {
  border-radius: 4px;
}
</style>
