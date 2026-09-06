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
  Sparkles,
  Zap,
  Box,
  ChevronRight,
  CloudUpload,
  Terminal,
  AlertTriangle,
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

const API_BASE = '/api'

/* ── App ─────────────────────────────────────────────────────────────────── */

function App() {
  const [step, setStep] = useState<AppStep>('upload')
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [diagramSpec, setDiagramSpec] = useState<DiagramSpec | null>(null)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [result, setResult] = useState<GenerationResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  /* ── Upload Handler ──────────────────────────────────────────────────── */

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

      const spec: DiagramSpec = await res.json()
      setDiagramSpec(spec)

      if (spec.ambiguities.length > 0) {
        setStep('clarify')
      } else {
        await generateTerraform(spec)
      }
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
      const res = await fetch(`${API_BASE}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(spec),
      })

      if (!res.ok) throw new Error(`Generation failed: ${res.statusText}`)

      const genResult: GenerationResult = await res.json()
      setResult(genResult)
      setStep('result')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Generation failed')
      setStep('upload')
    }
  }

  const downloadZip = async () => {
    if (!diagramSpec) return
    window.open(`${API_BASE}/download/${diagramSpec.diagram_id}`, '_blank')
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
    <div className="min-h-screen bg-background text-foreground">
      {/* ── Navbar ──────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center">
              <Box className="w-4 h-4 text-white" />
            </div>
            <span className="font-semibold text-sm tracking-tight">
              diagram<span className="text-muted-foreground">→</span>infra
            </span>
          </div>

          <div className="flex items-center gap-3">
            <StepIndicator step={step} />
            <div className="badge-success flex items-center gap-1.5">
              <span className="status-dot-success" />
              <span>v0.1.0</span>
            </div>
          </div>
        </div>
      </nav>

      {/* ── Main Content ───────────────────────────────────────────────── */}
      <main className="max-w-6xl mx-auto px-6 py-10">
        {error && (
          <div className="mb-6 p-4 rounded-xl border border-rose-500/20 bg-rose-500/5 flex items-start gap-3 animate-fade-in">
            <AlertTriangle className="w-5 h-5 text-rose-400 mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-rose-400">Something went wrong</p>
              <p className="text-sm text-muted-foreground mt-1">{error}</p>
            </div>
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

      {/* ── Footer ─────────────────────────────────────────────────────── */}
      <footer className="border-t border-border mt-20">
        <div className="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            ML-powered diagram → Terraform. YOLOv8n + EasyOCR + Jinja2 templates.
          </p>
          <p className="text-xs text-muted-foreground">AWS · Terraform v1</p>
        </div>
      </footer>
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
    <div className="hidden sm:flex items-center gap-1">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <span
            className={`text-xs px-2 py-0.5 rounded-full transition-colors ${
              i === currentIdx
                ? 'bg-primary/15 text-primary font-medium'
                : i < currentIdx
                  ? 'text-muted-foreground'
                  : 'text-muted-foreground/40'
            }`}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <ChevronRight className="w-3 h-3 text-muted-foreground/30 mx-0.5" />
          )}
        </div>
      ))}
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
    <div className="animate-fade-in">
      {/* Hero */}
      <div className="text-center mb-12">
        <div className="inline-flex items-center gap-2 badge-primary mb-4">
          <Sparkles className="w-3 h-3" />
          <span>ML-Powered</span>
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tighter mb-4">
          <span className="text-gradient">Sketch it.</span>{' '}
          <span className="text-foreground">Deploy it.</span>
        </h1>
        <p className="text-muted-foreground text-lg max-w-xl mx-auto leading-relaxed">
          Upload a photo of your hand-drawn architecture diagram and get
          production-ready Terraform code in seconds.
        </p>
      </div>

      {/* Upload Zone */}
      <div className="max-w-2xl mx-auto mb-8">
        <div
          className={`dropzone ${isDragOver ? 'dropzone-active' : ''} ${
            previewUrl ? 'p-4' : 'py-16'
          }`}
          onDrop={(e) => { onDrop(e); setIsDragOver(false) }}
          onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
          onDragLeave={() => setIsDragOver(false)}
        >
          {previewUrl ? (
            <div className="relative group">
              <img
                src={previewUrl}
                alt="Uploaded diagram"
                className="w-full rounded-lg object-contain max-h-80"
              />
              <div className="absolute inset-0 bg-background/60 opacity-0 group-hover:opacity-100 transition-opacity rounded-lg flex items-center justify-center">
                <label className="cursor-pointer text-sm text-foreground font-medium flex items-center gap-2">
                  <Upload className="w-4 h-4" />
                  Replace image
                  <input
                    type="file"
                    accept="image/png,image/jpeg"
                    onChange={onSelect}
                    className="hidden"
                  />
                </label>
              </div>
            </div>
          ) : (
            <div className="text-center">
              <div className="w-14 h-14 rounded-2xl bg-secondary flex items-center justify-center mx-auto mb-4">
                <CloudUpload className="w-7 h-7 text-muted-foreground" />
              </div>
              <p className="text-sm font-medium text-foreground mb-1">
                Drop your diagram here
              </p>
              <p className="text-xs text-muted-foreground mb-4">
                PNG or JPEG • Whiteboard sketches, hand-drawn diagrams
              </p>
              <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-secondary hover:bg-secondary/80 text-sm font-medium cursor-pointer transition-colors">
                <Upload className="w-4 h-4" />
                Browse files
                <input
                  type="file"
                  accept="image/png,image/jpeg"
                  onChange={onSelect}
                  className="hidden"
                />
              </label>
            </div>
          )}
        </div>

        {hasFile && (
          <button
            onClick={onAnalyze}
            className="w-full mt-4 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all duration-200 glow-primary"
          >
            <Zap className="w-4 h-4" />
            Analyze Diagram
            <ArrowRight className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Feature Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-3xl mx-auto">
        {[
          {
            icon: <Box className="w-5 h-5 text-violet-400" />,
            title: 'Object Detection',
            desc: 'YOLOv8n detects compute, database, storage, LB, network components',
          },
          {
            icon: <MessageSquare className="w-5 h-5 text-blue-400" />,
            title: 'Smart Clarification',
            desc: 'AI asks follow-up questions to resolve ambiguous components',
          },
          {
            icon: <FileCode2 className="w-5 h-5 text-emerald-400" />,
            title: 'Valid Terraform',
            desc: 'Generates terraform validate-passing .tf files for AWS',
          },
        ].map((f) => (
          <div key={f.title} className="card">
            <div className="mb-3">{f.icon}</div>
            <h3 className="text-sm font-semibold mb-1">{f.title}</h3>
            <p className="text-xs text-muted-foreground leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Analyzing Step ──────────────────────────────────────────────────────── */

function AnalyzingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-24 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight mb-2">Analyzing your diagram</h2>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        Running object detection, OCR, and relationship extraction…
      </p>
      <div className="mt-8 w-80">
        <div className="flex items-center gap-3 mb-3">
          <div className="shimmer w-full h-2 rounded-full" />
        </div>
        <div className="space-y-2">
          {['Preprocessing image…', 'Detecting components…', 'Extracting text…', 'Building graph…'].map(
            (label) => (
              <div key={label} className="flex items-center gap-2 text-xs text-muted-foreground">
                <Loader2 className="w-3 h-3 animate-spin" />
                {label}
              </div>
            )
          )}
        </div>
      </div>
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
    <div className="max-w-2xl mx-auto animate-fade-in">
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center">
          <MessageSquare className="w-5 h-5 text-amber-400" />
        </div>
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Clarify ambiguities</h2>
          <p className="text-sm text-muted-foreground">
            {ambiguities.length} component{ambiguities.length > 1 ? 's' : ''} need
            {ambiguities.length > 1 ? '' : 's'} clarification
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {ambiguities.map((amb, idx) => (
          <div key={amb.component_id} className="card">
            <div className="flex items-start gap-3">
              <span className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-xs font-medium text-muted-foreground shrink-0 mt-0.5">
                {idx + 1}
              </span>
              <div className="flex-1">
                <p className="text-sm font-medium mb-3">{amb.question}</p>
                <div className="flex flex-wrap gap-2">
                  {amb.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() =>
                        setAnswers((prev) => ({ ...prev, [amb.component_id]: opt }))
                      }
                      className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                        answers[amb.component_id] === opt
                          ? 'bg-primary text-primary-foreground glow-primary'
                          : 'bg-secondary text-foreground hover:bg-secondary/80'
                      }`}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button
        onClick={onSubmit}
        disabled={!allAnswered}
        className={`w-full mt-6 py-3 rounded-xl text-sm font-medium flex items-center justify-center gap-2 transition-all duration-200 ${
          allAnswered
            ? 'bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white glow-primary'
            : 'bg-secondary text-muted-foreground cursor-not-allowed'
        }`}
      >
        <Zap className="w-4 h-4" />
        Generate Terraform
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  )
}

