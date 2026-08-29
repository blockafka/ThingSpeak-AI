import { useState } from 'react'

export default function TechDetails({ data }) {
  const [open, setOpen] = useState(false)

  if (!data) return null

  return (
    <div className="mt-6">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-2 text-sm text-slate-400 hover:text-white transition-colors"
      >
        <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>▶</span>
        原始响应详情
      </button>

      {open && (
        <div className="mt-3 bg-[#1e1a22] rounded-xl border border-white/5 p-5 animate-fade-in-up">
          <pre className="text-xs text-slate-400 bg-black/30 rounded-lg p-3 overflow-x-auto whitespace-pre-wrap max-h-[420px]">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
