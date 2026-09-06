/**
 * Diagram-to-Infra-Code — Frontend App
 *
 * ⚠️  UI SHELL ONLY — NOT FUNCTIONALLY WIRED
 *
 * This component implements the complete 5-step UX flow
 * (Upload → Analyze → Clarify → Generate → Result) but the
 * backend API endpoints it calls (/analyze, /clarify, /generate,
 * /download) DO NOT EXIST YET. They are stubbed in Phase 6.
 *
 * Right now this is a layout/interaction skeleton. Uploading an
 * image and clicking "Analyze" will fail with a network error
 * until the FastAPI routes are implemented.
 *
 * Status: Phase 0 scaffold — pending Phase 6 backend wiring.
 */

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

/**
 * Backend API base URL.
 * These endpoints are NOT implemented yet — see backend/main.py.
 * Wiring happens in Phase 6.
 */
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

  /* ── API Calls (Phase 6 — endpoints not yet implemented) ─────────── */

  const analyzeImage = async () => {
    if (!uploadedFile) return
    setStep('analyzing')
    setError(null)

    try {
      const formData = new FormData()
      formData.append('image', uploadedFile)

      // POST /analyze — not implemented until Phase 6
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
      setError(
        err instanceof Error
          ? `${err.message} — backend not yet wired (Phase 6)`
          : 'Analysis failed — backend not yet wired (Phase 6)'
      )
      setStep('upload')
    }
  }

  const submitClarifications = async () => {
    if (!diagramSpec) return
    setStep('generating')
    setError(null)

    try {
      // POST /clarify — not implemented until Phase 6
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
      // POST /generate — not implemented until Phase 6
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
    // GET /download — not implemented until Phase 6
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
      {/* Navbar */}
      <nav className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 h-12 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Box className="w-4 h-4 text-accent" />
            <span className="text-sm font-medium tracking-tight">
              diagram→infra
            </span>
            <span className="text-[10px] text-muted-foreground font-mono ml-2 border border-border rounded px-1.5 py-0.5">
              UI shell · Phase 6
            </span>
          </div>

          <div className="flex items-center gap-3">
            <StepIndicator step={step} />
            <span className="text-[10px] text-muted-foreground font-mono">v0.1</span>
          </div>
        </div>
      </nav>

      {/* Main */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 p-3 rounded-lg border border-error/20 bg-error/5 flex items-start gap-2.5 animate-fade-in">
            <AlertTriangle className="w-4 h-4 text-error mt-0.5 shrink-0" />
            <p className="text-sm text-muted-foreground">{error}</p>
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

      {/* Footer */}
      <footer className="border-t border-border mt-16">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            YOLOv8n · EasyOCR · Jinja2 · AWS Terraform
          </p>
          <p className="text-xs text-muted-foreground">v1 — photo upload only</p>
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
    <div className="hidden sm:flex items-center gap-0.5">
      {steps.map((s, i) => (
        <div key={s.key} className="flex items-center">
          <span
            className={`text-[11px] px-1.5 py-0.5 rounded transition-colors ${
              i === currentIdx
                ? 'text-foreground font-medium'
                : i < currentIdx
                  ? 'text-muted-foreground'
                  : 'text-muted-foreground/30'
            }`}
          >
            {s.label}
          </span>
          {i < steps.length - 1 && (
            <ChevronRight className="w-3 h-3 text-border" />
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
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight mb-2">
          Diagram → Terraform
        </h1>
        <p className="text-sm text-muted-foreground max-w-lg">
          Upload a photo of a hand-drawn architecture diagram.
          Get <code className="text-xs font-mono text-foreground bg-secondary px-1 py-0.5 rounded">terraform validate</code>-passing
          {' '}.tf files for AWS.
        </p>
      </div>

      {/* Drop Zone */}
      <div className="max-w-2xl mb-6">
        <div
          className={`dropzone ${isDragOver ? 'dropzone-active' : ''} ${
            previewUrl ? 'p-3' : 'py-12'
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
                className="w-full rounded object-contain max-h-72"
              />
              <div className="absolute inset-0 bg-background/70 opacity-0 group-hover:opacity-100 transition-opacity rounded flex items-center justify-center">
                <label className="cursor-pointer text-xs text-foreground font-medium flex items-center gap-1.5">
                  <Upload className="w-3.5 h-3.5" />
                  Replace
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
              <CloudUpload className="w-6 h-6 text-muted-foreground mx-auto mb-3" />
              <p className="text-sm text-foreground mb-1">
                Drop your diagram here
              </p>
              <p className="text-xs text-muted-foreground mb-3">
                PNG or JPEG
              </p>
              <label className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-secondary hover:bg-secondary-hover text-xs font-medium cursor-pointer transition-colors">
                <Upload className="w-3.5 h-3.5" />
                Browse
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
            className="w-full mt-3 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium flex items-center justify-center gap-2 transition-colors hover:bg-accent-hover"
          >
            Analyze Diagram
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Info cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl">
        {[
          {
            icon: <Box className="w-4 h-4 text-muted-foreground" />,
            title: 'Detection',
            desc: 'YOLOv8n identifies compute, DB, storage, LB, network, arrows',
          },
          {
            icon: <MessageSquare className="w-4 h-4 text-muted-foreground" />,
            title: 'Clarification',
            desc: 'Asks follow-ups to resolve ambiguous or low-confidence components',
          },
          {
            icon: <FileCode2 className="w-4 h-4 text-muted-foreground" />,
            title: 'Generation',
            desc: 'Jinja2 templates → terraform validate in sandboxed Docker',
          },
        ].map((f) => (
          <div key={f.title} className="card p-4">
            <div className="flex items-center gap-2 mb-1.5">
              {f.icon}
              <h3 className="text-xs font-medium">{f.title}</h3>
            </div>
            <p className="text-[11px] text-muted-foreground leading-relaxed">{f.desc}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Analyzing Step ──────────────────────────────────────────────────────── */

function AnalyzingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
      <Loader2 className="w-6 h-6 text-muted-foreground animate-spin mb-4" />
      <h2 className="text-base font-medium tracking-tight mb-1">Analyzing diagram</h2>
      <p className="text-xs text-muted-foreground">
        Detection → OCR → relationship extraction
      </p>
    </div>
  )
}

/* ── Clarify Step ────────────────────────────────────────────────────────── */
/* Note: This screen is reachable only when the backend returns ambiguities.
   Since POST /analyze is not implemented (Phase 6), this screen cannot be
   reached in normal operation yet. */

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
    <div className="max-w-2xl animate-fade-in">
      <div className="flex items-center gap-2.5 mb-5">
        <MessageSquare className="w-4 h-4 text-muted-foreground" />
        <h2 className="text-base font-medium tracking-tight">
          Clarify {ambiguities.length} ambiguity{ambiguities.length > 1 ? 'ies' : 'y'}
        </h2>
      </div>

      <div className="space-y-3">
        {ambiguities.map((amb, idx) => (
          <div key={amb.component_id} className="card p-4">
            <div className="flex items-start gap-2.5">
              <span className="text-[10px] font-mono text-muted-foreground mt-0.5">
                {idx + 1}.
              </span>
              <div className="flex-1">
                <p className="text-sm mb-2.5">{amb.question}</p>
                <div className="flex flex-wrap gap-1.5">
                  {amb.options.map((opt) => (
                    <button
                      key={opt}
                      onClick={() =>
                        setAnswers((prev) => ({ ...prev, [amb.component_id]: opt }))
                      }
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                        answers[amb.component_id] === opt
                          ? 'bg-accent text-accent-foreground'
                          : 'bg-secondary text-muted-foreground hover:text-foreground'
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
        className={`w-full mt-4 py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors ${
          allAnswered
            ? 'bg-accent text-accent-foreground hover:bg-accent-hover'
            : 'bg-secondary text-muted-foreground cursor-not-allowed'
        }`}
      >
        Generate Terraform
        <ArrowRight className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}

/* ── Generating Step ─────────────────────────────────────────────────────── */

function GeneratingStep() {
  return (
    <div className="flex flex-col items-center justify-center py-20 animate-fade-in">
      <Terminal className="w-6 h-6 text-muted-foreground mb-4" />
      <h2 className="text-base font-medium tracking-tight mb-1">Generating Terraform</h2>
      <p className="text-xs text-muted-foreground">
        Mapping → templating → validation
      </p>
    </div>
  )
}

/* ── Result Step ─────────────────────────────────────────────────────────── */
/* Note: This screen is reachable only after POST /generate succeeds.
   Since the backend is not implemented (Phase 6), this screen cannot be
   reached in normal operation yet. */

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
      {/* Metrics */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        <div className="card p-4">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Validation
          </p>
          <div className="flex items-center gap-1.5">
            {result.validation.valid ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-success" />
                <span className="text-lg font-semibold tracking-tight">Pass</span>
              </>
            ) : (
              <>
                <XCircle className="w-4 h-4 text-error" />
                <span className="text-lg font-semibold tracking-tight">Fail</span>
              </>
            )}
          </div>
        </div>

        <div className="card p-4">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Components
          </p>
          <p className="text-lg font-semibold tracking-tight">
            {diagramSpec?.components.length ?? 0}
          </p>
        </div>

        <div className="card p-4">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
            Connections
          </p>
          <p className="text-lg font-semibold tracking-tight">
            {diagramSpec?.relationships.length ?? 0}
          </p>
        </div>
      </div>

      {/* Errors */}
      {!result.validation.valid && result.validation.errors.length > 0 && (
        <div className="mb-4 p-3 rounded-lg border border-error/20 bg-error/5">
          <p className="text-xs font-medium text-error mb-1.5 flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5" />
            Validation errors
          </p>
          <ul className="space-y-0.5">
            {result.validation.errors.map((err, i) => (
              <li key={i} className="text-[11px] text-muted-foreground font-mono pl-3">
                {err}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Code + Preview */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3 mb-6">
        <div className="lg:col-span-2 card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-border">
            <div className="flex items-center gap-2">
              <FileCode2 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-xs font-medium font-mono">main.tf</span>
            </div>
            <span className="text-[10px] text-muted-foreground font-mono">
              {result.terraform_code.split('\n').length} lines
            </span>
          </div>
          <pre className="p-3 text-[11px] font-mono leading-relaxed overflow-auto max-h-96 scrollbar-thin text-foreground/80">
            <code>{result.terraform_code}</code>
          </pre>
        </div>

        <div className="card p-0 overflow-hidden">
          <div className="px-3 py-2 border-b border-border">
            <span className="text-xs font-medium">Source</span>
          </div>
          {previewUrl ? (
            <img src={previewUrl} alt="Source diagram" className="w-full object-contain p-3" />
          ) : (
            <div className="p-6 text-center text-xs text-muted-foreground">
              No preview
            </div>
          )}
          {diagramSpec && (
            <div className="border-t border-border px-3 py-2">
              <div className="flex flex-wrap gap-1">
                {diagramSpec.components.map((c) => (
                  <span key={c.id} className="badge-neutral text-[10px]">
                    {c.subtype}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={onDownload}
          className="flex-1 py-2.5 rounded-lg bg-accent text-accent-foreground text-sm font-medium flex items-center justify-center gap-2 transition-colors hover:bg-accent-hover"
        >
          <Download className="w-3.5 h-3.5" />
          Download .tf ZIP
        </button>
        <button
          onClick={onReset}
          className="px-4 py-2.5 rounded-lg bg-secondary text-muted-foreground hover:text-foreground text-sm font-medium transition-colors"
        >
          New
        </button>
      </div>
    </div>
  )
}

export default App
