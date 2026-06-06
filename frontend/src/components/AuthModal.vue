<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '../stores/useUserStore'
import { X } from 'lucide-vue-next'

const userStore = useUserStore()
const { t } = useI18n()

const tab = ref<'login' | 'register' | 'local'>('login')
const username = ref('')
const password = ref('')
const email = ref('')
const displayName = ref('')
const error = ref('')
const loading = ref(false)
const selectedLocalAccount = ref('')

// Load local accounts on mount if in Tauri mode.
onMounted(() => {
  if (userStore.isTauriMode) {
    userStore.loadLocalAccounts()
  }
})

function switchTab(t: 'login' | 'register' | 'local') {
  tab.value = t
  error.value = ''
}

async function handleLogin() {
  error.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = 'Please enter both username and password'
    return
  }
  loading.value = true
  try {
    await userStore.login(username.value, password.value)
    close()
  } catch (e: any) {
    error.value = (e as any).userMessage || 'Login failed'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  error.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = 'Username and password are required'
    return
  }
  if (password.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }
  if (!email.value.trim() || !email.value.includes('@')) {
    error.value = 'Please enter a valid email address'
    return
  }
  if (!displayName.value.trim()) {
    error.value = 'Display name is required'
    return
  }
  loading.value = true
  try {
    await userStore.register(username.value, password.value, email.value, displayName.value)
    close()
  } catch (e: any) {
    error.value = (e as any).userMessage || 'Registration failed'
  } finally {
    loading.value = false
  }
}

async function handleLocalLogin() {
  error.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = 'Please enter both username and password'
    return
  }
  loading.value = true
  try {
    await userStore.loginLocal(username.value, password.value)
    close()
  } catch (e: any) {
    error.value = e.message || 'Local login failed'
  } finally {
    loading.value = false
  }
}

async function handleLocalRegister() {
  error.value = ''
  if (!username.value.trim() || !password.value.trim()) {
    error.value = 'Username and password are required'
    return
  }
  if (password.value.length < 6) {
    error.value = 'Password must be at least 6 characters'
    return
  }
  loading.value = true
  try {
    await userStore.registerLocal(
      username.value,
      password.value,
      email.value || '',
      displayName.value || username.value,
    )
    close()
  } catch (e: any) {
    error.value = e.message || 'Local registration failed'
  } finally {
    loading.value = false
  }
}

function switchLocalAccount() {
  if (!selectedLocalAccount.value) return
  const acct = userStore.localAccounts.find((a) => a.id === selectedLocalAccount.value)
  if (acct) {
    username.value = acct.username
    tab.value = 'local'
  }
}

function close() {
  userStore.showAuthModal = false
  error.value = ''
}

function onOverlayClick(e: MouseEvent) {
  if ((e.target as HTMLElement).classList.contains('modal-overlay')) {
    close()
  }
}
</script>

