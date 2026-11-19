import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCrudStore } from '@/stores/crud.store'
import * as crudApi from '@/api/crud.api'
import type {
  AvroSchema,
  DataListResponse,
  DataResponse,
  EntityModelOption,
} from '@/types/crud.types'

vi.mock('@/api/crud.api')

const registeredModels: EntityModelOption[] = [
  {
    slug: 'users',
    label: 'Users',
    datasource: 'postgresql',
    allowed_operations: ['read', 'create', 'update', 'delete'],
  },
  {
    slug: 'activity-logs',
    label: 'Activity Logs',
    datasource: 'mongodb',
    allowed_operations: ['read', 'delete'],
  },
]

const usersSchema: AvroSchema = {
  type: 'record',
  name: 'users',
  fields: [
    { name: 'id', type: 'int' },
    { name: 'email', type: 'string' },
    { name: 'first_name', type: 'string' },
  ],
}

describe('crud store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetches registered models dynamically with datasource and allowed_operations', async () => {
    vi.mocked(crudApi.listModels).mockResolvedValueOnce(registeredModels)

    const store = useCrudStore()
    const result = await store.fetchModels()

    expect(crudApi.listModels).toHaveBeenCalledTimes(1)
    expect(result).toEqual(registeredModels)
    expect(store.models).toEqual(registeredModels)
    expect(store.modelsLoaded).toBe(true)
    expect(store.selectedSlug).toBe('users')
  })

  it('loads schema and paginated items for selected entity slug', async () => {
    const listResp: DataListResponse = {
      code: 200,
      data: [{ id: 1, email: 'alice@example.com', first_name: 'Alice' }],
      page: 1,
      page_size: 10,
      total_page: 2,
      total_data: 15,
      message: 'success',
      data_schema: usersSchema,
    }
    vi.mocked(crudApi.describeEntity).mockResolvedValueOnce(usersSchema)
    vi.mocked(crudApi.listEntities).mockResolvedValueOnce(listResp)

    const store = useCrudStore()
    await store.selectModel('users')

    expect(crudApi.describeEntity).toHaveBeenCalledWith('users')
    expect(crudApi.listEntities).toHaveBeenCalledWith('users', 1, 10)
    expect(store.selectedSlug).toBe('users')
    expect(store.schema).toEqual(usersSchema)
    expect(store.items).toHaveLength(1)
    expect(store.totalPages).toBe(2)
    expect(store.totalData).toBe(15)
  })

  it('retrieves a single entity record by id', async () => {
    const detailResp: DataResponse = {
      code: 200,
      data: { id: 1, email: 'alice@example.com', first_name: 'Alice' },
      message: 'success',
      data_schema: usersSchema,
    }
    vi.mocked(crudApi.retrieveEntity).mockResolvedValueOnce(detailResp)

    const store = useCrudStore()
    store.selectedSlug = 'users'
    await store.fetchDetail(1)

    expect(crudApi.retrieveEntity).toHaveBeenCalledWith('users', 1)
    expect(store.selectedItem).toEqual(detailResp.data)
  })

  it('creates an entity record and refreshes the list', async () => {
    const createResp: DataResponse = {
      code: 0,
      data: { id: 2, email: 'bob@example.com', first_name: 'Bob' },
      message: 'created',
    }
    const listResp: DataListResponse = {
      code: 0,
      data: [createResp.data],
      page: 1,
      page_size: 10,
      total_page: 1,
      total_data: 1,
      message: '',
    }
    vi.mocked(crudApi.createEntity).mockResolvedValueOnce(createResp)
    vi.mocked(crudApi.listEntities).mockResolvedValueOnce(listResp)

    const store = useCrudStore()
    store.selectedSlug = 'users'
    const created = await store.createItem({ email: 'bob@example.com', first_name: 'Bob' })

    expect(crudApi.createEntity).toHaveBeenCalledWith('users', {
      email: 'bob@example.com',
      first_name: 'Bob',
    })
    expect(crudApi.listEntities).toHaveBeenCalledWith('users', 1, 10)
    expect(created).toEqual(createResp.data)
    expect(store.items).toEqual([createResp.data])
  })

  it('updates an entity record and refreshes the list', async () => {
    const updateResp: DataResponse = {
      code: 0,
      data: { id: 1, email: 'alice@example.com', first_name: 'Alicia' },
      message: 'updated',
    }
    const listResp: DataListResponse = {
      code: 0,
      data: [updateResp.data],
      page: 1,
      page_size: 10,
      total_page: 1,
      total_data: 1,
      message: '',
    }
    vi.mocked(crudApi.updateEntity).mockResolvedValueOnce(updateResp)
    vi.mocked(crudApi.listEntities).mockResolvedValueOnce(listResp)

    const store = useCrudStore()
    store.selectedSlug = 'users'
    const updated = await store.updateItem(1, { first_name: 'Alicia' })

    expect(crudApi.updateEntity).toHaveBeenCalledWith('users', 1, { first_name: 'Alicia' })
    expect(crudApi.listEntities).toHaveBeenCalledWith('users', 1, 10)
    expect(updated).toEqual(updateResp.data)
  })

  it('deletes an entity record and refreshes the list', async () => {
    const listResp: DataListResponse = {
      code: 0,
      data: [],
      page: 1,
      page_size: 10,
      total_page: 0,
      total_data: 0,
      message: '',
    }
    vi.mocked(crudApi.deleteEntity).mockResolvedValueOnce(undefined)
    vi.mocked(crudApi.listEntities).mockResolvedValueOnce(listResp)

    const store = useCrudStore()
    store.selectedSlug = 'activity-logs'
    await store.deleteItem('6751a1b2c3d4e5f60718293a')

    expect(crudApi.deleteEntity).toHaveBeenCalledWith(
      'activity-logs',
      '6751a1b2c3d4e5f60718293a',
    )
    expect(crudApi.listEntities).toHaveBeenCalledWith('activity-logs', 1, 10)
    expect(store.items).toEqual([])
  })
})
