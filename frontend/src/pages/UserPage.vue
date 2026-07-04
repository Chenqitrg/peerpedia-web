<!-- SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors -->
<!-- SPDX-License-Identifier: CC-BY-NC-SA-4.0 -->

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { useOffline } from '../composables/useOffline'
import { useNetworkStatus } from '../composables/useNetworkStatus'
import { getUser, getFollowing, getFollowers, followUser, unfollowUser } from '../api/users'
import { getArticles } from '../api/articles'
import { useUserStore } from '../stores/useUserStore'
import { useFollowCache } from '../composables/useFollowCache'
import { useBookmarkToggle } from '../composables/useBookmarkToggle'
import { useAsyncResource } from '../composables/useAsyncResource'
import ArticleCard from '../components/ArticleCard.vue'
import ReputationBadges from '../components/ReputationBadges.vue'
import type { UserProfile, ArticleSummary } from '../api/types'
import {
  UsersRound,
  UserCheck,
  BookOpen,
  MapPin,
  Mail,
  Edit,
} from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const { t } = useI18n()
const { canRead, canWrite, getFallback } = useOffline()

const canViewFollowGraph = computed(() => canRead('user.follow_graph'))

const id = computed(() => route.params.id as string)
const isSelf = computed(() => userStore.viewer?.id === id.value)
const { isSynced } = useNetworkStatus()

const { data: user, loading, error, execute: loadUser } = useAsyncResource(
  async () => getUser(id.value),
  null as UserProfile | null,
  { immediate: true },
)

const articles = ref<ArticleSummary[]>([])

const { toggle: handleToggleBookmark } = useBookmarkToggle(articles)

const isFollowing = ref(false)
const followLoading = ref(false)

// Load initial follow state.
  // Load initial follow state.
  async function loadFollowState() {
    if (!userStore.viewer) return
    if (!isSynced.value) {
      // Offline — read from local cache.
      const cache = useFollowCache()
      const ids = await cache.getCachedFollowingIds(userStore.viewer.id)
      if (isSelf.value && user.value) {
        if (ids !== null && ids.length > 0) {
          user.value = { ...user.value, following_count: ids.length }
        }
      } else if (ids) {
        isFollowing.value = ids.includes(id.value)
      }
      return
    }
    // Online — use server REST API. Fetch both following + followers counts.
    try {
      const [following, followers] = await Promise.all([
        getFollowing(userStore.viewer.id),
        getFollowers(userStore.viewer.id),
      ])
      const followed = Array.isArray(following) ? following : (following as any)?.users || []
      const followerList = Array.isArray(followers) ? followers : (followers as any)?.users || []
      if (isSelf.value && user.value) {
        user.value = { ...user.value, following_count: followed.length, followers_count: followerList.length }
      } else {
        isFollowing.value = followed.some((u: any) => u.id === id.value)
      }
    } catch { /* fall through */ }
  }


async function handleFollow() {
  if (!userStore.viewer) return
  if (!userStore.token) return
  followLoading.value = true
  try {
    if (isFollowing.value) {
      await unfollowUser(id.value)
    } else {
      await followUser(id.value)
    }
    isFollowing.value = !isFollowing.value
    // Refresh offline cache after mutation.
    useFollowCache().refreshCache(userStore.viewer.id).catch(() => {})
  } catch (e: any) {
    console.error('[UserPage] follow error:', e?.response?.status, e?.response?.data?.detail || e?.message || e)
    /* revert on failure — no state change */
  }
  finally { followLoading.value = false }
}

async function loadArticles() {
  const merged: ArticleSummary[] = []

  try {
    const artData = await getArticles({ author_id: id.value, page: 1, size: 50 })
    const serverArticles = Array.isArray(artData) ? artData : (artData.articles ?? [])
    merged.push(...serverArticles)
    useFollowCache().setCachedUserArticles(id.value, serverArticles).catch(() => {})
  } catch { /* server unreachable */ }

  articles.value = merged
}

// Load articles + follow state in parallel after user fetch.
watch(user, (u) => {
  if (u) { Promise.all([loadArticles(), loadFollowState()]) }
}, { immediate: true })

// Route change triggers user reload via useAsyncResource + watch(user, ...) —
// no explicit route watcher needed here.


</script>

