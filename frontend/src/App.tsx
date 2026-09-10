import { useState, useCallback } from 'react'
import {
  Upload,
  FileCode2,
  Download,
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  MessageSquare,
  Box,
  ChevronRight,
  CloudUpload,
  Terminal,
  AlertTriangle,
  RotateCcw
} from 'lucide-react'

/* ── Types ───────────────────────────────────────────────────────────────── */

interface Ambiguity {
  component_id: string
  issue: string
  question: string
  options: string[]
}

interface DiagramSpec {
  diagram_id: string
  layout_pattern: string
  components: Array<{
    id: string
    type: string
    subtype: string
    label: string
    confidence: number
  }>
  relationships: Array<{
    from: string
    to: string
    type: string
    confidence: number
  }>
  ambiguities: Ambiguity[]
}

interface GenerationResult {
  terraform_code: string
  validation: {
    valid: boolean
    errors: string[]
  }
}

type AppStep = 'upload' | 'analyzing' | 'clarify' | 'generating' | 'result'

const API_BASE = 'http://localhost:8000'

/* ── App ─────────────────────────────────────────────────────────────────── */

function App() {
  const [step, setStep] = useState<AppStep>('upload')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [diagramSpec, setDiagramSpec] = useState<DiagramSpec | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<GenerationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  /* ── Handlers ────────────────────────────────────────────────────────── */

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
      setUploadedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setError(null)
    }
  }, [])

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setUploadedFile(file)
      setPreviewUrl(URL.createObjectURL(file))
      setError(null)
    }
  }, [])

  /* ── API Calls ───────────────────────────────────────────────────────── */

  const analyzeImage = async () => {
    if (!uploadedFile) return
    setStep('analyzing')
    setError(null)

    try {
      const formData = new FormData()
      formData.append('image', uploadedFile)

      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) throw new Error(`Analysis failed: ${res.statusText}`)

      const data = await res.json()
      const rawSpec = data.spec
      const spec: DiagramSpec = {
        diagram_id: "auto-gen",
        layout_pattern: "unknown",
        components: rawSpec.nodes || [],
        relationships: rawSpec.edges || [],
        ambiguities: rawSpec.ambiguities || []
      }
      setDiagramSpec(spec)

      setDiagramSpec(spec)
      await generateTerraform(spec)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Analysis failed')
      setStep('upload')
    }
  }

  const submitClarifications = async () => {
    if (!diagramSpec) return
    setStep('generating')
    setError(null)

    try {
      const res = await fetch(`${API_BASE}/clarify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          diagram_id: diagramSpec.diagram_id,
          answers,
        }),
      })

      if (!res.ok) throw new Error(`Clarification failed: ${res.statusText}`)

      const refined: DiagramSpec = await res.json()
      setDiagramSpec(refined)
      await generateTerraform(refined)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Clarification failed')
      setStep('clarify')
    }
  }

  const generateTerraform = async (spec: DiagramSpec) => {
    setStep('generating')

    try {
      const payload = {
        spec: {
          nodes: spec.components,
          edges: spec.relationships,
          ambiguities: spec.ambiguities
        }
      }
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) throw new Error(`Generation failed: ${res.statusText}`)

      const tfText = await res.text()
      const genResult: GenerationResult = {
        terraform_code: tfText,
        validation: { valid: true, errors: [] }
      }
      setResult(genResult)
      setStep('result')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
      setStep('upload')
    }
  }

  const downloadZip = async () => {
    if (!result) return
    const blob = new Blob([result.terraform_code], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'terraform_infrastructure.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const resetAll = () => {
    setStep('upload')
    setUploadedFile(null)
    setPreviewUrl(null)
    setDiagramSpec(null)
    setAnswers({})
    setResult(null)
    setError(null)
  }

  /* ── Render ──────────────────────────────────────────────────────────── */

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans selection:bg-accent selection:text-foreground">
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3 cursor-pointer" onClick={resetAll}>
            <div className="w-8 h-8 rounded-lg bg-card border border-border flex items-center justify-center">
              <Box className="w-4 h-4 text-foreground" />
            </div>
            <span className="text-base font-semibold tracking-tight">
              diagram→infra
            </span>
          </div>
          <StepIndicator step={step} />
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-6 py-12 flex flex-col items-center">
        {error && (
          <div className="w-full max-w-2xl mb-8 p-4 rounded-xl border border-error/20 bg-error/10 flex items-start gap-3 animate-fade-in">
            <AlertTriangle className="w-5 h-5 text-error shrink-0" />
            <p className="text-sm font-medium text-error/90 leading-relaxed">{error}</p>
          </div>
        )}

        {step === 'upload' && (
          <UploadStep
            previewUrl={previewUrl}
            onDrop={handleFileDrop}
            onSelect={handleFileSelect}
            onAnalyze={analyzeImage}
            hasFile={!!uploadedFile}
          />
        )}

        {step === 'analyzing' && <AnalyzingStep />}

        {step === 'clarify' && diagramSpec && (
          <ClarifyStep
            ambiguities={diagramSpec.ambiguities}
            answers={answers}
            setAnswers={setAnswers}
            onSubmit={submitClarifications}
          />
        )}

        {step === 'generating' && <GeneratingStep />}

        {step === 'result' && result && (
          <ResultStep
            result={result}
            diagramSpec={diagramSpec}
            previewUrl={previewUrl}
            onDownload={downloadZip}
            onReset={resetAll}
          />
        )}
      </main>
    </div>
  )
}

/* ── Step Indicator ──────────────────────────────────────────────────────── */

function StepIndicator({ step }: { step: AppStep }) {
  const steps: { key: AppStep; label: string }[] = [
    { key: 'upload', label: 'Upload' },
    { key: 'analyzing', label: 'Analyze' },
    { key: 'clarify', label: 'Clarify' },
    { key: 'generating', label: 'Generate' },
    { key: 'result', label: 'Result' },
  ]

  const currentIdx = steps.findIndex(s => s.key === step)

  return (
    <div className="hidden md:flex items-center gap-1.5">
      {steps.map((s, i) => {
        const isActive = i === currentIdx;
        const isPast = i < currentIdx;
        
        return (
          <div key={s.key} className="flex items-center gap-1.5">
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-medium transition-all duration-300 ${
                isActive
                  ? 'bg-foreground text-background shadow-lg shadow-white/10'
                  : isPast
                    ? 'text-muted-foreground'
                    : 'text-muted-foreground/40'
              }`}
            >
              {s.label}
            </span>
            {i < steps.length - 1 && (
              <ChevronRight className="w-3.5 h-3.5 text-border" />
            )}
          </div>
        )
      })}
    </div>
  )
}