/* ── Generating Step ─────────────────────────────────────────────────────── */

function GeneratingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-24 animate-fade-in">
      <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-6">
        <Terminal className="w-8 h-8 text-emerald-400 animate-pulse" />
      </div>
      <h2 className="text-xl font-semibold tracking-tight mb-2">Generating Terraform</h2>
      <p className="text-sm text-muted-foreground max-w-md text-center">
        Mapping components to AWS resources, rendering templates, running validation…
      </p>
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
    <div className="animate-fade-in">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <div className="card">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Validation
          </p>
          <div className="flex items-center gap-2">
            {result.validation.valid ? (
              <>
                <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                <span className="text-2xl font-bold tracking-tight text-emerald-400">Pass</span>
              </>
            ) : (
              <>
                <XCircle className="w-5 h-5 text-rose-400" />
                <span className="text-2xl font-bold tracking-tight text-rose-400">Fail</span>
              </>
            )}
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            terraform validate {result.validation.valid ? 'succeeded' : `— ${result.validation.errors.length} error(s)`}
          </p>
        </div>

        <div className="card">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Components
          </p>
          <p className="text-3xl font-bold tracking-tight">
            {diagramSpec?.components.length ?? 0}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            {diagramSpec?.layout_pattern ?? 'unknown'} pattern
          </p>
        </div>

        <div className="card">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Relationships
          </p>
          <p className="text-3xl font-bold tracking-tight">
            {diagramSpec?.relationships.length ?? 0}
          </p>
          <p className="text-xs text-muted-foreground mt-1">connections mapped</p>
        </div>
      </div>

      {/* Validation Errors */}
      {!result.validation.valid && result.validation.errors.length > 0 && (
        <div className="mb-6 p-4 rounded-xl border border-rose-500/20 bg-rose-500/5">
          <p className="text-sm font-medium text-rose-400 mb-2 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            Validation Errors
          </p>
          <ul className="space-y-1">
            {result.validation.errors.map((err, i) => (
              <li key={i} className="text-xs text-muted-foreground font-mono pl-4">
                • {err}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Code + Preview Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
        {/* Code Viewer */}
        <div className="lg:col-span-2 card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <FileCode2 className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium">main.tf</span>
              {result.validation.valid && (
                <span className="badge-success">
                  <CheckCircle2 className="w-3 h-3" />
                  valid
                </span>
              )}
            </div>
            <span className="text-xs text-muted-foreground font-mono">
              {result.terraform_code.split('\n').length} lines
            </span>
          </div>
          <pre className="p-4 text-xs font-mono leading-relaxed overflow-auto max-h-[500px] scrollbar-thin text-emerald-300/90">
            <code>{result.terraform_code}</code>
          </pre>
        </div>

        {/* Diagram Preview */}
        <div className="card p-0 overflow-hidden">
          <div className="px-4 py-3 border-b border-border">
            <span className="text-sm font-medium">Source Diagram</span>
          </div>
          {previewUrl ? (
            <img
              src={previewUrl}
              alt="Source diagram"
              className="w-full object-contain p-4"
            />
          ) : (
            <div className="p-8 text-center text-muted-foreground text-sm">
              No preview available
            </div>
          )}

          {/* Component List */}
          {diagramSpec && (
            <div className="border-t border-border px-4 py-3">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
                Detected
              </p>
              <div className="flex flex-wrap gap-1.5">
                {diagramSpec.components.map((c) => (
                  <span key={c.id} className="badge-neutral">
                    {c.subtype}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button
          onClick={onDownload}
          className="flex-1 py-3 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 hover:from-violet-500 hover:to-blue-500 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all duration-200 glow-primary"
        >
          <Download className="w-4 h-4" />
          Download .tf ZIP
        </button>
        <button
          onClick={onReset}
          className="px-6 py-3 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground font-medium text-sm flex items-center justify-center gap-2 transition-colors"
        >
          New Diagram
        </button>
      </div>
    </div>
  )
}

export default App
