import apiClient from './client'
import type { CitationClickPayload } from './types'

export async function recordCitationClick(payload: CitationClickPayload): Promise<void> {
  await apiClient.post('/citations/click', payload)
}
