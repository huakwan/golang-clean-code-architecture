<script setup lang="ts">
import { ref } from 'vue'
import type { AvroSchema } from '@/types/crud.types'

defineProps<{
  schema: AvroSchema | null
  loading?: boolean
}>()

const showRawJson = ref(false)

function badgeClass(avroType: string): string {
  switch (avroType) {
    case 'int':
    case 'long':
    case 'float':
      return 'bg-amber-100 text-amber-800'
    case 'boolean':
      return 'bg-purple-100 text-purple-800'
    case 'datetime':
      return 'bg-sky-100 text-sky-800'
    case 'string':
      return 'bg-emerald-100 text-emerald-800'
    default:
      return 'bg-slate-100 text-slate-700'
  }
}
</script>

<template>
  <div class="rounded-xl border border-slate-200 bg-white p-5 shadow-xs">
    <div class="flex items-center justify-between gap-2">
      <div>
        <h3 class="text-sm font-semibold text-slate-900">Avro Schema</h3>
        <p v-if="schema" class="mt-0.5 font-mono text-xs text-slate-500">
          {{ schema.type }} · {{ schema.name }}
        </p>
      </div>
      <button
        v-if="schema"
        type="button"
        class="rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:bg-slate-50"
        @click="showRawJson = !showRawJson"
      >
        {{ showRawJson ? 'Table View' : 'Raw JSON' }}
      </button>
    </div>

    <div v-if="loading" class="mt-4 text-sm text-slate-500">Loading schema...</div>

    <div v-else-if="!schema" class="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-500">
      No schema loaded.
    </div>

    <pre
      v-else-if="showRawJson"
      class="mt-4 max-h-96 overflow-auto rounded-lg bg-slate-900 p-4 text-xs text-slate-100"
    >{{ JSON.stringify(schema, null, 2) }}</pre>

    <div v-else class="mt-4 divide-y divide-slate-100">
      <div
        v-for="(field, idx) in schema.fields"
        :key="`${field.name || 'embedded'}-${idx}`"
        class="flex items-center justify-between py-2 text-sm"
      >
        <span class="font-mono text-xs text-slate-800">
          {{ field.name || '(embedded struct)' }}
        </span>
        <span :class="['rounded-full px-2.5 py-0.5 font-mono text-xs font-medium', badgeClass(field.type)]">
          {{ field.type }}
        </span>
      </div>
    </div>
  </div>
</template>
