import { useState } from 'react'
import type { ProductResult } from '../api/analyses'

interface Props {
  products: ProductResult[]
}

function calcMargin(p: ProductResult, newPrice: number, newCost: number): number {
  const netSold = p.sold - p.returns
  const revenue = newPrice * netSold
  const purchaseCost = newCost * netSold
  const profit = revenue - Number(p.commission) - Number(p.logistics_total) - purchaseCost
  if (revenue <= 0) return 0
  return (profit / revenue) * 100
}

function zone(m: number) {
  if (m >= 25) return { label: 'Зелёная', cls: 'text-green-600' }
  if (m >= 10) return { label: 'Жёлтая', cls: 'text-yellow-600' }
  return { label: 'Красная', cls: 'text-red-600' }
}

export default function WhatIfPanel({ products }: Props) {
  const [selectedIdx, setSelectedIdx] = useState(0)
  const p = products[selectedIdx]

  const [price, setPrice] = useState(Math.round(Number(p.sale_price)))
  const [cost, setCost] = useState(Math.round(Number(p.purchase_price)))

  function onSelect(idx: number) {
    setSelectedIdx(idx)
    setPrice(Math.round(Number(products[idx].sale_price)))
    setCost(Math.round(Number(products[idx].purchase_price)))
  }

  const newMargin = calcMargin(p, price, cost)
  const origMargin = Number(p.margin_pct)
  const diff = newMargin - origMargin
  const z = zone(newMargin)

  const maxPrice = Math.round(Number(p.sale_price) * 2)
  const maxCost = Math.round(Number(p.purchase_price) * 2)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
      <h3 className="font-semibold text-gray-800 text-lg">What If — симулятор маржи</h3>

      <select
        className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        value={selectedIdx}
        onChange={(e) => onSelect(Number(e.target.value))}
      >
        {products.map((prod, i) => (
          <option key={prod.article} value={i}>{prod.name}</option>
        ))}
      </select>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Цена продажи</span>
            <span className="font-semibold">{price.toLocaleString('ru')} ₽</span>
          </div>
          <input
            type="range" min={1} max={maxPrice} value={price}
            onChange={(e) => setPrice(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>

        <div>
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>Себестоимость</span>
            <span className="font-semibold">{cost.toLocaleString('ru')} ₽</span>
          </div>
          <input
            type="range" min={1} max={maxCost} value={cost}
            onChange={(e) => setCost(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
        </div>
      </div>

      <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-500">Новая маржа</p>
          <p className={`text-2xl font-bold ${z.cls}`}>{newMargin.toFixed(1)}%</p>
          <p className="text-xs text-gray-400">{z.label}</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">Изменение</p>
          <p className={`text-lg font-semibold ${diff >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {diff >= 0 ? '+' : ''}{diff.toFixed(1)}%
          </p>
          <p className="text-xs text-gray-400">было {origMargin.toFixed(1)}%</p>
        </div>
      </div>
    </div>
  )
}
