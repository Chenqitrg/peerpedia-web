// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import apiClient from './client'
import type { SearchResult } from './types'

export interface SearchParams {
  q?: string
  category?: string
  sort?: string
  page?: number
  size?: number
}

export async function searchArticles(params: SearchParams): Promise<SearchResult> {
  const res = await apiClient.get('/search', { params })
  return res.data
}
