// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import apiClient from './client'
import type { AuthResponse, LoginPayload, RegisterPayload } from './types'

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const res = await apiClient.post('/auth/login', payload)
  return res.data
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await apiClient.post('/auth/register', payload)
  return res.data
}

export async function getMe(token: string): Promise<AuthResponse> {
  const res = await apiClient.get('/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
  return res.data
}
