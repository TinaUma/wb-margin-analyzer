import { useState } from 'react'
import type { ProductResult } from '../api/analyses'

const ZONE_CLASS: Record<string, string> = {
  green: 'bg-green-50',
  yellow: 'bg-yellow-50',
  red: 'bg-red-50',
}

const ZONE_BADGE: Record<string, string> = {
  green: 'bg-green-100 text-green-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  red: 'bg-red-100 text-red-800',
}

const ZONE_LABEL: Record<string, string> = {
  green: 'Зелёная',
  yellow: 'Жёлтая',
  red: 'Красная',
}

type SortKey = 'margin_pct' | 'profit' | 'sale_price'
type SortDir = 'asc' | 'desc'
type Zone = 'all' | 'green' | 'yellow' | 'red'

const PAGE_SIZE = 50

interface Props {
  products: ProductResult[]
}

export default function MarginTable({ products }: Props) {
  const [zone, setZone] = useState<Zone>('all')
  const [sortKey, setSortKey] = useState<SortKey>('margin_pct')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState<ProductResult | null>(null)

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir(sortDir === 'desc' ? 'asc' : 'desc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
    setPage(1)
  }

  const filtered = zone === 'all' ? products : products.filter(p => p.margin_zone === zone)
  const sorted = [...filtered].sort((a, b) => {
    const diff = Number(a[sortKey]) - Number(b[sortKey])
    return sortDir === 'desc' ? -diff : diff
  })

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE))
  const paginated = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  function SortArrow({ col }: { col: SortKey }) {
    if (sortKey !== col) return <span className="ml-1 text-gray-300">↕</span>
    return <span className="ml-1">{sortDir === 'desc' ? '↓' : '↑'}</span>
  }

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-4 text-xs text-gray-600 bg-gray-50 rounded-lg px-4 py-2 border border-gray-100">
        <span className="font-medium text-gray-500">Зоны маржинальности:</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-green-400 mr-1" />Зелёная ≥ 25%</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-yellow-400 mr-1" />Жёлтая 10–25%</span>
        <span><span className="inline-block w-2.5 h-2.5 rounded-full bg-red-400 mr-1" />Красная &lt; 10%</span>
      </div>

      {/* Zone filter */}
      <div className="flex gap-2 flex-wrap">
        {(['all', 'green', 'yellow', 'red'] as const).map(z => {
          const counts = z === 'all' ? products.length : products.filter(p => p.margin_zone === z).length
          const active = zone === z
          const cls = active
            ? z === 'green' ? 'bg-green-500 text-white'
              : z === 'yellow' ? 'bg-yellow-400 text-white'
              : z === 'red' ? 'bg-red-500 text-white'
              : 'bg-blue-500 text-white'
            : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-300'
          return (
            <button
              key={z}
              onClick={() => { setZone(z); setPage(1) }}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${cls}`}
            >
              {z === 'all' ? 'Все' : ZONE_LABEL[z]} ({counts})
            </button>
          )
        })}
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-gray-600 uppercase text-xs">
            <tr>
              <th className="px-4 py-3 text-left">Товар</th>
              <th
                className="px-4 py-3 text-right cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort('sale_price')}
              >
                Цена <SortArrow col="sale_price" />
              </th>
              <th className="px-4 py-3 text-right">Продано</th>
              <th
                className="px-4 py-3 text-right cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort('profit')}
              >
                Прибыль ₽ <SortArrow col="profit" />
              </th>
              <th
                className="px-4 py-3 text-right cursor-pointer select-none hover:text-gray-900"
                onClick={() => toggleSort('margin_pct')}
              >
                Маржа % <SortArrow col="margin_pct" />
              </th>
              <th className="px-4 py-3 text-center">Зона</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {paginated.map((p) => (
              <tr
                key={p.article}
                className={`${ZONE_CLASS[p.margin_zone]} cursor-pointer hover:brightness-95 transition-all`}
                onClick={() => setSelected(p)}
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900">{p.name}</div>
                  <div className="text-xs text-gray-400">{p.article}</div>
                </td>
                <td className="px-4 py-3 text-right text-gray-700">{Number(p.sale_price).toLocaleString('ru')} ₽</td>
                <td className="px-4 py-3 text-right text-gray-700">{p.sold}</td>
                <td className="px-4 py-3 text-right font-medium text-gray-900">
                  {Number(p.profit).toLocaleString('ru')} ₽
                </td>
                <td className="px-4 py-3 text-right font-bold text-gray-900">
                  {Number(p.margin_pct).toFixed(1)}%
                </td>
                <td className="px-4 py-3 text-center">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${ZONE_BADGE[p.margin_zone]}`}>
                    {ZONE_LABEL[p.margin_zone]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-500">
          <span>{filtered.length} товаров · стр. {page} из {totalPages}</span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              ← Назад
            </button>
            <button
              onClick={() => setPage(p => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="px-3 py-1 rounded border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
            >
              Вперёд →
            </button>
          </div>
        </div>
      )}

      {/* Product modal */}
      {selected && (
        <ProductModal product={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

function ProductModal({ product: p, onClose }: { product: ProductResult; onClose: () => void }) {
  const fmt = (n: number) => Number(n).toLocaleString('ru')
  const rows: [string, string][] = [
    ['Артикул', p.article],
    ['Категория', p.category],
    ['Закупочная цена', `${fmt(p.purchase_price)} ₽`],
    ['Цена продажи', `${fmt(p.sale_price)} ₽`],
    ['Вес', `${p.weight} кг`],
    ['Продано шт.', String(p.sold)],
    ['Возвраты шт.', String(p.returns)],
    ['Чистая выручка', `${fmt(p.net_revenue)} ₽`],
    ['Комиссия WB', `${fmt(p.commission)} ₽`],
    ['Логистика', `${fmt(p.logistics_total)} ₽`],
    ['Затраты на закупку', `${fmt(p.purchase_cost)} ₽`],
    ['Прибыль', `${fmt(p.profit)} ₽`],
    ['Маржинальность', `${Number(p.margin_pct).toFixed(1)}%`],
  ]

  return (
    <div
      className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-xl max-w-md w-full max-h-[90vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}
      >
        <div className={`px-6 py-4 rounded-t-2xl flex items-start justify-between ${ZONE_CLASS[p.margin_zone]}`}>
          <div>
            <h2 className="font-bold text-gray-900 text-base leading-tight">{p.name}</h2>
            <span className={`mt-1 inline-block px-2 py-0.5 rounded-full text-xs font-medium ${ZONE_BADGE[p.margin_zone]}`}>
              {ZONE_LABEL[p.margin_zone]}
            </span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none ml-4">✕</button>
        </div>
        <div className="px-6 py-4">
          <dl className="divide-y divide-gray-100">
            {rows.map(([label, value]) => (
              <div key={label} className="flex justify-between py-2 text-sm">
                <dt className="text-gray-500">{label}</dt>
                <dd className="font-medium text-gray-900">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </div>
  )
}
