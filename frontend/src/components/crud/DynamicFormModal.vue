<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import type { ApiErrorResponse } from '@/types/api.types'
import type { AvroField, AvroSchema } from '@/types/crud.types'

const READ_ONLY_FIELDS = new Set(['id', '_id', 'created_at', 'updated_at'])

const props = defineProps<{
  open: boolean
  mode: 'create' | 'edit'
  schema: AvroSchema | null
  initialData?: Record<string, unknown> | null
  entityLabel?: string
  submitting?: boolean
  error?: ApiErrorResponse | null
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: Record<string, unknown>): void
}>()

const formValues = reactive<Record<string, unknown>>({})
const validationError = ref<string | null>(null)

const editableFields = computed<AvroField[]>(() =>
  (props.schema?.fields ?? []).filter(
    (field) => Boolean(field.name) && !READ_ONLY_FIELDS.has(field.name) && !field.fields,
  ),
)

function toDatetimeLocal(value: unknown): string {
  if (!value) return ''
  const date = new Date(String(value))
  if (Number.isNaN(date.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}

function defaultValueForField(field: AvroField, source?: Record<string, unknown> | null): unknown {
  const existing = source?.[field.name]
  if (field.type === 'boolean') {
    return Boolean(existing)
  }
  if (field.type === 'map' || field.type === 'array') {
    if (existing !== undefined && existing !== null) {
      return typeof existing === 'string' ? existing : JSON.stringify(existing, null, 2)
    }
    return field.type === 'array' ? '[]' : '{}'
  }
  if (field.type === 'datetime') {
    return toDatetimeLocal(existing)
  }
  if (existing === undefined || existing === null) {
    return ''
  }
  return String(existing)
}

function resetForm(): void {
  validationError.value = null
  for (const key of Object.keys(formValues)) {
    delete formValues[key]
  }
  const source = props.mode === 'edit' ? props.initialData : null
  for (const field of editableFields.value) {
    formValues[field.name] = defaultValueForField(field, source)
  }
}

watch(
  () => [props.open, props.mode, props.schema, props.initialData],
  ([isOpen]) => {
    if (isOpen) {
      resetForm()
    }
  },
  { immediate: true },
)

function inputTypeFor(field: AvroField): string {
  if (field.type === 'int' || field.type === 'long' || field.type === 'float' || field.type === 'double') {
    return 'number'
  }
  if (field.type === 'datetime') return 'datetime-local'
  if (field.name === 'email') return 'email'
  return 'text'
}

function isFloatType(type: string): boolean {
  return type === 'float' || type === 'double'
}

function handleSubmit(): void {
  validationError.value = null
  const payload: Record<string, unknown> = {}

  for (const field of editableFields.value) {
    const raw = formValues[field.name]

    if (field.type === 'boolean') {
      payload[field.name] = Boolean(raw)
      continue
    }

    if (field.type === 'map' || field.type === 'array') {
      const text = String(raw ?? '').trim()
      if (!text) continue
      try {
        payload[field.name] = JSON.parse(text)
      } catch {
        validationError.value = `Invalid JSON in field "${field.name}".`
        return
      }
      continue
    }

    if (field.type === 'int' || field.type === 'long') {
      const text = String(raw ?? '').trim()
      if (text === '') continue
      const parsed = Number.parseInt(text, 10)
      if (Number.isNaN(parsed)) {
        validationError.value = `Field "${field.name}" must be an integer.`
        return
      }
      payload[field.name] = parsed
      continue
    }

    if (field.type === 'float' || field.type === 'double') {
      const text = String(raw ?? '').trim()
      if (text === '') continue
      const parsed = Number.parseFloat(text)
      if (Number.isNaN(parsed)) {
        validationError.value = `Field "${field.name}" must be a number.`
        return
      }
      payload[field.name] = parsed
      continue
    }

    if (field.type === 'datetime') {
      const text = String(raw ?? '').trim()
      if (!text) continue
      const parsed = new Date(text)
      payload[field.name] = Number.isNaN(parsed.getTime()) ? text : parsed.toISOString()
      continue
    }

    payload[field.name] = String(raw ?? '')
  }

  emit('submit', payload)
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4"
    @click.self="emit('close')"
  >
    <div class="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl">
      <div class="flex items-center justify-between border-b border-slate-200 pb-3">
        <div>
          <h3 class="text-base font-semibold text-slate-900">
            {{ mode === 'create' ? 'Create' : 'Edit' }} {{ entityLabel || schema?.name || 'Record' }}
          </h3>
          <p class="text-xs text-slate-500">
            Fields generated automatically from the entity Avro schema.
          </p>
        </div>
        <button
          type="button"
          class="rounded-md px-2 py-1 text-sm text-slate-500 hover:bg-slate-100"
          @click="emit('close')"
        >
          ✕
        </button>
      </div>

      <div
        v-if="validationError"
        class="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-3.5 py-2.5 text-xs text-amber-800"
      >
        {{ validationError }}
      </div>

      <div
        v-if="error"
        class="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3.5 py-2.5 text-xs text-rose-800"
      >
        <span class="font-mono font-semibold">{{ error.trace_id }}</span>: {{ error.message }}
      </div>

      <form class="mt-4 space-y-4" @submit.prevent="handleSubmit">
        <div v-if="editableFields.length === 0" class="py-4 text-center text-sm text-slate-500">
          No editable fields available in this schema.
        </div>

        <div class="-mx-1 max-h-96 space-y-3.5 overflow-y-auto px-1 py-1">
          <div v-for="field in editableFields" :key="field.name">
            <label
              v-if="field.type === 'boolean'"
              class="flex items-center gap-2.5 text-sm font-medium text-slate-700"
            >
              <input
                v-model="formValues[field.name]"
                type="checkbox"
                :data-testid="`field-${field.name}`"
                class="h-4 w-4 rounded border-slate-300 text-indigo-600 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:ring-offset-1"
              />
              <span class="font-mono text-xs">{{ field.name }}</span>
              <span class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                {{ field.type }}
              </span>
            </label>

            <div v-else>
              <label class="mb-1 flex items-center justify-between text-xs font-medium text-slate-700">
                <span class="font-mono">{{ field.name }}</span>
                <span class="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                  {{ field.type }}
                </span>
              </label>

              <textarea
                v-if="field.type === 'map' || field.type === 'array'"
                v-model="(formValues[field.name] as string)"
                :data-testid="`field-${field.name}`"
                rows="3"
                class="block w-full rounded-lg border border-slate-300 px-3 py-2 font-mono text-xs text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />

              <input
                v-else
                v-model="(formValues[field.name] as string)"
                :type="inputTypeFor(field)"
                :step="isFloatType(field.type) ? 'any' : undefined"
                :data-testid="`field-${field.name}`"
                class="block w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-200"
              />
            </div>
          </div>
        </div>

        <div class="flex justify-end gap-2 border-t border-slate-200 pt-4">
          <button
            type="button"
            class="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            @click="emit('close')"
          >
            Cancel
          </button>
          <button
            type="submit"
            :disabled="submitting || editableFields.length === 0"
            data-testid="form-submit"
            class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ submitting ? 'Saving...' : mode === 'create' ? 'Create' : 'Save Changes' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
