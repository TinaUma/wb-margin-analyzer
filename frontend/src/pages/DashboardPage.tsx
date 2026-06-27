import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getAnalysisStatus, interpretAnalysis } from '../api/analyses'
import type { ProductResult } from '../api/analyses'
import client from '../api/client'
import MarginTable from '../components/MarginTable'
import WhatIfPanel from '../components/WhatIfPanel'
import ChatBlock from '../components/ChatBlock'

type Status = 'processing' | 'done' | 'failed'

export default function DashboardPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const analysisId = Number(id)

  const [status, setStatus] = useState<Status>('processing')
  const [products, setProducts] = useState<ProductResult[]>([])
  const [interpretation, setInterpretation] = useState<string | null>(null)
  const [interpreting, setInterpreting] = useState(false)
  const [tab, setTab] = useState<'table' | 'whatif' | 'chat'>('table')

  useEffect(() => {
    if (!analysisId) return
    const interval = setInterval(async () => {
      try {
        const data = await getAnalysisStatus(analysisId)
        setStatus(data.status)
        if (data.status === 'done') {
          setProducts(data.results ?? [])
          clearInterval(interval)
        } else if (data.status === 'failed') {
          clearInterval(interval)
        }
      } catch {
        clearInterval(interval)
      }
    }, 2000)
    return () => clearInterval(interval)
  }, [analysisId])

  async function handleExport() {
    const resp = await client.get(`/analyses/${analysisId}/export`, { responseType: 'blob' })
    const url = URL.createObjectURL(resp.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `analysis_${analysisId}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  }

  async function handleInterpret() {
    setInterpreting(true)
    try {
      const { interpretation: text } = await interpretAnalysis(analysisId)
      setInterpretation(text)
      setTab('chat')
    } finally {
      setInterpreting(false)
    }
  }

  const sorted = [...products].sort((a, b) => Number(b.profit) - Number(a.profit))
  const top3 = sorted.slice(0, 3)
  const bottom3 = sorted.slice(-3).reverse()

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center gap-4 mb-6">
          <button onClick={() => navigate('/upload')} className="text-sm text-gray-400 hover:text-gray-600">← Новый</button>
          <button onClick={() => navigate('/history')} className="text-sm text-gray-400 hover:text-gray-600">История</button>
          <div className="flex-1" />
          <span className="text-xs text-gray-400">Анализ #{analysisId}</span>
        </div>

        {status === 'processing' && (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
            <div className="inline-block w-8 h-8 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-gray-600 font-medium">Анализируем данные…</p>
            <p className="text-sm text-gray-400 mt-1">Обычно занимает несколько секунд</p>
          </div>
        )}

        {status === 'failed' && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-8 text-center text-red-600">
            Анализ завершился с ошибкой. Попробуйте загрузить файлы снова.
          </div>
        )}

        {status === 'done' && products.length > 0 && (
          <div className="space-y-6">
            {/* Top / Bottom 3 */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <TopCard title="Топ-3 прибыльных" products={top3} color="green" />
              <TopCard title="Топ-3 убыточных" products={bottom3} color="red" />
            </div>

            {/* Action buttons */}
            <div className="flex gap-3">
              {!interpretation && (
                <button
                  onClick={handleInterpret}
                  disabled={interpreting}
                  className="flex-1 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 text-white rounded-lg py-3 text-sm font-semibold transition-colors"
                >
                  {interpreting ? 'AI анализирует…' : '✨ Получить AI-интерпретацию'}
                </button>
              )}
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-5 py-3 bg-white border border-gray-200 hover:border-gray-300 hover:bg-gray-50 text-gray-700 rounded-lg text-sm font-semibold transition-colors"
              >
                ↓ Скачать Excel
              </button>
            </div>

            {/* Tabs */}
            <div className="bg-white rounded-xl border border-gray-200">
              <div className="flex border-b border-gray-100">
                {(['table', 'whatif', 'chat'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTab(t)}
                    className={`px-5 py-3 text-sm font-medium transition-colors ${
                      tab === t
                        ? 'border-b-2 border-blue-500 text-blue-600'
                        : 'text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    {t === 'table' ? 'Таблица' : t === 'whatif' ? 'What If' : 'AI Чат'}
                  </button>
                ))}
              </div>

              <div className="p-4">
                {tab === 'table' && <MarginTable products={products} />}
                {tab === 'whatif' && <WhatIfPanel products={products} />}
                {tab === 'chat' && (
                  <div className="space-y-4">
                    {interpretation && (
                      <div className="bg-indigo-50 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap">
                        {interpretation}
                      </div>
                    )}
                    <ChatBlock analysisId={analysisId} />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function TopCard({
  title, products, color,
}: {
  title: string
  products: ProductResult[]
  color: 'green' | 'red'
}) {
  const cls = color === 'green'
    ? 'bg-green-50 border-green-200'
    : 'bg-red-50 border-red-200'
  const textCls = color === 'green' ? 'text-green-700' : 'text-red-700'

  return (
    <div className={`rounded-xl border p-4 ${cls}`}>
      <h3 className={`text-sm font-semibold mb-3 ${textCls}`}>{title}</h3>
      <div className="space-y-2">
        {products.map((p) => (
          <div key={p.article} className="flex justify-between items-center text-sm">
            <span className="text-gray-700 truncate max-w-[60%]">{p.name}</span>
            <span className={`font-bold ${textCls}`}>{Number(p.margin_pct).toFixed(1)}%</span>
          </div>
        ))}
      </div>
    </div>
  )
}
