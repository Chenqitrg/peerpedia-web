// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

import apiClient from './client'
import type { CompilePreviewPayload, CompilePreviewResponse } from './types'

export async function compilePreview(payload: CompilePreviewPayload): Promise<CompilePreviewResponse> {
  const res = await apiClient.post('/compile-preview', payload)
  return res.data
}

export async function compileDownload(content: string, format: 'markdown' | 'typst') {
  return apiClient.post('/compile-download', { content, format }, { responseType: 'blob' })
}
