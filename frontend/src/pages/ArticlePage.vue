<script setup lang="ts">
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useArticleStore } from '../stores/useArticleStore'
import DiffViewer from '../components/DiffViewer.vue'

const route = useRoute()
const store = useArticleStore()
const id = route.params.id as string

onMounted(() => {
  store.fetchArticle(id)
})

function statusBadge(status: string): string {
  switch (status) {
    case 'published': return 'badge-published'
    case 'review':
    case 'in_review': return 'badge-review'
    default: return 'badge-draft'
  }
}
</script>

<template>
  <div class="article-page animate-fade-in">
    <!-- Loading -->
    <div v-if="!store.currentArticle" class="space-y-4 animate-pulse">
      <div class="skeleton h-10 w-3/4 mb-2" />
      <div class="skeleton h-5 w-1/3 mb-4" />
      <div class="skeleton h-4 w-full mb-2" />
      <div class="skeleton h-4 w-full mb-2" />
      <div class="skeleton h-4 w-2/3" />
    </div>

    <!-- Article content -->
    <article v-else class="max-w-content">
      <!-- Header -->
      <header class="mb-8">
        <div class="flex items-center gap-2 mb-3">
          <span :class="statusBadge(store.currentArticle.status)">
            {{ store.currentArticle.status }}
          </span>
        </div>

        <h1 class="text-display-md md:text-display text-ink mb-4">
          {{ store.currentArticle.title || 'Untitled' }}
        </h1>

        <div class="flex flex-wrap items-center gap-3 text-sm text-ink-muted">
          <span v-if="store.currentArticle.authors?.length" class="flex items-center gap-1.5">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            {{ store.currentArticle.authors.map((a: any) => a.name).join(', ') }}
          </span>
          <span class="text-ink-subtle">·</span>
          <span>{{ store.currentArticle.review_count ?? 0 }} reviews</span>
          <span class="text-ink-subtle">·</span>
          <span>{{ store.currentArticle.fork_count ?? 0 }} forks</span>
        </div>
      </header>

      <!-- Scores section -->
      <section v-if="store.currentArticle.score" class="card p-6 mb-8">
        <h2 class="text-lg font-heading font-semibold text-ink mb-4">Review Scores</h2>
        <div class="grid grid-cols-5 gap-4 text-center">
          <div v-for="[key, val] in Object.entries(store.currentArticle.score)" :key="key" class="space-y-1">
            <div class="text-2xl font-bold text-primary-600">{{ val }}</div>
            <div class="text-xs text-ink-muted capitalize">{{ key }}</div>
          </div>
        </div>
      </section>

      <!-- Article body placeholder -->
      <section class="card p-6 mb-8">
        <h2 class="text-lg font-heading font-semibold text-ink mb-4">Abstract</h2>
        <div class="prose-custom">
          <p class="text-ink-muted">
            {{ store.currentArticle.compiled_output || 'No abstract available.' }}
          </p>
        </div>
      </section>

      <!-- History / Diff section -->
      <section class="mt-12">
        <DiffViewer :article-id="id" />
      </section>
    </article>
  </div>
</template>
