import { useEffect, useRef, useState } from 'react'
import AgentNode from './AgentNode'
import { apiUrl } from '../lib/api'

const STEPS = [
  { key: 'analyzing', label: '策略分析', icon: '🧠', weight: 45 },
  { key: 'creating', label: '内容创作', icon: '✍️', weight: 55 },
]

const TIPS = {
  analyzing: [
    '正在读取产品图片，提取视觉特征...',
    '正在从六个维度召回 DNA 片段...',
    '正在让 AI 组合最合适的 DNA 片段...',
    '正在提炼核心卖点与避坑点...',
    '正在生成视觉拍摄方向...',
  ],
  creating: [
    '正在按照爆款风格组织文案结构...',
    '正在润色小红书语感和钩子...',
    '正在生成图片排序与图注建议...',
    '正在检查内容合规性...',
  ],
}

export default function GeneratingView({ formData, onComplete }) {
  const [stepStates, setStepStates] = useState(
    STEPS.map(s => ({ key: s.key, status: 'idle' })),
  )
  const [currentStep, setCurrentStep] = useState('analyzing')
  const [tipIndex, setTipIndex] = useState(0)
  const [elapsed, setElapsed] = useState(0)
  const [errorMessage, setErrorMessage] = useState('')
  const [dnaPreview, setDnaPreview] = useState(null)
  const [sellingPointsPreview, setSellingPointsPreview] = useState(null)

  const startTimeRef = useRef(Date.now())
  const timerRef = useRef(null)
  const tipTimerRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    startTimeRef.current = Date.now()
    timerRef.current = setInterval(() => {
      setElapsed(Math.round((Date.now() - startTimeRef.current) / 1000))
    }, 1000)

    // 循环切换当前步骤的提示文案
    tipTimerRef.current = setInterval(() => {
      setTipIndex(prev => (prev + 1) % TIPS[currentStep].length)
    }, 2500)

    const run = async () => {
      try {
        // 构建 FormData
        const formBody = new FormData()
        formBody.append('product_name', formData.product_name || '')
        formBody.append('product_category', formData.product_category || '')
        formBody.append('origin_place', formData.origin_place || '')
        formBody.append('target_audience', formData.target_audience || '')
        if (formData.selling_scene) formBody.append('selling_scene', formData.selling_scene)
        if (formData.user_note) formBody.append('user_note', formData.user_note)
        if (formData.images && formData.images.length > 0) {
          formData.images.forEach(img => {
            formBody.append('images', img.file)
          })
        }

        // 启动第一步
        setStepStates(STEPS.map((s, i) => ({
          key: s.key,
          status: i === 0 ? 'running' : 'idle',
        })))
        setCurrentStep('analyzing')

        const controller = new AbortController()
        abortRef.current = controller

        const response = await fetch(apiUrl('/api/generate'), {
          method: 'POST',
          body: formBody,
          signal: controller.signal,
        })

        if (!response.ok) {
          const errText = await response.text().catch(() => '')
          throw new Error(`服务端错误 ${response.status}: ${errText.slice(0, 100)}`)
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let buffer = ''
        let finalResult = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })

          // SSE 事件以 \n\n 分隔
          let eventEnd
          while ((eventEnd = buffer.indexOf('\n\n')) !== -1) {
            const rawEvent = buffer.slice(0, eventEnd)
            buffer = buffer.slice(eventEnd + 2)
            const parsed = parseSseEvent(rawEvent)
            if (!parsed) continue

            handleSseEvent(parsed)
            if (parsed.type === 'result') {
              finalResult = parsed.data
            }
          }
        }

        // 处理 buffer 中剩余的内容
        if (buffer.trim()) {
          const parsed = parseSseEvent(buffer)
          if (parsed) {
            handleSseEvent(parsed)
            if (parsed.type === 'result') finalResult = parsed.data
          }
        }

        clearInterval(timerRef.current)
        clearInterval(tipTimerRef.current)
        const totalElapsed = Math.round((Date.now() - startTimeRef.current) / 1000)

        if (finalResult) {
          setTimeout(() => onComplete(finalResult, totalElapsed), 400)
        } else {
          throw new Error('未收到生成结果')
        }
      } catch (error) {
        if (error.name === 'AbortError') return
        clearInterval(timerRef.current)
        clearInterval(tipTimerRef.current)
        setErrorMessage(error.message)
        setStepStates(STEPS.map(s => ({
          key: s.key,
          status: s.key === currentStep ? 'error' : 'idle',
        })))
      }
    }

    run()

    return () => {
      clearInterval(timerRef.current)
      clearInterval(tipTimerRef.current)
      abortRef.current?.abort()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 处理单条 SSE 事件
  const handleSseEvent = ({ type, data }) => {
    if (type === 'error') {
      setErrorMessage(data?.message || '生成失败')
      return
    }

    if (type === 'progress') {
      const step = data.step
      const status = data.status

      if (step === 'analyzing' && status === 'start') {
        setStepStates(prev => prev.map(s => ({
          key: s.key,
          status: s.key === 'analyzing' ? 'running' : 'idle',
        })))
        setCurrentStep('analyzing')
        setTipIndex(0)
      }

      if (step === 'analyzing' && status === 'done') {
        setStepStates(prev => prev.map(s => ({
          key: s.key,
          status: s.key === 'analyzing' ? 'done' : s.status,
        })))
        // 展示中间结果预览
        if (data.selected_fragments) setDnaPreview(data.selected_fragments)
        if (data.key_selling_points) setSellingPointsPreview(data.key_selling_points)
      }

      if (step === 'creating' && status === 'start') {
        setStepStates(prev => prev.map(s => {
          if (s.key === 'analyzing') return { ...s, status: 'done' }
          if (s.key === 'creating') return { ...s, status: 'running' }
          return s
        }))
        setCurrentStep('creating')
        setTipIndex(0)
      }

      if (step === 'creating' && status === 'done') {
        setStepStates(prev => prev.map(s => ({
          ...s,
          status: s.key === 'creating' ? 'done' : s.status,
        })))
      }

      if (step === 'completed' && status === 'done') {
        setStepStates(STEPS.map(s => ({ key: s.key, status: 'done' })))
      }
    }
  }

  const getStepStatus = (stepKey) => {
    const step = stepStates.find(s => s.key === stepKey)
    return step ? step.status : 'idle'
  }

  const progress = (() => {
    let total = 0
    for (const step of STEPS) {
      const status = getStepStatus(step.key)
      if (status === 'done') total += step.weight
      else if (status === 'running') total += step.weight * 0.5
    }
    return Math.min(Math.round(total), errorMessage ? 100 : 95)
  })()

  const currentTips = TIPS[currentStep] || TIPS.analyzing

  return (
    <div className="animate-fade-in-up max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <p className="text-base text-slate-300 tabular-nums">
          生成中… <span className="text-slate-500">已用时 {elapsed}s</span>
        </p>
      </div>

      <div className="glass-card rounded-2xl p-5 mb-6">
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-4">
          {STEPS.map((step, i) => (
            <div key={step.key} className="flex items-center gap-2">
              <AgentNode icon={step.icon} label={step.label} status={getStepStatus(step.key)} />
              {i < STEPS.length - 1 && <div className="text-slate-500 text-sm sm:text-lg">→</div>}
            </div>
          ))}
        </div>
      </div>

      <div className="mb-6">
        <div className="flex justify-between text-sm mb-1">
          <span className="text-slate-200 transition-all duration-500">
            {errorMessage ? `❌ ${errorMessage}` : currentTips[tipIndex]}
          </span>
          <span className="text-white font-medium tabular-nums">{progress}%</span>
        </div>
        <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full progress-bar-striped transition-all duration-700 ease-out bg-gradient-to-r from-amber-400 via-orange-400 to-rose-400"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="bg-[#1e1a22] rounded-2xl p-5 border border-white/5">
          <h3 className="text-sm font-medium text-amber-300 mb-3">本次输入</h3>
          <div className="space-y-2 text-sm text-slate-300">
            <div><span className="text-slate-500">产品：</span>{formData.product_name}</div>
            <div><span className="text-slate-500">品类：</span>{formData.product_category}</div>
            <div><span className="text-slate-500">产地：</span>{formData.origin_place}</div>
            <div><span className="text-slate-500">目标人群：</span>{formData.target_audience}</div>
            <div><span className="text-slate-500">场景：</span>{formData.selling_scene || '—'}</div>
            {formData.images?.length > 0 && (
              <div><span className="text-slate-500">图片：</span>{formData.images.length} 张</div>
            )}
          </div>
        </div>

        <div className="bg-[#1e1a22] rounded-2xl p-5 border border-white/5">
          <h3 className="text-sm font-medium text-amber-300 mb-3">输出</h3>
          <div className="space-y-2 text-sm text-slate-300">
            <div><span className="text-slate-500">笔记：</span>小红书爆款标题 + 正文</div>
            <div><span className="text-slate-500">标签：</span>精准话题标签</div>
            <div><span className="text-slate-500">配图：</span>3-6 张图片拍摄建议</div>
            <div><span className="text-slate-500">DNA：</span>六维片段组合说明</div>
          </div>
        </div>
      </div>

      {dnaPreview && dnaPreview.length > 0 && (
        <div className="bg-[#1e1a22] rounded-2xl p-5 border border-white/5 mt-4 animate-fade-in-up">
          <h3 className="text-sm font-medium text-amber-300 mb-3">✨ 已组合的 DNA 片段</h3>
          <div className="space-y-2">
            {dnaPreview.map((dna, i) => (
              <div
                key={dna.fragment_id || i}
                className="flex items-center justify-between rounded-xl bg-white/5 px-4 py-2.5 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="text-amber-300 font-medium">
                    {dna.type || 'DNA'}
                  </span>
                  <span className="text-white">{dna.value || dna.fragment_id}</span>
                </div>
                <span className="text-xs text-slate-400 tabular-nums">
                  score {Number(dna.score || 0).toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {sellingPointsPreview && sellingPointsPreview.length > 0 && (
        <div className="bg-[#1e1a22] rounded-2xl p-5 border border-white/5 mt-4 animate-fade-in-up">
          <h3 className="text-sm font-medium text-amber-300 mb-3">💡 提炼的核心卖点</h3>
          <div className="flex flex-wrap gap-2">
            {sellingPointsPreview.map((point, i) => (
              <span
                key={i}
                className="px-3 py-1.5 rounded-full text-xs bg-amber-400/15 text-amber-100 border border-amber-400/20"
              >
                {point}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// 解析单条 SSE 事件（event: xxx\ndata: xxx）
function parseSseEvent(raw) {
  const lines = raw.split('\n')
  let type = 'message'
  let dataStr = ''

  for (const line of lines) {
    if (line.startsWith('event:')) {
      type = line.slice(6).trim()
    } else if (line.startsWith('data:')) {
      dataStr += line.slice(5).trim()
    }
  }

  if (!dataStr) return null

  try {
    return { type, data: JSON.parse(dataStr) }
  } catch {
    return { type, data: dataStr }
  }
}
