import { ref } from 'vue'
import { defineStore } from 'pinia'
import * as crudApi from '@/api/crud.api'
import type { AvroSchema, EntityModelOption } from '@/types/crud.types'

export const useCrudStore = defineStore('crud', () => {
  const models = ref<EntityModelOption[]>([])
  const modelsLoaded = ref(false)
  const selectedSlug = ref<string>('')
  const schema = ref<AvroSchema | null>(null)
  const items = ref<Record<string, unknown>[]>([])
  const selectedItem = ref<Record<string, unknown> | null>(null)

  const page = ref(1)
  const pageSize = ref(10)
  const totalPages = ref(1)
  const totalData = ref(0)

  const loadingModels = ref(false)
  const loadingList = ref(false)
  const loadingSchema = ref(false)
  const loadingDetail = ref(false)
  const submitting = ref(false)
  const error = ref<string | null>(null)

  async function fetchModels(force = false): Promise<EntityModelOption[]> {
    if (modelsLoaded.value && !force) {
      return models.value
    }
    loadingModels.value = true
    error.value = null
    try {
      const list = await crudApi.listModels()
      models.value = Array.isArray(list) ? list : []
      modelsLoaded.value = true
      if (!selectedSlug.value && models.value.length > 0) {
        selectedSlug.value = models.value[0].slug
      }
      return models.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to load models'
      throw err
    } finally {
      loadingModels.value = false
    }
  }

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

  async function createItem(
    payload: Record<string, unknown>,
    slug = selectedSlug.value,
  ): Promise<Record<string, unknown>> {
    submitting.value = true
    error.value = null
    try {
      const response = await crudApi.createEntity(slug, payload)
      await fetchList(slug, 1, pageSize.value)
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to create record'
      throw err
    } finally {
      submitting.value = false
    }
  }

  async function updateItem(
    id: string | number,
    payload: Record<string, unknown>,
    slug = selectedSlug.value,
  ): Promise<Record<string, unknown>> {
    submitting.value = true
    error.value = null
    try {
      const response = await crudApi.updateEntity(slug, id, payload)
      await fetchList(slug, page.value, pageSize.value)
      return response.data
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to update record'
      throw err
    } finally {
      submitting.value = false
    }
  }

  async function deleteItem(id: string | number, slug = selectedSlug.value): Promise<void> {
    submitting.value = true
    error.value = null
    try {
      await crudApi.deleteEntity(slug, id)
      const nextPage = items.value.length <= 1 && page.value > 1 ? page.value - 1 : page.value
      await fetchList(slug, nextPage, pageSize.value)
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'Failed to delete record'
      throw err
    } finally {
      submitting.value = false
    }
  }

  function clearDetail(): void {
    selectedItem.value = null
  }

  return {
    models,
    modelsLoaded,
    selectedSlug,
    schema,
    items,
    selectedItem,
    page,
    pageSize,
    totalPages,
    totalData,
    loadingModels,
    loadingList,
    loadingSchema,
    loadingDetail,
    submitting,
    error,
    fetchModels,
    fetchSchema,
    fetchList,
    selectModel,
    fetchDetail,
    createItem,
    updateItem,
    deleteItem,
    clearDetail,
  }
})
