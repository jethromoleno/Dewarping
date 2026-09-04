import { useState, useEffect } from 'react'
import { getProcessingInfo } from '../api'

export default function ProcessingInfo({ sessionId, labelInfo }) {
  const [info, setInfo] = useState(null)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    if (sessionId) {
      getProcessingInfo(sessionId).then(setInfo).catch(() => setInfo(null))
    }
  }, [sessionId])

  if (!info && !labelInfo) return null

  return (
    <div className="card-hover animate-slide-up">
      <button
        className="w-full flex items-center justify-between text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <h3 className="section-title">Processing Details</h3>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform duration-300 ${expanded ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="mt-5 space-y-4 animate-fade-in">
          {labelInfo && (
            <InfoSection title="Label Extraction">
              <InfoRow label="Labels Found" value={labelInfo.labels?.length || 0} />
              <InfoRow label="Reason" value={labelInfo.reason} />
              <InfoRow
                label="Time"
                value={`${labelInfo.extraction_time_ms?.toFixed(1)} ms`}
                accent
              />
              {labelInfo.labels?.map((label) => (
                <div key={label.index}>
                  <InfoRow label={`Label ${label.index + 1}`} value={`Score: ${label.score?.toFixed(3)}`} />
                  {label.output_size && (
                    <InfoRow
                      label="Output"
                      value={`${label.output_size[0]} x ${label.output_size[1]}`}
                    />
                  )}
                </div>
              ))}
            </InfoSection>
          )}

          {info && (
            <>
              <InfoSection title="Dimensions">
                <InfoRow label="Source" value={`${info.perspective?.input_size?.[0]} x ${info.perspective?.input_size?.[1]}`} />
                <InfoRow label="Output" value={`${info.perspective?.output_size?.[0]} x ${info.perspective?.output_size?.[1]}`} />
              </InfoSection>

              <InfoSection title="Timing">
                <InfoRow label="Perspective" value={`${info.perspective?.perspective_time_ms?.toFixed(1)} ms`} />
                <InfoRow label="Total" value={`${info.total_time_ms?.toFixed(1)} ms`} accent />
              </InfoSection>

              {info.perspective?.source_corners && (
                <InfoSection title="Detected Corners (TL, TR, BR, BL)">
                  <div className="code-block text-xs mt-2">
                    {JSON.stringify(info.perspective.source_corners, null, 2)}
                  </div>
                </InfoSection>
              )}

              {info.perspective?.homography_matrix && (
                <InfoSection title="Homography Matrix">
                  <div className="code-block text-xs mt-2">
                    {JSON.stringify(info.perspective.homography_matrix, null, 2)}
                  </div>
                </InfoSection>
              )}

              {info.detection?.mode === 'automatic' && (
                <InfoSection title="Detection">
                  <InfoRow label="Score" value={info.detection.score?.toFixed(3)} />
                  <InfoRow label="Reason" value={info.detection.reason} />
                </InfoSection>
              )}

              <InfoSection title="Nonlinear Correction">
                <InfoRow
                  label="Applied"
                  value={info.nonlinear?.applied ? 'Yes' : 'No'}
                  accent={info.nonlinear?.applied}
                />
                {info.nonlinear?.applied && (
                  <InfoRow label="Method" value={info.nonlinear.method} />
                )}
              </InfoSection>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function InfoSection({ title, children }) {
  return (
    <div>
      <h4 className="text-sm font-semibold text-white/80 mb-2">{title}</h4>
      <div className="space-y-1.5">{children}</div>
    </div>
  )
}

function InfoRow({ label, value, accent = false }) {
  return (
    <div className="flex items-center justify-between py-1">
      <span className="text-xs text-gray-500">{label}</span>
      <span className={`text-sm font-mono ${accent ? 'text-accent-light' : 'text-gray-300'}`}>
        {value}
      </span>
    </div>
  )
}
