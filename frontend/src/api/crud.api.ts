import { httpClient } from '@/api/http'
import type {
  AvroSchema,
  DataListResponse,
  DataResponse,
  EntityModelOption,
} from '@/types/crud.types'

export async function listModels(): Promise<EntityModelOption[]> {
  const { data } = await httpClient.get<EntityModelOption[]>('/api/v1/data/models/')
  return data
}

export async function describeEntity(slug: string): Promise<AvroSchema> {
  const { data } = await httpClient.get<AvroSchema>(`/api/v1/data/${slug}/describe`)
  return data
}

export async function listEntities<T = Record<string, unknown>>(
  slug: string,
  page = 1,
  pageSize = 10,
): Promise<DataListResponse<T>> {
  const { data } = await httpClient.get<DataListResponse<T>>(`/api/v1/data/${slug}/`, {
    params: { _page: page, _pageSize: pageSize },
  })
  return data
}

export async function retrieveEntity<T = Record<string, unknown>>(
  slug: string,
  id: string | number,
): Promise<DataResponse<T>> {
  const { data } = await httpClient.get<DataResponse<T>>(`/api/v1/data/${slug}/${id}`)
  return data
}

export async function createEntity<T = Record<string, unknown>>(
  slug: string,
  payload: Record<string, unknown>,
): Promise<DataResponse<T>> {
  const { data } = await httpClient.post<DataResponse<T>>(`/api/v1/data/${slug}/`, payload)
  return data
}

export async function updateEntity<T = Record<string, unknown>>(
  slug: string,
  id: string | number,
  payload: Record<string, unknown>,
): Promise<DataResponse<T>> {
  const { data } = await httpClient.put<DataResponse<T>>(`/api/v1/data/${slug}/${id}`, payload)
  return data
}

export async function deleteEntity(slug: string, id: string | number): Promise<void> {
  await httpClient.delete(`/api/v1/data/${slug}/${id}`)
}
