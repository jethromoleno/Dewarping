import { useRef, useState } from 'react'

export default function ImageUploader({ onUpload, loading }) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef(null)

  const handleFile = (file) => {
    if (file && file.type.startsWith('image/')) {
      onUpload(file)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    handleFile(file)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  return (
    <div
      className={`
        card-hover cursor-pointer transition-all duration-300
        flex flex-col items-center justify-center py-20
        border-2 border-dashed
        ${dragOver
          ? 'border-accent bg-accent/5 shadow-[0_0_30px_rgba(220,38,38,0.1)]'
          : 'border-surface-border hover:border-gray-500'
        }
      `}
      onClick={() => inputRef.current?.click()}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={(e) => handleFile(e.target.files[0])}
        disabled={loading}
      />

      <div className={`
        w-20 h-20 rounded-2xl flex items-center justify-center mb-6
        transition-all duration-300
        ${dragOver
          ? 'bg-accent/10 scale-110'
          : 'bg-surface-elevated'
        }
      `}>
        <svg
          className={`w-10 h-10 transition-colors duration-300 ${dragOver ? 'text-accent' : 'text-gray-500'}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
          />
        </svg>
      </div>

      <h3 className="text-lg font-semibold text-white mb-2">
        {dragOver ? 'Drop image here' : 'Upload an image'}
      </h3>
      <p className="text-gray-500 text-sm mb-4">
        Drag and drop or click to browse
      </p>
      <p className="text-gray-600 text-xs">
        PNG, JPG, JPEG, or WebP
      </p>
    </div>
  )
}
