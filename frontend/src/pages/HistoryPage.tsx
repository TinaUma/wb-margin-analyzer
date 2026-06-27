import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getHistory } from '../api/analyses'
import type { HistoryItem } from '../api/analyses'

const STATUS_LABEL: Record<string, string> = {
  done: 'Готов',
  processing: 'Обработка',
  failed: 'Ошибка',
}

const STATUS_CLS: Record<string, string> = {
  done: 'bg-green-100 text-green-800',
  processing: 'bg-blue-100 text-blue-800',
  failed: 'bg-red-100 text-red-800',
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getHistory()
      .then(setItems)
      .catch(() => setError('Не удалось загрузить историю'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">История анализов</h1>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="bg-blue-500 hover:bg-blue-600 text-white text-sm px-4 py-2 rounded-lg font-medium transition-colors"
          >
            + Новый анализ
          </button>
        </div>

        {loading && (
          <div className="text-center py-12 text-gray-400">Загружаем…</div>
        )}
        {error && (
          <div className="text-center py-12 text-red-500">{error}</div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-lg">Нет анализов</p>
            <p className="text-sm mt-1">Загрузите первый файл, чтобы начать</p>
          </div>
        )}

        <div className="space-y-3">
          {items.map((item) => {
            const meta = item.files_meta as Record<string, string> | null
            const date = new Date(item.created_at).toLocaleString('ru', {
              day: '2-digit', month: 'short', year: 'numeric',
              hour: '2-digit', minute: '2-digit',
            })
            return (
              <div
                key={item.analysis_id}
                onClick={() => item.status === 'done' && navigate(`/dashboard/${item.analysis_id}`)}
                className={`bg-white rounded-xl border border-gray-200 p-4 flex items-center justify-between
                  ${item.status === 'done' ? 'cursor-pointer hover:border-blue-300 transition-colors' : ''}`}
              >
                <div>
                  <p className="text-sm font-medium text-gray-800">Анализ #{item.analysis_id}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{date}</p>
                  {meta?.purchases_filename && (
                    <p className="text-xs text-gray-400">{meta.purchases_filename}</p>
                  )}
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full ${STATUS_CLS[item.status] ?? 'bg-gray-100 text-gray-700'}`}>
                  {STATUS_LABEL[item.status] ?? item.status}
                </span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
