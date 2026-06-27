import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import FileDropzone from '../components/FileDropzone'
import { createAnalysis } from '../api/analyses'
import client from '../api/client'

type FileStatus = 'idle' | 'ok' | 'error'

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} КБ`
  return `${(bytes / 1024 / 1024).toFixed(1)} МБ`
}

export default function UploadPage() {
  const navigate = useNavigate()
  const [purchasesFile, setPurchasesFile] = useState<File | null>(null)
  const [salesFile, setSalesFile] = useState<File | null>(null)
  const [fileStatus, setFileStatus] = useState<FileStatus>('idle')
  const [validating, setValidating] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function validateBoth(p: File, s: File) {
    setValidating(true)
    setFileStatus('idle')
    setError(null)
    const form = new FormData()
    form.append('purchases_file', p)
    form.append('sales_file', s)
    try {
      await client.post('/uploads/validate', form)
      setFileStatus('ok')
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        .response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Ошибка валидации файлов')
      setFileStatus('error')
    } finally {
      setValidating(false)
    }
  }

  function handlePurchasesChange(file: File) {
    setPurchasesFile(file)
    setFileStatus('idle')
    if (salesFile) validateBoth(file, salesFile)
  }

  function handleSalesChange(file: File) {
    setSalesFile(file)
    setFileStatus('idle')
    if (purchasesFile) validateBoth(purchasesFile, file)
  }

  async function handleSubmit() {
    if (!purchasesFile || !salesFile) return
    setError(null)
    setSubmitting(true)
    try {
      const { analysis_id } = await createAnalysis(purchasesFile, salesFile)
      navigate(`/dashboard/${analysis_id}`)
    } catch {
      setError('Не удалось запустить анализ. Проверьте файлы.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 py-10 px-4">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Новый анализ</h1>
            <p className="text-sm text-gray-500 mt-1">Загрузите файлы закупок и продаж</p>
          </div>
          <button
            onClick={() => navigate('/history')}
            className="text-sm text-blue-500 hover:underline"
          >
            История →
          </button>
        </div>

        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Файл закупок</h2>
            <FileDropzone label="Закупки (.xlsx)" file={purchasesFile} onChange={handlePurchasesChange} />
            {purchasesFile && (
              <FileBadge file={purchasesFile} status={validating ? 'idle' : fileStatus} />
            )}
          </div>

          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Файл продаж</h2>
            <FileDropzone label="Продажи (.xlsx)" file={salesFile} onChange={handleSalesChange} />
            {salesFile && (
              <FileBadge file={salesFile} status={validating ? 'idle' : fileStatus} />
            )}
          </div>
        </div>

        {validating && (
          <div className="mt-4 flex items-center gap-2 text-sm text-blue-600">
            <span className="inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            Проверяем файлы на сервере…
          </div>
        )}

        {error && (
          <div className="mt-4 bg-red-50 border border-red-200 rounded-lg p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={!purchasesFile || !salesFile || submitting || validating}
          className="mt-6 w-full bg-blue-500 hover:bg-blue-600 disabled:opacity-50 text-white rounded-lg py-3 text-sm font-semibold transition-colors"
        >
          {submitting ? 'Запускаем анализ…' : 'Запустить анализ'}
        </button>
      </div>
    </div>
  )
}

function FileBadge({ file, status }: { file: File; status: FileStatus }) {
  return (
    <div className="mt-3 flex items-center gap-2 text-xs text-gray-600">
      {status === 'ok' && <span className="text-green-600 text-base">✓</span>}
      {status === 'error' && <span className="text-red-500 text-base">✕</span>}
      {status === 'idle' && <span className="text-gray-300 text-base">·</span>}
      <span className="font-medium text-gray-800">{file.name}</span>
      <span className="text-gray-400">{formatSize(file.size)}</span>
    </div>
  )
}
