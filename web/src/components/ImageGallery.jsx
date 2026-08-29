import { useState } from 'react'

export default function ImageGallery({ images }) {
  const [selected, setSelected] = useState(0)
  const [loaded, setLoaded] = useState({})

  if (!images.length) {
    return (
      <div className="glass-card rounded-xl p-8 text-center text-slate-500">
        暂无图片
      </div>
    )
  }

  const labels = ['产品主图', '细节展示', '场景氛围']

  const handleDownload = async (url, index) => {
    try {
      const res = await fetch(url)
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `product_${labels[index] || index + 1}.png`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch {
      window.open(url, '_blank')
    }
  }

  return (
    <div className="space-y-3 h-full flex flex-col">
      {/* 主图 */}
      <div className="glass-card rounded-xl overflow-hidden relative flex-1">
        {!loaded[selected] && (
          <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-white/0 animate-pulse flex items-center justify-center">
            <span className="text-slate-500 text-sm">加载中...</span>
          </div>
        )}
        <img
          src={images[selected]}
          alt={labels[selected] || '产品图'}
          className={`w-full aspect-[3/4] object-cover transition-opacity duration-500 ${loaded[selected] ? 'opacity-100' : 'opacity-0'}`}
          onLoad={() => setLoaded(prev => ({ ...prev, [selected]: true }))}
          onError={(e) => { e.target.src = 'https://placehold.co/600x800/1e1e2e/666?text=Loading...'; setLoaded(prev => ({ ...prev, [selected]: true })) }}
        />
        {/* 下载按钮 */}
        <button
          onClick={() => handleDownload(images[selected], selected)}
          className="absolute bottom-3 right-3 bg-black/60 hover:bg-black/80 text-white text-xs px-3 py-1.5 rounded-lg backdrop-blur-sm transition-all hover:scale-105"
        >
          ⬇ 下载
        </button>
      </div>

      {/* 缩略图 */}
      <div className="flex gap-2">
        {images.map((url, i) => (
          <button
            key={i}
            onClick={() => setSelected(i)}
            className={`flex-1 rounded-lg overflow-hidden border-2 transition-all ${
              i === selected ? 'border-blue-500 scale-105' : 'border-transparent opacity-60 hover:opacity-100'
            }`}
          >
            <img
              src={url}
              alt={labels[i] || `图${i + 1}`}
              className={`w-full aspect-square object-cover transition-opacity duration-500 ${loaded[i] ? 'opacity-100' : 'opacity-0'}`}
              onLoad={() => setLoaded(prev => ({ ...prev, [i]: true }))}
              onError={(e) => { e.target.src = 'https://placehold.co/200x200/1e1e2e/666?text=' + (i + 1) }}
            />
            <div className="text-xs text-center py-1 text-slate-400 bg-black/40">
              {labels[i] || `图${i + 1}`}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
