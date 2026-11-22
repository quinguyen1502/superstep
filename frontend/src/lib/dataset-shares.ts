import type { CellValue, DatasetColumn, DatasetFilters, DatasetPage } from '@/lib/datasets'

export const DATASET_SHARE_PAGE = '/dataset-view'
export const DATASET_SHARE_API = '/api/public/v1/dataset-view'
export const DATASET_SHARE_HEADER = 'X-Dataset-Share'
export const DATASET_SHARE_PAGE_SIZE = 50

export const isDatasetSharePage = (pathname: string) =>
  pathname.toLowerCase().replace(/\/+$/, '') === DATASET_SHARE_PAGE

export function datasetShareToken(hash: string): string {
  const token = hash.slice(1)
  return /^dssh_[A-Za-z0-9_-]{43}$/.test(token) ? token : ''
}

export function datasetShareUrl(token: string): string {
  const url = new URL(DATASET_SHARE_PAGE, location.origin)
  url.hash = token
  return url.href
}

export type DatasetShareInput = {
  name: string
  fields: string[]
  filter_tree: DatasetFilters | null
  schema_revision: number
}

export type DatasetShare = Pick<DatasetShareInput, 'name' | 'fields' | 'filter_tree'> & {
  id: string
  available: boolean
}

export type DatasetShareView = {
  name: string
  columns: Pick<DatasetColumn, 'key' | 'label' | 'kind'>[]
  searchable: boolean
}

export type DatasetShareRows = DatasetPage<Record<string, CellValue>>
export type DatasetSharePreview = DatasetShareRows & { view: DatasetShareView }
