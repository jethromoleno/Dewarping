import { getImageUrl, getDownloadUrl } from '../api'

export default function ImageComparison({
  sessionId,
  corrected,
  labelUrls,
  labelRotation = 0,
  onRotate = () => {},
}) {
  const hasLabels = labelUrls && labelUrls.length > 0
  const rightSrc = !hasLabels && corrected ? getImageUrl(sessionId, 'corrected') : null

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-3 animate-fade-in">
        <h3 className="section-title">Original</h3>
        <div className="card p-0 overflow-hidden group">
          <img
            src={getImageUrl(sessionId, corrected ? 'original-overlay' : 'original')}
            alt="Original"
            className="w-full h-auto transition-transform duration-500 group-hover:scale-[1.02]"
          />
        </div>
      </div>

      <div className="space-y-3 animate-fade-in" style={{ animationDelay: '0.1s' }}>
        <h3 className="section-title">{hasLabels ? 'Extracted Labels' : 'Corrected'}</h3>
        <div className="card p-0 overflow-hidden group relative">
          {hasLabels && (
            <div className="absolute top-2 right-2 z-10 flex items-center gap-2 bg-surface/80 backdrop-blur rounded-lg p-1">
              <button
                type="button"
                onClick={() => onRotate(-90)}
                title="Rotate left (counter-clockwise)"
                className="p-1.5 rounded-md text-gray-300 hover:text-accent hover:bg-surface-border/40 transition-colors"
                aria-label="Rotate left"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 12a9 9 0 109-9 9.75 9.75 0 00-6.74 2.74L3 8" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 3v5h5" />
                </svg>
              </button>
              <button
                type="button"
                onClick={() => onRotate(90)}
                title="Rotate right (clockwise)"
                className="p-1.5 rounded-md text-gray-300 hover:text-accent hover:bg-surface-border/40 transition-colors"
                aria-label="Rotate right"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 12a9 9 0 11-9-9 9.75 9.75 0 016.74 2.74L21 8" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 3v5h-5" />
                </svg>
              </button>
            </div>
          )}
          {hasLabels ? (
            <div className="flex items-center justify-center p-4">
              <img
                src={labelUrls[0].url}
                alt={`Label ${labelUrls[0].index + 1}`}
                className="max-w-full max-h-[70vh] object-contain transition-transform duration-300"
                style={{ transform: `rotate(${labelRotation}deg)` }}
              />
            </div>
          ) : rightSrc ? (
            <>
              <img
                src={rightSrc}
                alt="Corrected"
                className="w-full h-auto transition-transform duration-500 group-hover:scale-[1.02]"
              />
              <div className="p-4 border-t border-surface-border">
                <a
                  href={getDownloadUrl(sessionId)}
                  download="corrected_image.png"
                  className="btn-secondary w-full flex items-center justify-center gap-2 text-sm no-underline"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Corrected Image
                </a>
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center py-24 text-gray-600 italic">
              Corrected image will appear here
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
