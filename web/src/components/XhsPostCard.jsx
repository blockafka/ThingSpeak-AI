import { useState } from 'react'

export default function XhsPostCard({ copy }) {
  const [copied, setCopied] = useState(false)

  const fullText = `${copy.title || ''}\n\n${copy.body || ''}\n\n${(copy.hashtags || []).join(' ')}`

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(fullText)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const ta = document.createElement('textarea')
      ta.value = fullText
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="glass-card rounded-xl p-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
          <span className="text-red-400">📱</span> 小红书成稿预览
        </h3>
        <button
          onClick={handleCopy}
          className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
            copied
              ? 'bg-green-500/20 text-green-400 scale-95'
              : 'bg-blue-500/20 text-blue-300 hover:bg-blue-500/30 hover:scale-105'
          }`}
        >
          {copied ? '✓ 已复制' : '复制文案'}
        </button>
      </div>

      {/* 文案内容区 */}
      <div className="flex-1 overflow-y-auto max-h-[500px]">
        {/* 模拟作者信息 */}
        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-white/10">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-orange-400 to-amber-500 flex items-center justify-center text-white text-xs font-bold">
            物
          </div>
          <div className="flex-1">
            <div className="text-xs font-medium text-white">物言小铺</div>
            <div className="text-[10px] text-slate-500">刚刚</div>
          </div>
          <span className="text-[10px] text-red-400 border border-red-400/30 rounded-full px-2 py-0.5">+ 关注</span>
        </div>

        {/* 标题 */}
        <h2 className="text-lg font-bold mb-3 leading-snug text-white">
          {copy.title || '标题生成中...'}
        </h2>

        {/* 正文 */}
        <div className="text-sm leading-relaxed whitespace-pre-line text-slate-300 mb-4">
          {copy.body || '正文生成中...'}
        </div>

        {/* Hashtags */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {(copy.hashtags || []).map((tag, i) => (
            <span
              key={i}
              className="text-xs text-blue-300 bg-blue-500/15 px-2 py-0.5 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* 模拟互动栏 */}
        <div className="flex items-center gap-6 pt-3 border-t border-white/10 text-slate-500">
          <span className="flex items-center gap-1 text-xs">❤️ <span className="text-slate-300">1.2k</span></span>
          <span className="flex items-center gap-1 text-xs">⭐ <span className="text-slate-300">986</span></span>
          <span className="flex items-center gap-1 text-xs">💬 <span className="text-slate-300">47</span></span>
          <span className="flex items-center gap-1 text-xs ml-auto text-slate-400">↗ 分享</span>
        </div>
      </div>
    </div>
  )
}
