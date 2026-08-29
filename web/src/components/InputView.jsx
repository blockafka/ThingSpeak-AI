import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import DnaDashboard from './DnaDashboard'

const PRODUCT_CATEGORIES = [
  '果干蜜饯', '茶', '肉制品', '零食', '调味品',
  '酒水饮料', '糕点', '粮油', '滋补养生', '乳制品',
  '手工艺品', '文创周边', '服饰配件', '家居用品',
]

const INITIAL_FORM = {
  product_name: '',
  product_category: '',
  origin_place: '',
  target_audience: '',
  selling_scene: '',
  user_note: '',
}

const MAX_IMAGES = 3

function CategoryInput({ value, onChange }) {
  const [open, setOpen] = useState(false)
  const [dropdownStyle, setDropdownStyle] = useState({})
  const inputRef = useRef(null)
  const wrapperRef = useRef(null)

  const filtered = PRODUCT_CATEGORIES.filter(c =>
    c.includes(value.trim()) && c !== value.trim()
  )

  const updatePosition = () => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect()
      setDropdownStyle({
        top: rect.bottom + window.scrollY + 4,
        left: rect.left + window.scrollX,
        width: rect.width,
      })
    }
  }

  useEffect(() => {
    if (open) {
      updatePosition()
      window.addEventListener('resize', updatePosition)
      window.addEventListener('scroll', updatePosition, true)
      return () => {
        window.removeEventListener('resize', updatePosition)
        window.removeEventListener('scroll', updatePosition, true)
      }
    }
  }, [open])

  const handleSelect = (cat) => {
    onChange(cat)
    setOpen(false)
  }

  const dropdown = open && filtered.length > 0 && (
    <div
      style={dropdownStyle}
      className="fixed z-[9999] max-h-52 overflow-y-auto rounded-xl border border-white/10 bg-[#12121a] shadow-xl"
    >
      {filtered.map(cat => (
        <div
          key={cat}
          onMouseDown={(e) => { e.preventDefault(); handleSelect(cat) }}
          onTouchStart={() => handleSelect(cat)}
          className="px-3 py-2 text-sm text-slate-300 hover:bg-amber-400/10 hover:text-amber-200 cursor-pointer first:rounded-t-xl last:rounded-b-xl transition-colors"
        >
          {cat}
        </div>
      ))}
    </div>
  )

  return (
    <div ref={wrapperRef} className="relative">
      <label className="block text-xs text-slate-500 mb-1.5">
        产品品类 <span className="text-rose-400">*</span>
      </label>
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => { onChange(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
        placeholder="例如：果干蜜饯"
        autoComplete="off"
      />
      {typeof document !== 'undefined' && createPortal(dropdown, document.body)}
    </div>
  )
}

function ImageUploader({ images, onChange }) {
  const inputRef = useRef(null)

  const handleFiles = (fileList) => {
    const files = Array.from(fileList || [])
    const remaining = MAX_IMAGES - images.length
    const toAdd = files.slice(0, remaining)
    if (toAdd.length === 0) return

    const newImages = toAdd.map(file => ({
      file,
      url: URL.createObjectURL(file),
      name: file.name,
    }))
    onChange([...images, ...newImages])
  }

  const removeImage = (index) => {
    const next = images.filter((_, i) => i !== index)
    URL.revokeObjectURL(images[index].url)
    onChange(next)
  }

  return (
    <div>
      <label className="block text-xs text-slate-500 mb-2">
        产品图片（最多 {MAX_IMAGES} 张，可选）
      </label>

      <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
        {images.map((img, index) => (
          <div
            key={index}
            className="relative aspect-square rounded-xl overflow-hidden bg-white/5 border border-white/10 group"
          >
            <img
              src={img.url}
              alt={img.name}
              className="w-full h-full object-cover"
            />
            <button
              type="button"
              onClick={() => removeImage(index)}
              className="absolute top-1 right-1 w-6 h-6 rounded-full bg-black/60 text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
            >
              ✕
            </button>
            <div className="absolute bottom-0 left-0 right-0 bg-black/50 text-[10px] text-white px-1.5 py-0.5 truncate">
              图 {index + 1}
            </div>
          </div>
        ))}

        {images.length < MAX_IMAGES && (
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="aspect-square rounded-xl border-2 border-dashed border-white/15 bg-white/5 hover:border-amber-400/40 hover:bg-amber-400/5 transition-all flex flex-col items-center justify-center text-slate-400 hover:text-amber-300"
          >
            <div className="text-2xl mb-1">+</div>
            <div className="text-xs">上传图片</div>
          </button>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <p className="mt-2 text-[11px] text-slate-500">
        • 上传产品特写、包装、产地等图片，AI 会读图理解产品特点
        <br />
        • 不上传也可以生成，纯文字输入同样可用
      </p>
    </div>
  )
}

export default function InputView({ onGenerate }) {
  const [form, setForm] = useState(INITIAL_FORM)
  const [images, setImages] = useState([])
  const [loading, setLoading] = useState(false)

  const update = (key, value) => setForm(prev => ({ ...prev, [key]: value }))

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!form.product_name.trim() || !form.product_category || !form.origin_place.trim() || !form.target_audience.trim()) {
      return
    }
    setLoading(true)
    onGenerate({ ...form, images })
  }

  return (
    <div className="animate-fade-in-up">
      <div className="mb-8 max-w-3xl mx-auto">
      </div>

      {/* DNA 进化仪表盘 */}
      <div className="mb-5 max-w-3xl mx-auto">
        <DnaDashboard />
      </div>

      <form onSubmit={handleSubmit} className="space-y-5 max-w-3xl mx-auto">
        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-medium text-slate-300 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-amber-400/20 text-amber-300 text-xs flex items-center justify-center font-bold">1</span>
            产品基本信息
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1.5">
                产品名称 <span className="text-rose-400">*</span>
              </label>
              <input
                value={form.product_name}
                onChange={(e) => update('product_name', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
                placeholder="例如：贵州刺梨果干"
              />
            </div>
            <CategoryInput
              value={form.product_category}
              onChange={(v) => update('product_category', v)}
            />
            <div>
              <label className="block text-xs text-slate-500 mb-1.5">
                产地 <span className="text-rose-400">*</span>
              </label>
              <input
                value={form.origin_place}
                onChange={(e) => update('origin_place', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
                placeholder="例如：贵州贵阳"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1.5">
                目标人群 <span className="text-rose-400">*</span>
              </label>
              <input
                value={form.target_audience}
                onChange={(e) => update('target_audience', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
                placeholder="例如：年轻白领、宝妈、长辈游客"
              />
            </div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-medium text-slate-300 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-amber-400/20 text-amber-300 text-xs flex items-center justify-center font-bold">2</span>
            场景与补充说明
          </h2>

          <div className="space-y-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1.5">使用场景</label>
              <input
                value={form.selling_scene}
                onChange={(e) => update('selling_scene', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors"
                placeholder="例如：中秋送礼、办公室解馋、旅游伴手礼"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1.5">补充说明</label>
              <textarea
                value={form.user_note}
                onChange={(e) => update('user_note', e.target.value)}
                rows={3}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-white text-sm focus:border-amber-400 focus:outline-none transition-colors resize-none"
                placeholder="例如：突出高维C健康卖点，包装有苗族纹样设计，适合送朋友"
              />
            </div>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h2 className="text-sm font-medium text-slate-300 mb-4 flex items-center gap-2">
            <span className="w-6 h-6 rounded-full bg-amber-400/20 text-amber-300 text-xs flex items-center justify-center font-bold">3</span>
            产品图片
          </h2>
          <ImageUploader images={images} onChange={setImages} />
        </div>

        <div className="flex justify-center">
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 bg-amber-400 hover:bg-amber-300 text-slate-950 rounded-xl font-medium transition-all disabled:opacity-60 disabled:cursor-not-allowed hover:scale-[1.02]"
          >
            {loading ? '生成中...' : '✨ 生成小红书笔记'}
          </button>
        </div>
      </form>
    </div>
  )
}