<template>
  <Teleport to="body">
    <div
      v-if="userStore.showAuthModal"
      class="modal-overlay fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      @click="onOverlayClick"
    >
      <div class="w-full max-w-sm bg-card border border-divider rounded-xl shadow-2xl p-6 animate-fade-in">
        <!-- Tab switcher -->
        <div class="flex items-center justify-between mb-5">
          <div class="flex gap-4">
            <button
              class="text-sm font-semibold pb-1 border-b-2 transition-colors"
              :class="tab === 'login'
                ? 'text-ink border-accent'
                : 'text-ink-muted border-transparent hover:text-ink'"
              @click="switchTab('login')"
            >
              Log In
            </button>
            <button
              v-if="userStore.isTauriMode"
              class="text-sm font-semibold pb-1 border-b-2 transition-colors"
              :class="tab === 'local'
                ? 'text-ink border-accent'
                : 'text-ink-muted border-transparent hover:text-ink'"
              @click="switchTab('local')"
            >
              Local
            </button>
            <button
              class="text-sm font-semibold pb-1 border-b-2 transition-colors"
              :class="tab === 'register'
                ? 'text-ink border-accent'
                : 'text-ink-muted border-transparent hover:text-ink'"
              @click="switchTab('register')"
            >
              Create Account
            </button>
          </div>
          <button
            class="flex items-center justify-center w-6 h-6 rounded text-ink-muted hover:text-ink hover:bg-[#21262d] transition-colors"
            @click="close"
          >
            <X class="w-4 h-4" stroke-width="2" />
          </button>
        </div>

        <!-- Login form -->
        <form v-if="tab === 'login'" @submit.prevent="handleLogin" class="space-y-3">
          <input
            v-model="username"
            type="text"
            :placeholder="t('auth.username')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="password"
            type="password"
            :placeholder="t('auth.password')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <p v-if="error" class="text-xs text-[#d73a49]">{{ error }}</p>
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2 text-sm font-semibold bg-accent text-[#0d1117] rounded-lg hover:brightness-110 transition-all duration-200 disabled:opacity-50"
          >
            {{ loading ? '...' : t('auth.signIn') }}
          </button>
        </form>

        <!-- Register form -->
        <form v-if="tab === 'register'" @submit.prevent="handleRegister" class="space-y-3">
          <input
            v-model="username"
            type="text"
            :placeholder="t('auth.username')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="email"
            type="email"
            :placeholder="t('auth.email')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="displayName"
            type="text"
            :placeholder="t('auth.name')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="password"
            type="password"
            :placeholder="t('auth.password')"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <p v-if="error" class="text-xs text-[#d73a49]">{{ error }}</p>
          <button
            type="submit"
            :disabled="loading"
            class="w-full py-2 text-sm font-semibold bg-accent text-[#0d1117] rounded-lg hover:brightness-110 transition-all duration-200 disabled:opacity-50"
          >
            {{ loading ? '...' : 'Create Account' }}
          </button>
        </form>

        <!-- Local account form (Tauri only) -->
        <div v-if="tab === 'local'" class="space-y-3">
          <!-- Account switcher -->
          <div v-if="userStore.localAccounts.length > 0" class="space-y-1">
            <label class="text-xs text-ink-muted">Switch account</label>
            <select
              v-model="selectedLocalAccount"
              @change="switchLocalAccount"
              class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="">— select an account —</option>
              <option
                v-for="acct in userStore.localAccounts"
                :key="acct.id"
                :value="acct.id"
              >
                {{ acct.username }}
              </option>
            </select>
          </div>

          <div class="text-xs text-ink-muted text-center py-1">
            — or enter credentials —
          </div>

          <input
            v-model="username"
            type="text"
            placeholder="Username"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="password"
            type="password"
            placeholder="Password"
            required
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <!-- Extra fields for new account creation -->
          <input
            v-model="email"
            type="email"
            placeholder="Email (optional)"
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <input
            v-model="displayName"
            type="text"
            placeholder="Display name (optional)"
            class="w-full bg-[#0d1117] border border-divider rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
          />
          <p class="text-xs text-ink-muted">💻 Stored locally — no server required</p>
          <p v-if="error" class="text-xs text-[#d73a49]">{{ error }}</p>
          <div class="flex gap-2">
            <button
              type="button"
              :disabled="loading"
              class="flex-1 py-2 text-sm font-semibold bg-accent text-[#0d1117] rounded-lg hover:brightness-110 transition-all duration-200 disabled:opacity-50"
              @click="handleLocalLogin"
            >
              {{ loading ? '...' : 'Sign In' }}
            </button>
            <button
              type="button"
              :disabled="loading"
              class="flex-1 py-2 text-sm font-semibold border border-accent text-accent rounded-lg hover:bg-accent/10 transition-all duration-200 disabled:opacity-50"
              @click="handleLocalRegister"
            >
              {{ loading ? '...' : 'Create Account' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>
