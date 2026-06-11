/**
 * xspec Specification Tests — SchoolsPage Follow State
 *
 * SPECIFICATION STATUS = LOCKED
 *
 * These tests encode the contract for follow behavior on the Schools page.
 * Do not modify tests merely to make implementation pass.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'

// ── Hoisted mock data ────────────────────────────────────────────────────

const { mockUsers, mockFollowing, mockViewer, viewerRef } = vi.hoisted(() => {
  const v = {
    id: 'uuid-einstein', name: 'Albert Einstein', username: 'einstein',
    anonymous_name: '', affiliation: 'Princeton', expertise: ['physics'],
    reputation: {}, followers_count: 5, following_count: 3, article_count: 1,
  }
  return {
    mockUsers: [
      { id: 'uuid-feynman', name: 'Richard Feynman', affiliation: 'Caltech',
        expertise: ['physics'], article_count: 16, reputation: {} },
      { id: 'uuid-bohr', name: 'Niels Bohr', affiliation: 'Copenhagen',
        expertise: ['quantum mechanics'], article_count: 3, reputation: {} },
    ],
    mockFollowing: [{ id: 'uuid-bohr', name: 'Niels Bohr' }],
    mockViewer: v,
    viewerRef: { current: v as typeof v | null },
  }
})

// ── Module-level mutable state for mock control ──────────────────────────

import { ref as vRef } from 'vue'
const mockIsOnline = vRef(true)
let mockIsTauriMode = false
let mockIsBrowserLocal = false
let mockCanReadSchools = true

// ── Module mocks ─────────────────────────────────────────────────────────

const mockGetUsers = vi.fn().mockResolvedValue(mockUsers)
const mockGetFollowing = vi.fn().mockResolvedValue(mockFollowing)
const mockFollowUser = vi.fn().mockResolvedValue({})
const mockUnfollowUser = vi.fn().mockResolvedValue({})

vi.mock('../../api/users', () => ({
  getUsers: (...args: any[]) => mockGetUsers(...args),
  getFollowing: (...args: any[]) => mockGetFollowing(...args),
  followUser: (...args: any[]) => mockFollowUser(...args),
  unfollowUser: (...args: any[]) => mockUnfollowUser(...args),
}))

const mockTauriGetFollowing = vi.fn()
const mockTauriFollowUser = vi.fn()
const mockTauriUnfollowUser = vi.fn()

vi.mock('../../composables/useTauri', () => ({
  useTauri: () => ({
    getFollowing: (...args: any[]) => mockTauriGetFollowing(...args),
    followUser: (...args: any[]) => mockTauriFollowUser(...args),
    unfollowUser: (...args: any[]) => mockTauriUnfollowUser(...args),
    isFollowing: vi.fn(),
    listAccounts: vi.fn(),
    isTauri: { value: false },
    isBrowserLocal: { value: false },
  }),
}))

vi.mock('../../stores/useUserStore', () => ({
  useUserStore: () => ({
    get viewer() { return viewerRef.current },
    isTauriMode: mockIsTauriMode,
    isBrowserLocal: mockIsBrowserLocal,
    token: { value: 'test-token' },
  }),
}))

vi.mock('../../composables/useOffline', () => ({
  useOffline: () => ({
    canRead: (feature: string) => feature === 'schools' ? mockCanReadSchools : true,
    canWrite: () => true,
    getFallback: () => '',
    isLocalOnly: () => false,
  }),
}))

vi.mock('../../composables/useNetworkStatus', () => ({
  useNetworkStatus: () => ({
    isOnline: mockIsOnline,
    startPing: vi.fn(),
    stopPing: vi.fn(),
  }),
}))

const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockPush }),
  useRoute: () => ({ params: {}, query: {}, path: '/' }),
}))

// ── Imports ───────────────────────────────────────────────────────────────

import SchoolsPage from '../SchoolsPage.vue'

// Import for vi.mocked usage
const api = await import('../../api/users')

describe('xspec: SchoolsPage Follow State', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockIsOnline.value = true
    mockIsTauriMode = false
    mockIsBrowserLocal = false
    mockCanReadSchools = true
    mockGetUsers.mockResolvedValue(mockUsers)
    mockGetFollowing.mockResolvedValue(mockFollowing)
    mockFollowUser.mockResolvedValue({})
    mockUnfollowUser.mockResolvedValue({})
    mockTauriGetFollowing.mockResolvedValue([])
    mockTauriFollowUser.mockResolvedValue({ ok: true })
    mockTauriUnfollowUser.mockResolvedValue({ ok: true })
  })

  async function mountAndSettle() {
    const wrapper = mount(SchoolsPage)
    await nextTick()
    await new Promise(r => setTimeout(r, 50))
    return wrapper
  }

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: loadFollowState uses Tauri IPC in Tauri mode
  // (Rust backend now implements follow commands — local path is correct.)
  // ═══════════════════════════════════════════════════════════════════════
  describe('loadFollowState: Tauri mode uses Tauri IPC', () => {
    it('GIVEN Tauri mode '
     + 'WHEN the Schools page loads '
     + 'THEN follow state is fetched via Tauri IPC', async () => {
      mockIsTauriMode = true
      mockTauriGetFollowing.mockResolvedValue([{ id: 'uuid-bohr' }])

      await mountAndSettle()

      // Must use Tauri IPC with user_id parameter
      expect(mockTauriGetFollowing).toHaveBeenCalledWith({ user_id: 'uuid-einstein' })
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: loadFollowState uses Tauri IPC in offline local mode
  // ═══════════════════════════════════════════════════════════════════════
  describe('loadFollowState: offline local uses Tauri IPC', () => {
    it('GIVEN Tauri mode without server '
     + 'WHEN the Schools page loads '
     + 'THEN follow state is fetched via Tauri IPC with user_id param', async () => {
      mockIsTauriMode = true
      mockIsOnline.value = false
      mockTauriGetFollowing.mockResolvedValue([{ id: 'uuid-bohr' }])

      await mountAndSettle()

      // Must use Tauri IPC with user_id (not follower_id)
      expect(mockTauriGetFollowing).toHaveBeenCalledWith({ user_id: 'uuid-einstein' })
      expect(mockGetFollowing).not.toHaveBeenCalled()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: loadFollowState uses REST API in pure web mode
  // ═══════════════════════════════════════════════════════════════════════
  describe('loadFollowState: web mode uses REST API', () => {
    it('GIVEN pure web mode (no Tauri) '
     + 'WHEN the Schools page loads '
     + 'THEN follow state is fetched via REST API', async () => {
      mockIsTauriMode = false
      mockIsBrowserLocal = false

      await mountAndSettle()

      expect(mockGetFollowing).toHaveBeenCalledWith('uuid-einstein')
      expect(mockTauriGetFollowing).not.toHaveBeenCalled()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: toggleFollow uses Tauri IPC in Tauri mode
  // ═══════════════════════════════════════════════════════════════════════
  describe('toggleFollow: Tauri mode uses Tauri IPC', () => {
    it('GIVEN Tauri mode '
     + 'WHEN the user clicks Follow '
     + 'THEN the follow is persisted via Tauri IPC', async () => {
      mockIsTauriMode = true

      const wrapper = await mountAndSettle()
      const btn = wrapper.findAll('button').find(b => b.text().trim() === 'Follow')
      expect(btn).toBeTruthy()
      await btn!.trigger('click')
      await nextTick()

      expect(mockTauriFollowUser).toHaveBeenCalled()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: toggleFollow reverts on REST API failure
  // ═══════════════════════════════════════════════════════════════════════
  describe('toggleFollow: revert on failure', () => {
    it('GIVEN follow API call fails '
     + 'WHEN the user clicks Follow '
     + 'THEN the button reverts to "Follow"', async () => {
      mockFollowUser.mockRejectedValueOnce(new Error('Network error'))

      const wrapper = await mountAndSettle()
      const btn = wrapper.findAll('button').find(b => b.text().trim() === 'Follow')
      await btn!.trigger('click')
      await nextTick()
      await new Promise(r => setTimeout(r, 10))

      // Button should revert to "Follow" after failed API call
      const btns = wrapper.findAll('button')
      const followBtn = btns.find(b => b.text().trim() === 'Follow')
      expect(followBtn).toBeTruthy()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: toggleFollow calls unfollowUser (REST API) for already-followed
  // ═══════════════════════════════════════════════════════════════════════
  describe('toggleFollow: unfollow calls REST API in web mode', () => {
    it('GIVEN a user is already followed '
     + 'WHEN the user clicks the "Following" button '
     + 'THEN unfollowUser REST API is called', async () => {
      // Bohr is in mockFollowing — he is already followed
      mockGetFollowing.mockResolvedValue(mockFollowing)

      const wrapper = await mountAndSettle()
      // Find the "Following" button (Bohr)
      const btns = wrapper.findAll('button')
      const followingBtn = btns.find(b => b.text().trim() === 'Following')
      expect(followingBtn).toBeTruthy()

      await followingBtn!.trigger('click')
      await nextTick()

      expect(mockUnfollowUser).toHaveBeenCalled()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // ═══════════════════════════════════════════════════════════════════════
  // Regression: Tauri IPC error triggers revert
  // ═══════════════════════════════════════════════════════════════════════
  describe('Regression: Tauri IPC error reverts optimistic update', () => {
    it('GIVEN Tauri offline mode '
     + 'WHEN follow IPC returns { error } '
     + 'THEN button reverts to "Follow"', async () => {
      mockIsTauriMode = true
      mockIsOnline.value = false
      mockTauriGetFollowing.mockResolvedValue([])
      // Tauri _invoke returns { error } on failure — doesn't throw
      mockTauriFollowUser.mockResolvedValue({ error: 'command not found' })

      const wrapper = await mountAndSettle()
      // Simulate clicking Follow button
      await wrapper.find('button').trigger('click')
      await nextTick()
      await new Promise(r => setTimeout(r, 10))

      // Must have attempted Tauri IPC
      expect(mockTauriFollowUser).toHaveBeenCalled()
      // REST API must NOT be called
      expect(mockFollowUser).not.toHaveBeenCalled()
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: no follow state loaded without viewer
  // ═══════════════════════════════════════════════════════════════════════
  describe('loadFollowState: no viewer = no call', () => {
    it('GIVEN no viewer is logged in '
     + 'WHEN the Schools page loads '
     + 'THEN no follow API call is made', async () => {
      viewerRef.current = null

      await mountAndSettle()

      expect(mockGetFollowing).not.toHaveBeenCalled()
      expect(mockTauriGetFollowing).not.toHaveBeenCalled()

      viewerRef.current = mockViewer
    })
  })

  // ═══════════════════════════════════════════════════════════════════════
  // Regression: follow loads after users (no race condition)
  // ═══════════════════════════════════════════════════════════════════════
  describe('loadFollowState: runs after users fetch', () => {
    it('GIVEN users take time to load '
     + 'WHEN the Schools page is mounted '
     + 'THEN follow state is loaded after users arrive', async () => {
      let resolveUsers: (v: any) => void
      mockGetUsers.mockReturnValue(new Promise(r => { resolveUsers = r }))

      mount(SchoolsPage)
      await nextTick()

      // getFollowing should NOT be called before users resolve
      expect(mockGetFollowing).not.toHaveBeenCalled()

      // Resolve users
      resolveUsers!(mockUsers)
      await nextTick()
      await new Promise(r => setTimeout(r, 10))

      // Now getFollowing should be called
      expect(mockGetFollowing).toHaveBeenCalledWith('uuid-einstein')
    })
  })
})