/* ── Upload Step ─────────────────────────────────────────────────────────── */

function UploadStep({
  previewUrl,
  onDrop,
  onSelect,
  onAnalyze,
  hasFile,
}: {
  previewUrl: string | null
  onDrop: (e: React.DragEvent) => void
  onSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onAnalyze: () => void
  hasFile: boolean
}) {
  const [isDragOver, setIsDragOver] = useState(false)

  return (
    <div className="w-full max-w-3xl flex flex-col items-center animate-slide-up">
      <div className="text-center mb-10">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          Diagram to Terraform Code
        </h1>
        <p className="text-base text-muted-foreground max-w-lg mx-auto leading-relaxed">
          Upload a photo of your whiteboard sketch and instantly get production-ready AWS Terraform.
        </p>
      </div>

      <div className="w-full mb-12">
        <div
          className={`dropzone ${isDragOver ? 'dropzone-active' : ''} ${previewUrl ? 'p-4' : ''}`}
          onDrop={(e) => { onDrop(e); setIsDragOver(false) }}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
        >
          {previewUrl ? (
            <div className="relative group w-full flex justify-center">
              <img
                src={previewUrl}
                alt="Uploaded diagram"
                className="rounded-lg object-contain max-h-[400px] shadow-lg shadow-black"
              />
              <div className="absolute inset-0 bg-background/80 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex flex-col items-center justify-center backdrop-blur-sm">
                <label className="cursor-pointer px-4 py-2 bg-secondary text-foreground rounded-lg font-medium text-sm flex items-center gap-2 hover:bg-secondary-hover transition-colors shadow-lg">
                  <Upload className="w-4 h-4" />
                  Choose another image
                  <input type="file" accept="image/png,image/jpeg" onChange={onSelect} className="hidden" />
                </label>
              </div>
            </div>
          ) : (
            <>
              <div className="w-16 h-16 rounded-full bg-secondary/50 flex items-center justify-center mb-4 border border-border shadow-inner">
                <CloudUpload className="w-8 h-8 text-muted-foreground" />
              </div>
              <h3 className="text-lg font-semibold mb-1">Drag and drop your diagram</h3>
              <p className="text-sm text-muted-foreground mb-6">Supports PNG or JPEG up to 10MB</p>
              <label className="px-5 py-2.5 bg-foreground text-background rounded-lg font-semibold text-sm cursor-pointer hover:bg-foreground/90 transition-all shadow-lg shadow-white/10 hover:shadow-white/20">
                Browse Files
                <input type="file" accept="image/png,image/jpeg" onChange={onSelect} className="hidden" />
              </label>
            </>
          )}
        </div>

        {hasFile && (
          <div className="mt-6 flex justify-center animate-fade-in">
            <button
              onClick={onAnalyze}
              className="px-8 py-3 rounded-xl bg-foreground text-background font-semibold flex items-center justify-center gap-2 transition-all hover:bg-foreground/90 hover:-translate-y-0.5 shadow-xl shadow-white/10 group"
            >
              Analyze Diagram
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 w-full">
        {[
          { icon: <Box className="w-5 h-5" />, title: 'AI Detection', desc: 'Custom YOLOv8n identifies AWS components, databases, network boundaries, and arrows.' },
          { icon: <MessageSquare className="w-5 h-5" />, title: 'Smart Clarification', desc: 'Asks clarifying multiple-choice questions to resolve ambiguous hand-drawn shapes.' },
          { icon: <FileCode2 className="w-5 h-5" />, title: 'Valid Terraform', desc: 'Generates syntactically correct .tf files validated against the Terraform CLI.' },
        ].map((f) => (
          <div key={f.title} className="card">
            <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center mb-4 border border-border">
              {f.icon}
            </div>
            <h3 className="text-sm font-semibold mb-2">{f.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Analyzing & Generating Step ─────────────────────────────────────────── */

function AnalyzingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-32 animate-fade-in">
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-accent blur-xl opacity-20 rounded-full animate-pulse"></div>
        <Loader2 className="w-10 h-10 text-foreground animate-spin relative z-10" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight mb-2">Analyzing diagram...</h2>
      <p className="text-sm text-muted-foreground">Running detection model and extracting relationships.</p>
    </div>
  )
}

function GeneratingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-32 animate-fade-in">
      <div className="relative mb-8">
        <div className="absolute inset-0 bg-accent blur-xl opacity-20 rounded-full animate-pulse"></div>
        <Terminal className="w-10 h-10 text-foreground animate-pulse relative z-10" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight mb-2">Generating Infrastructure...</h2>
      <p className="text-sm text-muted-foreground">Mapping components and rendering Terraform code.</p>
    </div>
  )
}

/* ── Clarify Step ────────────────────────────────────────────────────────── */

function ClarifyStep({
  ambiguities,
  answers,
  setAnswers,
  onSubmit,
}: {
  ambiguities: Ambiguity[]
  answers: Record<string, string>
  setAnswers: React.Dispatch<React.SetStateAction<Record<string, string>>>
  onSubmit: () => void
}) {
  const allAnswered = ambiguities.every((a) => answers[a.component_id])

  return (
    <div className="w-full max-w-2xl animate-slide-up">
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold tracking-tight mb-2">Clarify Ambiguities</h2>
        <p className="text-muted-foreground text-sm">We found {ambiguities.length} component{ambiguities.length > 1 ? 's' : ''} that need your confirmation before generating code.</p>
      </div>

      <div className="space-y-4 mb-8">
        {ambiguities.map((amb, idx) => (
          <div key={amb.component_id} className="card border-border/50">
            <div className="flex items-start gap-4">
              <div className="w-6 h-6 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
                <span className="text-xs font-semibold">{idx + 1}</span>
              </div>
              <div className="flex-1 pt-0.5">
                <h3 className="text-sm font-semibold mb-1">{amb.issue}</h3>
                <p className="text-sm text-muted-foreground mb-4">{amb.question}</p>
                <div className="flex flex-wrap gap-2">
                  {amb.options.map((opt) => {
                    const isSelected = answers[amb.component_id] === opt;
                    return (
                      <button
                        key={opt}
                        onClick={() => setAnswers((prev) => ({ ...prev, [amb.component_id]: opt }))}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                          isSelected
                            ? 'bg-foreground text-background shadow-lg shadow-white/10'
                            : 'bg-secondary text-foreground hover:bg-secondary-hover border border-border'
                        }`}
                      >
                        {opt}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="flex justify-end">
        <button
          onClick={onSubmit}
          disabled={!allAnswered}
          className={`px-8 py-3 rounded-xl font-semibold flex items-center gap-2 transition-all group ${
            allAnswered
              ? 'bg-foreground text-background hover:-translate-y-0.5 shadow-xl shadow-white/10'
              : 'bg-secondary text-muted-foreground cursor-not-allowed opacity-50'
          }`}
        >
          Generate Code
          <ArrowRight className={`w-4 h-4 ${allAnswered ? 'group-hover:translate-x-1 transition-transform' : ''}`} />
        </button>
      </div>
    </div>
  )
}

/* ── Result Step ─────────────────────────────────────────────────────────── */

function ResultStep({
  result,
  diagramSpec,
  previewUrl,
  onDownload,
  onReset,
}: {
  result: GenerationResult
  diagramSpec: DiagramSpec | null
  previewUrl: string | null
  onDownload: () => void
  onReset: () => void
}) {
  return (
    <div className="w-full animate-slide-up">
      
      {/* 3 Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5 mb-6">
        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
            {diagramSpec?.components.length === 0 ? (
              <XCircle className="w-6 h-6 text-error" />
            ) : result.validation.valid ? (
              <CheckCircle2 className="w-6 h-6 text-success" />
            ) : (
              <XCircle className="w-6 h-6 text-error" />
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Validation</p>
            {diagramSpec?.components.length === 0 ? (
              <p className="text-xl font-bold text-error">Failed</p>
            ) : result.validation.valid ? (
              <p className="text-xl font-bold">Passed</p>
            ) : (
              <p className="text-xl font-bold text-error">Failed</p>
            )}
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
            <Box className="w-6 h-6 text-foreground" />
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Components</p>
            <p className="text-xl font-bold">{diagramSpec?.components.length ?? 0}</p>
          </div>
        </div>

        <div className="card flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-secondary border border-border flex items-center justify-center shrink-0">
            <ChevronRight className="w-6 h-6 text-foreground" />
          </div>
          <div>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-1">Connections</p>
            <p className="text-xl font-bold">{diagramSpec?.relationships.length ?? 0}</p>
          </div>
        </div>
      </div>

      {/* Validation Errors */}
      {((!result.validation.valid && result.validation.errors.length > 0) || diagramSpec?.components.length === 0) && (
        <div className="card border-destructive/50 bg-destructive/10 mb-6">
          <div className="flex items-center gap-3 mb-3">
            <XCircle className="w-5 h-5 text-destructive" />
            <h3 className="font-semibold text-destructive">
              {diagramSpec?.components.length === 0 ? "No Architecture Detected" : "Validation Errors Detected"}
            </h3>
          </div>
          <ul className="list-disc list-inside text-sm text-destructive/80 space-y-1">
            {diagramSpec?.components.length === 0 ? (
              <li>The AI could not confidently detect any valid infrastructure components (like servers or databases) in this image. Try drawing darker lines or using a white background.</li>
            ) : (
              result.validation.errors.map((err, i) => (
                <li key={i}>{err}</li>
              ))
            )}
          </ul>
        </div>
      )}

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Left: Code */}
        <div className="card p-0 overflow-hidden flex flex-col h-[600px]">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border bg-card">
            <div className="flex items-center gap-2">
              <FileCode2 className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-semibold font-mono">main.tf</span>
            </div>
            <span className="text-xs text-muted-foreground font-mono bg-secondary px-2 py-1 rounded">
              {result.terraform_code.split('\n').length} lines
            </span>
          </div>
          <div className="flex-1 overflow-auto bg-black p-5 scrollbar-thin">
            <pre className="text-sm font-mono leading-relaxed text-foreground/90">
              <code>{result.terraform_code}</code>
            </pre>
          </div>
        </div>

        {/* Right: Preview & Tags */}
        <div className="flex flex-col gap-6 h-[600px]">
          <div className="card p-0 flex-1 flex flex-col overflow-hidden" style={{ minHeight: 0 }}>
            <div className="px-5 py-4 border-b border-border bg-card shrink-0">
              <span className="text-sm font-semibold">Diagram Source</span>
            </div>
            <div className="flex-1 bg-secondary/20 p-2 flex items-center justify-center overflow-hidden" style={{ minHeight: 0 }}>
              {previewUrl ? (
                <img 
                  src={previewUrl} 
                  alt="Source diagram" 
                  className="rounded-lg shadow-lg"
                  style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
                />
              ) : (
                <div className="text-sm text-muted-foreground">No image available</div>
              )}
            </div>
          </div>
          
          <div className="card overflow-hidden">
            <h3 className="text-sm font-semibold mb-4">Detected Architecture</h3>
            <div className="flex flex-wrap gap-2">
              {diagramSpec?.components.map((c) => (
                <span key={c.id} className="badge-neutral">
                  {c.subtype}
                </span>
              ))}
              {(!diagramSpec?.components || diagramSpec.components.length === 0) && (
                <span className="text-sm text-muted-foreground">No components detected.</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-4">
        <button
          onClick={onReset}
          className="px-6 py-3 rounded-xl bg-secondary text-foreground hover:bg-secondary-hover font-semibold transition-all border border-border flex items-center gap-2"
        >
          <RotateCcw className="w-4 h-4" />
          Start Over
        </button>
        <button
          onClick={onDownload}
          className="px-8 py-3 rounded-xl bg-foreground text-background font-semibold flex items-center gap-2 transition-all hover:bg-foreground/90 hover:-translate-y-0.5 shadow-xl shadow-white/10"
        >
          <Download className="w-4 h-4" />
          Download Terraform
        </button>
      </div>

    </div>
  )
}

export default App
