import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTauri } from '../useTauri'

// Mock @tauri-apps/api/core — must be at top level before any import uses it.
const mockInvoke = vi.fn()
vi.mock('@tauri-apps/api/core', () => ({
  invoke: mockInvoke,
}))

describe('useTauri', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    delete (window as any).__TAURI__
  })

  it('detects Web mode (no __TAURI__)', () => {
    const tauri = useTauri()
    expect(tauri.isTauri.value).toBe(false)
  })

  it('detects Tauri mode when __TAURI__ is present', () => {
    ;(window as any).__TAURI__ = {}
    const tauri = useTauri()
    expect(tauri.isTauri.value).toBe(true)
  })

  it('createAccount returns null in Web mode', async () => {
    const tauri = useTauri()
    const result = await tauri.createAccount({
      username: 'test',
      password: 'pass',
      email: '',
      name: '',
    })
    expect(result).toBeNull()
  })

  it('login returns null in Web mode', async () => {
    const tauri = useTauri()
    const result = await tauri.login({ username: 'test', password: 'pass' })
    expect(result).toBeNull()
  })

  it('listAccounts returns null in Web mode', async () => {
    const tauri = useTauri()
    const result = await tauri.listAccounts()
    expect(result).toBeNull()
  })

  it('saveDraft returns null in Web mode', async () => {
    const tauri = useTauri()
    const result = await tauri.saveDraft({
      id: 'd1',
      account_id: 'a1',
      title: 'Draft',
      content: '# Hello',
      format: 'markdown',
    })
    expect(result).toBeNull()
  })

  it('calls invoke in Tauri mode for login', async () => {
    ;(window as any).__TAURI__ = {}
    mockInvoke.mockResolvedValue({ id: 'u1', username: 'alice' })

    const tauri = useTauri()
    const result = await tauri.login({ username: 'alice', password: 'pass' })
    expect(mockInvoke).toHaveBeenCalledWith('login', {
      username: 'alice',
      password: 'pass',
    })
    expect(result).toEqual({ id: 'u1', username: 'alice' })
  })

  it('returns error object when invoke throws', async () => {
    ;(window as any).__TAURI__ = {}
    mockInvoke.mockRejectedValue(new Error('IPC failed'))

    const tauri = useTauri()
    const result = await tauri.login({ username: 'alice', password: 'pass' })
    expect(result).toEqual({ error: 'IPC failed' })
  })

  it('returns error object when invoke returns AppError', async () => {
    ;(window as any).__TAURI__ = {}
    mockInvoke.mockResolvedValue({
      code: 'AUTH_FAILED',
      message: 'Incorrect password',
    })

    const tauri = useTauri()
    const result = await tauri.login({ username: 'alice', password: 'wrong' })
    expect(result).toEqual({ error: 'Incorrect password' })
  })

  it('saveDraft calls invoke with correct params in Tauri mode', async () => {
    ;(window as any).__TAURI__ = {}
    mockInvoke.mockResolvedValue({
      id: 'draft-1',
      account_id: 'a1',
      title: 'Draft',
      content: '# Hello',
      format: 'markdown',
      updated_at: '2026-06-06',
    })

    const tauri = useTauri()
    const result = await tauri.saveDraft({
      account_id: 'a1',
      title: 'Draft',
      content: '# Hello',
      format: 'markdown',
    })
    expect(mockInvoke).toHaveBeenCalledWith('save_draft', expect.objectContaining({
      account_id: 'a1',
      title: 'Draft',
    }))
    expect(result).toHaveProperty('id', 'draft-1')
  })
})
