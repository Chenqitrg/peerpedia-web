<script setup lang="ts">
defineProps<{
  count?: number
}>()
</script>

<template>
  <div class="space-y-4">
    <div v-for="i in (count ?? 3)" :key="i" class="card p-5 animate-pulse">
      <div class="skeleton h-5 w-2/3 mb-3" />
      <div class="skeleton h-4 w-1/3 mb-2" />
      <div class="skeleton h-3 w-full" />
    </div>
  </div>
</template>
