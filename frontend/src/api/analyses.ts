import client from './client'

export interface ProductResult {
  article: string
  name: string
  category: string
  purchase_price: number
  sale_price: number
  weight: number
  sold: number
  returns: number
  net_revenue: number
  commission: number
  logistics_total: number
  purchase_cost: number
  profit: number
  margin_pct: number
  margin_zone: 'green' | 'yellow' | 'red'
}

export interface AnalysisStatus {
  analysis_id: number
  status: 'processing' | 'done' | 'failed'
  created_at: string
  files_meta: Record<string, unknown> | null
  results: ProductResult[] | null
}

export interface HistoryItem {
  analysis_id: number
  status: string
  created_at: string
  files_meta: Record<string, unknown> | null
}

export async function createAnalysis(
  purchasesFile: File,
  salesFile: File,
): Promise<{ analysis_id: number; status: string }> {
  const form = new FormData()
  form.append('purchases_file', purchasesFile)
  form.append('sales_file', salesFile)
  const { data } = await client.post('/analyses', form)
  return data
}

export async function getAnalysisStatus(id: number): Promise<AnalysisStatus> {
  const { data } = await client.get<AnalysisStatus>(`/analyses/${id}`)
  return data
}

export async function getHistory(): Promise<HistoryItem[]> {
  const { data } = await client.get<HistoryItem[]>('/analyses')
  return data
}

export async function interpretAnalysis(id: number): Promise<{ interpretation: string }> {
  const { data } = await client.post(`/analyses/${id}/interpret`)
  return data
}

export async function chatWithAnalysis(
  id: number,
  message: string,
): Promise<{ reply: string }> {
  const { data } = await client.post(`/analyses/${id}/chat`, { message })
  return data
}
