import { useRef, useState } from 'react'
import type { DragEvent } from 'react'

interface Props {
  label: string
  file: File | null
  onChange: (f: File) => void
}

export default function FileDropzone({ label, file, onChange }: Props) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) onChange(f)
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={handleDrop}
      onClick={() => inputRef.current?.click()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors
        ${dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-blue-400'}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".xlsx,.xls"
        className="hidden"
        onChange={(e) => { const f = e.target.files?.[0]; if (f) onChange(f) }}
      />
      <p className="text-sm font-medium text-gray-600">{label}</p>
      {file ? (
        <p className="mt-2 text-sm text-blue-600 font-semibold">{file.name}</p>
      ) : (
        <p className="mt-2 text-xs text-gray-400">Перетащите .xlsx файл или нажмите</p>
      )}
    </div>
  )
}
