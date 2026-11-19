<script setup lang="ts">
import { computed } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import AppLayout from '@/components/layout/AppLayout.vue'
import ToastNotification from '@/components/common/ToastNotification.vue'

const route = useRoute()
const useShell = computed(() => Boolean(route.meta.requiresAuth))
</script>

<template>
  <ToastNotification />
  <AppLayout v-if="useShell">
    <RouterView />
  </AppLayout>
  <RouterView v-else />
</template>
