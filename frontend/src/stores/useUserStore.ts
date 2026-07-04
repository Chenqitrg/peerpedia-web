// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { login as apiLogin, register as apiRegister, getMe } from '../api/auth'
import { loadString, loadJSON, saveString, saveJSON, remove } from '../composables/useLocalStorage'
import type { UserProfile } from '../api/types'

export const useUserStore = defineStore('user', () => {
  const storedToken = loadString('token')
  const storedViewer = loadJSON<UserProfile>('viewer')

  const viewer = ref<UserProfile | null>(storedViewer)
  const token = ref<string | null>(storedToken)
  const showAuthModal = ref(false)
  const intendedRoute = ref<string | null>(null)
  const syncError = ref<string | null>(null)

  function _persist(user: UserProfile, t: string) {
    viewer.value = user
    token.value = t
    saveJSON('viewer', user)
    saveString('token', t)
  }

  function clear() {
    const uid = viewer.value?.id
    viewer.value = null
    token.value = null
    syncError.value = null
    remove('viewer')
    remove('token')
    // Clear stale draft data to prevent cross-user leaks.
    remove('peerpedia_draft')
    if (uid) {
      remove(`editor-draft-${uid}-new`)
      remove(`editor-draft-id-${uid}-new`)
      remove(`peerpedia_draft_${uid}`)
    }
  }

  async function login(username: string, password: string) {
    const { user, token: t } = await apiLogin({ username, password })
    _persist(user, t)
  }

  async function register(username: string, password: string, email: string, name: string) {
    const { user, token: t } = await apiRegister({ username, password, email, name })
    _persist(user, t)
  }

  function logout() {
    clear()
    showAuthModal.value = false
  }

  async function restoreSession() {
    const t = token.value
    if (!t) return
    try {
      const { user } = await getMe(t)
      viewer.value = user
      saveJSON('viewer', user)
    } catch {
      clear()
    }
  }

  return {
    viewer,
    token,
    showAuthModal,
    intendedRoute,
    syncError,
    login,
    register,
    logout,
    restoreSession,
    clear,
  }
})
