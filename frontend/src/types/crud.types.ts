export interface AvroField {
  name: string
  type: string
  fields?: AvroSchema
}

export interface AvroSchema {
  type: string
  name: string
  fields: AvroField[]
}

export interface DataResponse<T = Record<string, unknown>> {
  code: number
  data: T
  message: string
  data_schema?: AvroSchema
}

export interface DataListResponse<T = Record<string, unknown>> {
  code: number
  data: T[]
  page: number
  page_size: number
  total_page: number
  total_data: number
  message: string
  data_schema?: AvroSchema
}

export type DatasourceType = 'postgresql' | 'mongodb'

export interface EntityModelOption {
  slug: string
  label: string
  datasource: DatasourceType
}

/**
 * Models registered in the Go reference API (src/config/crudModels.go).
 * In Step 3, this list will be fetched dynamically from Python's GET /api/v1/data/models/.
 */
export const GO_REGISTERED_MODELS: readonly EntityModelOption[] = [
  { slug: 'users', label: 'Users', datasource: 'postgresql' },
  { slug: 'user-tokens', label: 'User Tokens', datasource: 'postgresql' },
  { slug: 'user-permissions', label: 'User Permissions', datasource: 'postgresql' },
] as const