<template>
  <div class="user-page animate-fade-in">
    <!-- Loading -->
    <div v-if="loading" class="space-y-4 animate-pulse">
      <div class="flex items-start gap-4 mb-6">
        <div class="skeleton w-16 h-16 rounded-full shrink-0" />
        <div class="space-y-2 flex-1">
          <div class="skeleton h-7 w-1/3" />
          <div class="skeleton h-4 w-1/4" />
          <div class="skeleton h-4 w-1/5" />
        </div>
      </div>
    </div>

    <template v-else-if="user">
      <!-- Profile header -->
      <div class="bg-card border border-divider rounded-lg p-6 mb-6">
        <div class="flex flex-col sm:flex-row items-start gap-5">
          <!-- Avatar -->
          <div class="w-16 h-16 rounded-full bg-[#21262d] flex items-center justify-center shrink-0 border border-divider overflow-hidden">
            <img
              v-if="user.avatar_url"
              :src="user.avatar_url"
              :alt="user.name"
              class="w-full h-full object-cover"
            />
            <span v-else class="text-xl font-heading font-bold text-ink-muted">
              {{ (user.name || '?')[0].toUpperCase() }}
            </span>
          </div>

          <div class="flex-1 min-w-0">
            <!-- Name -->
            <h1 class="text-display-md font-heading font-bold text-ink mb-0.5">
              {{ user.name }}
            </h1>

            <!-- Anonymous name (only visible to self) -->
            <p v-if="isSelf" class="text-xs text-ink-muted mb-2">
              {{ t('user.anonymousName') }}: <span class="font-mono text-ink">{{ user.anonymous_name }}</span>
            </p>

            <!-- Affiliation & Contact -->
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-ink-muted mb-3">
              <span v-if="user.affiliation" class="flex items-center gap-1">
                <MapPin class="w-3 h-3" stroke-width="2" />
                {{ user.affiliation }}
              </span>
              <span v-if="user.contact" class="flex items-center gap-1">
                <Mail class="w-3 h-3" stroke-width="2" />
                {{ user.contact }}
              </span>
              <span class="flex items-center gap-1">
                <BookOpen class="w-3 h-3" stroke-width="2" />
                {{ t('user.articlesCount', { count: user.article_count }) }}
              </span>
            </div>

            <!-- Stats row -->
            <div class="flex items-center gap-4 text-sm">
              <router-link
                v-if="canViewFollowGraph"
                :to="`/user/${user.id}/followers`"
                class="flex items-center gap-1.5 text-ink-muted hover:text-ink transition-colors no-underline"
              >
                <UsersRound class="w-3.5 h-3.5" stroke-width="2" />
                <span class="font-semibold">{{ user.followers_count }}</span>
                <span>{{ t('common.followers') }}</span>
              </router-link>
              <span
                v-else
                class="flex items-center gap-1.5 text-ink-muted/50 cursor-not-allowed"
                :data-tooltip="t(getFallback('user.follow_graph'))"
              >
                <UsersRound class="w-3.5 h-3.5" stroke-width="2" />
                <span class="font-semibold">{{ user.followers_count }}</span>
                <span>{{ t('common.followers') }}</span>
              </span>
              <router-link
                v-if="canViewFollowGraph"
                :to="`/user/${user.id}/following`"
                class="flex items-center gap-1.5 text-ink-muted hover:text-ink transition-colors no-underline"
              >
                <UserCheck class="w-3.5 h-3.5" stroke-width="2" />
                <span class="font-semibold">{{ user.following_count }}</span>
                <span>{{ t('common.following') }}</span>
              </router-link>
              <span
                v-else
                class="flex items-center gap-1.5 text-ink-muted/50 cursor-not-allowed"
                :data-tooltip="t(getFallback('user.follow_graph'))"
              >
                <UserCheck class="w-3.5 h-3.5" stroke-width="2" />
                <span class="font-semibold">{{ user.following_count }}</span>
                <span>{{ t('common.following') }}</span>
              </span>
            </div>
          </div>

          <!-- Follow/Unfollow button (viewing others) -->
          <button
            v-if="!isSelf && userStore.viewer"
            class="btn-sm shrink-0 transition-colors duration-200"
            :class="isFollowing
              ? 'btn-outline rounded-xl'
              : canWrite('user.follow_graph') && userStore.token
                ? 'bg-accent text-page hover:brightness-110 rounded-xl'
                : 'bg-[#21262d] text-ink-muted/50 cursor-not-allowed rounded-xl'"
            :disabled="followLoading || !canWrite('user.follow_graph') || !userStore.token"
            :data-tooltip="!userStore.token ? 'Sign in to follow' : !canWrite('user.follow_graph') ? t(getFallback('user.follow_graph')) : ''"
            @click="handleFollow"
          >
            {{ isFollowing ? t('common.following') : t('common.follow') }}
          </button>

          <!-- Edit profile button (self only) — coming soon -->
          <button
            v-if="isSelf"
            class="btn-outline btn-sm shrink-0 opacity-50 cursor-not-allowed"
            disabled
            :data-tooltip="t('common.comingSoon')"
          >
            <Edit class="w-3.5 h-3.5" stroke-width="2" />
            {{ t('common.editProfile') }}
          </button>
        </div>

        <!-- Expertise -->
        <div v-if="user.expertise?.length" class="flex flex-wrap gap-1.5 mt-4 pt-4 border-t border-divider">
          <span
            v-for="exp in user.expertise"
            :key="exp"
            class="px-2.5 py-0.5 text-xs text-ink-muted bg-[#21262d] rounded-full"
          >
            {{ exp }}
          </span>
        </div>

        <!-- Reputation -->
        <div v-if="user.reputation" class="mt-4 pt-4 border-t border-divider">
          <ReputationBadges :reputation="user.reputation" :show-label="true" />
        </div>
      </div>


      <!-- Articles section -->
      <div>
        <h2 class="text-lg font-heading font-semibold text-ink mb-4">
          {{ isSelf ? t('user.myDrafts') : t('user.articlesTitle') }}
        </h2>

        <div v-if="articles.length === 0" class="card p-8 text-center">
          <p class="text-ink-muted text-sm">{{ t('common.noArticles') }}</p>
        </div>

        <div v-else class="space-y-4">
          <ArticleCard
            v-for="article in articles"
            :key="article.id"
            :article="article"
            @toggle-bookmark="handleToggleBookmark"
            @deleted="(id: string) => articles = articles.filter(a => a.id !== id)"
          />
        </div>
      </div>
    </template>

    <!-- Error state -->
    <div v-else class="card p-12 text-center">
      <p class="text-ink-muted">{{ t('user.notFound') }}</p>
    </div>
  </div>
</template>
