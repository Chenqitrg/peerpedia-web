// SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors
// SPDX-License-Identifier: CC-BY-NC-SA-4.0

// Draft persistence via REST API + localStorage fallback.

import apiClient from '../api/client'
import { v4 as uuidv4 } from 'uuid'

function draftStorageKey(accountId?: string): string {
  return accountId ? `peerpedia_draft_${accountId}` : 'peerpedia_draft'
}

interface PersistenceResult {
  id?: string
  account_id?: string
  title?: string
  content?: string
  format?: string
  commit_hash?: string
  updated_at?: string
  error?: string
  ok?: boolean
}

export function useDraftPersistence() {

  async function save(
    accountId: string,
    title: string,
    content: string,
    format: string,
    draftId?: string,
  ): Promise<PersistenceResult> {
    const storageKey = draftStorageKey(accountId)
    try {
      if (draftId) {
        const { data } = await apiClient.put(`/articles/${draftId}`, {
          title,
          content,
          commit_message: 'Save draft',
          publish: false,
        })
        localStorage.setItem(storageKey, JSON.stringify({
          id: data.id, title: data.title, content, format,
        }))
        return { id: data.id, title: data.title, content, format, commit_hash: data.commit_hash || '' }
      }

      const clientId = uuidv4()
      const { data } = await apiClient.post('/articles', {
        id: clientId,
        title,
        content,
        format,
        commit_message: 'Save draft',
        publish: false,
      })
      localStorage.setItem(storageKey, JSON.stringify({
        id: data.id, title: data.title, content, format,
      }))
      return {
        id: data.id,
        title: data.title,
        content,
        format,
        commit_hash: (data as any).commit_hash || '',
      }
    } catch (e: unknown) {
      throw e
    }
  }

  async function load(draftId: string, accountId?: string): Promise<PersistenceResult> {
    try {
      const { data: source } = await apiClient.get(`/articles/${draftId}/source`)
      return {
        id: draftId,
        title: '',
        content: source.content || '',
        format: source.format || 'markdown',
      }
    } catch {
      const storageKey = draftStorageKey(accountId)
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        try { return JSON.parse(stored) as PersistenceResult } catch { /* corrupt */ }
      }
      return { id: draftId, title: '', content: '', format: 'markdown' }
    }
  }

  async function listDrafts(accountId: string): Promise<{ id: string; title: string; updated_at: string }[]> {
    try {
      const { data } = await apiClient.get('/articles', {
        params: { status: 'draft', author_id: accountId },
      })
      const list = Array.isArray(data) ? data : (data.items || [])
      return list.map((item: Record<string, unknown>) => ({
        id: item.id as string,
        title: item.title as string,
        updated_at: item.updated_at as string,
      }))
    } catch {
      return []
    }
  }

  async function deleteDraft(draftId: string, accountId?: string): Promise<PersistenceResult> {
    try {
      await apiClient.put(`/articles/${draftId}`, { publish: false })
      localStorage.removeItem(draftStorageKey(accountId))
      return { ok: true }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : String(e)
      return { error: message }
    }
  }

  return { save, load, listDrafts, deleteDraft }
}
