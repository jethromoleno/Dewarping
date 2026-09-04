export default function Sidebar({
  mode,
  setMode,
  enableNonlinear,
  setEnableNonlinear,
  onDetect,
  onDetectLabel,
  onCorrect,
  loading,
  sessionId,
}) {
  return (
    <aside className="w-72 bg-surface-dark border-r border-surface-border flex flex-col p-5 space-y-6 overflow-y-auto">
      <div className="space-y-1">
        <h2 className="text-base font-bold text-white tracking-tight">Settings</h2>
        <div className="h-0.5 w-8 bg-accent rounded-full" />
      </div>

      <div className="space-y-3">
        <label className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          Correction Mode
        </label>
        <div className="flex gap-2">
          {['automatic', 'manual'].map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`
                flex-1 py-2.5 px-3 rounded-xl text-sm font-medium capitalize
                transition-all duration-200 border
                ${mode === m
                  ? 'bg-accent/10 border-accent text-accent-light'
                  : 'bg-surface-card border-surface-border text-gray-400 hover:border-gray-500 hover:text-gray-300'
                }
              `}
            >
              {m}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-3">
        <label className="flex items-center gap-3 cursor-pointer group">
          <div className={`
            w-10 h-5 rounded-full relative transition-colors duration-200
            ${enableNonlinear ? 'bg-accent' : 'bg-surface-border'}
          `}>
            <div className={`
              absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all duration-200
              ${enableNonlinear ? 'left-5.5 translate-x-0' : 'left-0.5'}
            `}
              style={{ left: enableNonlinear ? '22px' : '2px' }}
            />
          </div>
          <span className="text-sm text-gray-400 group-hover:text-gray-300 transition-colors">
            Nonlinear Correction
          </span>
        </label>
        <p className="text-xs text-gray-600 leading-relaxed">
          Experimental post-homography correction for mild radial distortion.
        </p>
      </div>

      <div className="h-px bg-surface-border" />

      {mode === 'automatic' && (
        <button
          className="btn-primary w-full text-sm"
          onClick={onDetectLabel}
          disabled={!sessionId || loading}
        >
          Extract Label
        </button>
      )}

      {mode === 'automatic' && (
        <button
          className="btn-secondary w-full text-sm"
          onClick={onDetect}
          disabled={!sessionId || loading}
        >
          Detect Boundaries
        </button>
      )}

      <div className="flex-1" />

      <div className="text-xs text-gray-600 space-y-1">
        <p>Image Warp Correction v1.0</p>
        <p>Powered by OpenCV + FastAPI</p>
      </div>
    </aside>
  )
}
