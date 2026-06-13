<!-- SPDX-FileCopyrightText: 2024-2026 Chenqi Meng and PeerPedia contributors -->
<!-- SPDX-License-Identifier: CC-BY-NC-SA-4.0 -->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

defineProps<{
  message: string
  backToHome?: boolean
}>()

defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="card p-8 text-center">
    <p class="text-ink-muted mb-4">{{ message }}</p>
    <button v-if="!backToHome" class="btn-outline mt-4" @click="$emit('retry')">{{ t('common.retry') }}</button>
    <router-link v-else to="/" class="btn-primary no-underline">{{ t('common.backToHome') }}</router-link>
  </div>
</template>
