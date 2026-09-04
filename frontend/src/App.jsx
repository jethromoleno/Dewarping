import { useState, useCallback } from 'react'
import Sidebar from './components/Sidebar'
import ImageUploader from './components/ImageUploader'
import QuadEditor from './components/QuadEditor'
import ImageComparison from './components/ImageComparison'
import ProcessingInfo from './components/ProcessingInfo'
import Spinner from './components/Spinner'
import Toast from './components/Toast'
import {
  uploadImage,
  detectBoundaries,
  detectLabel,
  correctImage,
  getImageUrl,
  getImageLabelUrl,
} from './api'

export default function App() {
  const [sessionId, setSessionId] = useState(null)
  const [imageMeta, setImageMeta] = useState(null)
  const [mode, setMode] = useState('automatic')
  const [enableNonlinear, setEnableNonlinear] = useState(false)
  const [suggestedCorners, setSuggestedCorners] = useState(null)
  const [corrected, setCorrected] = useState(false)
  const [processingInfo, setProcessingInfo] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [toast, setToast] = useState(null)
  const [labelUrls, setLabelUrls] = useState([])
  const [labelDetectionInfo, setLabelDetectionInfo] = useState(null)
  const [labelRotation, setLabelRotation] = useState(0)

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type })
    setTimeout(() => setToast(null), 4000)
  }, [])

  const handleRotateLabel = useCallback((delta) => {
    setLabelRotation((prev) => (prev + delta + 360) % 360)
  }, [])

  const handleUpload = useCallback(async (file) => {
    setLoading(true)
    setLoadingMsg('Uploading image...')
    try {
      const res = await uploadImage(file)
      setSessionId(res.image_id)
      setImageMeta({ width: res.width, height: res.height })
      setCorrected(false)
      setProcessingInfo(null)
      setSuggestedCorners(null)
      setLabelUrls([])
      setLabelDetectionInfo(null)
      setLabelRotation(0)
      showToast('Image uploaded successfully', 'success')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Upload failed', 'error')
    } finally {
      setLoading(false)
    }
  }, [showToast])

  const handleDetect = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    setLoadingMsg('Detecting document boundaries...')
    try {
      const res = await detectBoundaries(sessionId)
      if (res.success && res.corners) {
        setSuggestedCorners(res.corners)
        showToast(`Detection successful (score: ${res.score.toFixed(3)})`, 'success')
      } else {
        showToast('Detection failed. Try manual mode.', 'warning')
      }
    } catch (err) {
      showToast(err.response?.data?.detail || 'Detection failed', 'error')
    } finally {
      setLoading(false)
    }
  }, [sessionId, showToast])

  const handleDetectLabel = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    setLoadingMsg('Extracting sticker label...')
    try {
      const res = await detectLabel(sessionId)
      if (res.success && res.labels && res.labels.length > 0) {
        // Only ONE detected label is returned per scan.
        const label = res.labels[0]
        const urls = [{
          url: getImageLabelUrl(sessionId, label.index),
          index: label.index,
          score: label.score,
        }]
        setLabelUrls(urls)
        setLabelRotation(0)
        setLabelDetectionInfo({
          labels: res.labels,
          reason: res.reason,
          extraction_time_ms: res.extraction_time_ms,
        })
        setCorrected(true)
        showToast(
          `1 label extracted (${res.extraction_time_ms.toFixed(0)}ms)`,
          'success'
        )
      } else {
        showToast(res.reason || 'No sticker labels detected. Try manual mode.', 'warning')
      }
    } catch (err) {
      showToast(err.response?.data?.detail || 'Label detection failed', 'error')
    } finally {
      setLoading(false)
    }
  }, [sessionId, showToast])

  const handleCorrect = useCallback(async (corners) => {
    if (!sessionId || !corners) return
    setLoading(true)
    setLoadingMsg('Correcting image...')
    try {
      const res = await correctImage(sessionId, corners, {
        enableNonlinear,
        mode,
      })
      setCorrected(true)
      setLabelUrls([])
      setProcessingInfo(res)
      showToast(`Corrected in ${res.total_time_ms.toFixed(1)}ms`, 'success')
    } catch (err) {
      showToast(err.response?.data?.detail || 'Correction failed', 'error')
    } finally {
      setLoading(false)
    }
  }, [sessionId, enableNonlinear, mode, showToast])

  const handleNewImage = useCallback(() => {
    setSessionId(null)
    setImageMeta(null)
    setCorrected(false)
    setProcessingInfo(null)
    setSuggestedCorners(null)
    setLabelUrls([])
    setLabelDetectionInfo(null)
    setLabelRotation(0)
  }, [])

  return (
    <div className="flex h-screen bg-surface overflow-hidden">
      <Sidebar
        mode={mode}
        setMode={setMode}
        enableNonlinear={enableNonlinear}
        setEnableNonlinear={setEnableNonlinear}
        onDetect={handleDetect}
        onDetectLabel={handleDetectLabel}
        onCorrect={() => {}}
        sessionId={sessionId}
        loading={loading}
      />

      <main className="flex-1 overflow-y-auto p-6 lg:p-8">
        <div className="max-w-6xl mx-auto space-y-6 animate-fade-in">
          <header className="space-y-1">
            <h1 className="text-3xl font-extrabold tracking-tight text-white">
              Image Warp Correction
            </h1>
            <p className="text-gray-400 text-base">
              Upload a distorted image to automatically straighten perspective
              or manually adjust a bounding box.
            </p>
          </header>

          {!sessionId ? (
            <ImageUploader onUpload={handleUpload} loading={loading} />
          ) : (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="badge">
                    <span className="badge-dot" />
                    Session: {sessionId}
                  </div>
                  <div className="badge">
                    {imageMeta?.width} x {imageMeta?.height}
                  </div>
                </div>
                <button className="btn-secondary text-sm" onClick={handleNewImage}>
                  New Image
                </button>
              </div>

              {mode === 'manual' && (
                <QuadEditor
                  sessionId={sessionId}
                  suggestedCorners={suggestedCorners}
                  onCorrect={handleCorrect}
                  loading={loading}
                />
              )}

              {mode === 'automatic' && !corrected && labelUrls.length === 0 && (
                <div className="card text-center py-12">
                  <p className="text-gray-400 mb-4">
                    Click <strong className="text-accent">Extract Label</strong> in the sidebar
                    to automatically detect and extract the sticker label.
                  </p>
                  <p className="text-gray-500 text-sm">
                    Or switch to Manual mode for precise corner placement.
                  </p>
                </div>
              )}

              <ImageComparison
                sessionId={sessionId}
                corrected={corrected}
                labelUrls={labelUrls}
                labelRotation={labelRotation}
                onRotate={handleRotateLabel}
              />

              {(processingInfo || labelDetectionInfo) && (
                <ProcessingInfo
                  sessionId={sessionId}
                  labelInfo={labelDetectionInfo}
                />
              )}
            </div>
          )}
        </div>
      </main>

      {loading && <Spinner message={loadingMsg} />}
      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </div>
  )
}
