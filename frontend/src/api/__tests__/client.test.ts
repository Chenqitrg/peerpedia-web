// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import { describe, it, expect } from 'vitest'

describe('API client', () => {
  it('has correct base URL', async () => {
    const { apiClient } = await import('../client')
    expect(apiClient.defaults.baseURL).toBe('http://localhost:8080/api/v1')
  })
})
