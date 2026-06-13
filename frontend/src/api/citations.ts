// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import apiClient from './client'
import type { CitationClickPayload } from './types'

export async function recordCitationClick(payload: CitationClickPayload): Promise<void> {
  await apiClient.post('/citations/click', payload)
}
