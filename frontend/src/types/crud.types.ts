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

export type CrudOperation = 'read' | 'create' | 'update' | 'delete'

export interface EntityModelOption {
  slug: string
  label: string
  datasource: DatasourceType
  allowed_operations: CrudOperation[]
}
