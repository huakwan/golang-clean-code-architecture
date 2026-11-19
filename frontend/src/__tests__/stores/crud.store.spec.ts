import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useCrudStore } from '@/stores/crud.store'
import * as crudApi from '@/api/crud.api'
import type { AvroSchema, DataListResponse, DataResponse } from '@/types/crud.types'

vi.mock('@/api/crud.api')

const usersSchema: AvroSchema = {
  type: 'record',
  name: 'user-model',
  fields: [
    { name: 'id', type: 'int' },
    { name: 'email', type: 'string' },
    { name: 'first_name', type: 'string' },
  ],
}

describe('crud store (Step 1 read-only)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
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
})
