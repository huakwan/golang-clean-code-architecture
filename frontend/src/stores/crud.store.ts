import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as crudApi from '@/api/crud.api'
import {
  GO_REGISTERED_MODELS,
  type AvroSchema,
  type EntityModelOption,
} from '@/types/crud.types'

export const useCrudStore = defineStore('crud', () => {
  const models = ref<EntityModelOption[]>([...GO_REGISTERED_MODELS])
  const selectedSlug = ref<string>(GO_REGISTERED_MODELS[0].slug)
  const schema = ref<AvroSchema | null>(null)
  const items = ref<Record<string, unknown>[]>([])
  const selectedItem = ref<Record<string, unknown> | null>(null)

  const page = ref(1)
  const pageSize = ref(10)
  const totalPages = ref(1)
  const totalData = ref(0)

  const loadingList = ref(false)
  const loadingSchema = ref(false)
  const loadingDetail = ref(false)
  const error = ref<string | null>(null)

  async function fetchSchema(slug = selectedSlug.value): Promise<AvroSchema | null> {
    loadingSchema.value = true
    error.value = null
    try {
      schema.value = await crudApi.describeEntity(slug)
      return schema.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load schema'
      schema.value = null
      throw err
    } finally {
      loadingSchema.value = false
    }
  }

  async function fetchList(
    slug = selectedSlug.value,
    targetPage = page.value,
    targetPageSize = pageSize.value,
  ): Promise<void> {
    loadingList.value = true
    error.value = null
    try {
      const response = await crudApi.listEntities(slug, targetPage, targetPageSize)
      items.value = Array.isArray(response.data) ? response.data : []
      page.value = response.page || targetPage
      pageSize.value = response.page_size || targetPageSize
      totalPages.value = Math.max(1, response.total_page || 1)
      totalData.value = response.total_data ?? items.value.length
      if (!schema.value && response.data_schema) {
        schema.value = response.data_schema
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load data'
      items.value = []
      throw err
    } finally {
      loadingList.value = false
    }
  }

  async function selectModel(slug: string): Promise<void> {
    selectedSlug.value = slug
    page.value = 1
    selectedItem.value = null
    await Promise.all([fetchSchema(slug), fetchList(slug, 1, pageSize.value)])
  }

  async function fetchDetail(id: string | number): Promise<Record<string, unknown> | null> {
    loadingDetail.value = true
    error.value = null
    try {
      const response = await crudApi.retrieveEntity(selectedSlug.value, id)
      selectedItem.value = response.data ?? null
      return selectedItem.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load record'
      throw err
    } finally {
      loadingDetail.value = false
    }
  }

  function clearDetail(): void {
    selectedItem.value = null
  }

  return {
    models,
    selectedSlug,
    schema,
    items,
    selectedItem,
    page,
    pageSize,
    totalPages,
    totalData,
    loadingList,
    loadingSchema,
    loadingDetail,
    error,
    fetchSchema,
    fetchList,
    selectModel,
    fetchDetail,
    clearDetail,
  }
})
