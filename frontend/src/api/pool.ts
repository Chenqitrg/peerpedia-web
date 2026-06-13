// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import apiClient from './client'

export async function getPool(): Promise<import('./types').PoolResponse> {
  const res = await apiClient.get('/pool')
  return res.data
}
