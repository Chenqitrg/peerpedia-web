<script setup lang="ts">
defineProps<{
  score: { originality: number; rigor: number; completeness: number; pedagogy: number; impact: number } | null
  highlightFirst?: boolean
}>()
</script>

<template>
  <template v-if="score">
    <span :class="highlightFirst ? 'text-accent font-semibold' : ''">O:{{ score.originality }}</span>
    <span>R:{{ score.rigor }}</span>
    <span>C:{{ score.completeness }}</span>
    <span>P:{{ score.pedagogy }}</span>
    <span>I:{{ score.impact }}</span>
  </template>
  <span v-else class="text-ink-muted">No scores yet</span>
</template>
