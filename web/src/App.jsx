import { useState } from 'react'
import NavBar from './components/NavBar'
import HeroBackground from './components/HeroBackground'
import InputView from './components/InputView'
import GeneratingView from './components/GeneratingView'
import ResultView from './components/ResultView'

export default function App() {
  const [view, setView] = useState('input')
  const [formData, setFormData] = useState(null)
  const [result, setResult] = useState(null)
  const [elapsed, setElapsed] = useState(0)

  const handleGenerate = (data) => {
    // data 包含 form 字段 + images（File 对象数组）
    setFormData(data)
    setResult(null)
    setView('generating')
  }

  const handleComplete = (finalResult, elapsedTime) => {
    setResult(finalResult)
    setElapsed(elapsedTime)
    setView('result')
  }

  const handleReset = () => {
    setView('input')
    setResult(null)
  }

  return (
    <div className="min-h-screen">
      <HeroBackground static={view !== 'input'} />
      <NavBar />
      <main className="relative z-10 max-w-6xl mx-auto px-4 py-8">
        {view === 'input' && <InputView onGenerate={handleGenerate} />}
        {view === 'generating' && (
          <GeneratingView
            formData={formData}
            onComplete={handleComplete}
          />
        )}
        {view === 'result' && (
          <ResultView result={result} elapsed={elapsed} onReset={handleReset} />
        )}
      </main>
    </div>
  )
}
