import { useRef, useEffect, useState, useCallback } from 'react'
import { fabric } from 'fabric'
import { getImageUrl } from '../api'

const CANVAS_MAX_WIDTH = 700

export default function QuadEditor({ sessionId, suggestedCorners, onCorrect, loading }) {
  const canvasRef = useRef(null)
  const fabricRef = useRef(null)
  const [corners, setCorners] = useState(null)
  const [imageSize, setImageSize] = useState({ width: 0, height: 0 })

  const initCanvas = useCallback(() => {
    if (!canvasRef.current || fabricRef.current) return

    const canvas = new fabric.Canvas(canvasRef.current, {
      selection: false,
      backgroundColor: '#111111',
    })
    fabricRef.current = canvas

    canvas.on('object:modified', () => sendCorners(canvas))
    canvas.on('mouse:up', () => sendCorners(canvas))
  }, [])

  const sendCorners = useCallback((canvas) => {
    const objs = canvas.getObjects()
    const poly = objs.find((o) => o.type === 'polygon')
    if (!poly) return

    const matrix = poly.calcTransformMatrix()
    const pts = poly.points.map((p) => {
      const pt = fabric.util.transformPoint(
        new fabric.Point(p.x - poly.pathOffset.x, p.y - poly.pathOffset.y),
        matrix
      )
      return [pt.x, pt.y]
    })
    setCorners(pts)
  }, [])

  const loadCanvas = useCallback(async () => {
    const canvas = fabricRef.current
    if (!canvas || !sessionId) return

    const img = await loadImage(getImageUrl(sessionId, 'display'))
    const aspect = img.height / img.width
    const w = Math.min(CANVAS_MAX_WIDTH, img.width)
    const h = Math.round(w * aspect)

    canvas.setDimensions({ width: w, height: h })
    setImageSize({ width: w, height: h })

    const bg = new fabric.Image(img, {
      left: 0,
      top: 0,
      selectable: false,
      evented: false,
      scaleX: w / img.width,
      scaleY: h / img.height,
    })
    canvas.setBackgroundImage(bg, () => canvas.renderAll())

    const defaultCorners = getSuggestedCorners(w, h)
    drawPolygon(canvas, defaultCorners)
  }, [sessionId])

  useEffect(() => {
    initCanvas()
    return () => {
      if (fabricRef.current) {
        fabricRef.current.dispose()
        fabricRef.current = null
      }
    }
  }, [initCanvas])

  useEffect(() => {
    if (sessionId) {
      setTimeout(() => loadCanvas(), 100)
    }
  }, [sessionId, loadCanvas])

  useEffect(() => {
    if (suggestedCorners && fabricRef.current && imageSize.width > 0) {
      const canvas = fabricRef.current
      const scaleX = imageSize.width / (imageSize.width || 1)
      const scaleY = imageSize.height / (imageSize.height || 1)
      const scaled = suggestedCorners.map(([x, y]) => [x * scaleX, y * scaleY])
      drawPolygon(canvas, scaled)
    }
  }, [suggestedCorners, imageSize])

  const handleCorrect = () => {
    if (corners && sessionId) {
      onCorrect(corners)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="section-title">Manual Bounding Box</h3>
        <div className="flex gap-2">
          <button
            className="btn-secondary text-xs px-3 py-1.5"
            onClick={() => {
              if (fabricRef.current && imageSize.width > 0) {
                drawPolygon(fabricRef.current, getSuggestedCorners(imageSize.width, imageSize.height))
              }
            }}
          >
            Reset
          </button>
          <button
            className="btn-primary text-xs px-4 py-1.5"
            onClick={handleCorrect}
            disabled={!corners || loading}
          >
            Correct Image
          </button>
        </div>
      </div>

      <div className="card p-0 overflow-hidden">
        <canvas ref={canvasRef} />
      </div>

      {corners && (
        <div className="flex items-center gap-2">
          <span className="badge">
            <span className="badge-dot" />
            Corners: 4/4
          </span>
          <span className="text-xs text-gray-600">
            Drag the red handles to adjust the bounding box
          </span>
        </div>
      )}
    </div>
  )
}

function loadImage(src) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => resolve(img)
    img.onerror = reject
    img.src = src
  })
}

function getSuggestedCorners(w, h) {
  const mx = Math.round(w * 0.1)
  const my = Math.round(h * 0.1)
  return [
    [mx, my],
    [w - mx, my],
    [w - mx, h - my],
    [mx, h - my],
  ]
}

function drawPolygon(canvas, cornerPoints) {
  canvas.getObjects().forEach((obj) => {
    if (obj.type === 'polygon') canvas.remove(obj)
  })

  const points = cornerPoints.map(([x, y]) => ({ x, y }))
  const poly = new fabric.Polygon(points, {
    fill: 'rgba(220, 38, 38, 0.10)',
    stroke: '#dc2626',
    strokeWidth: 2.5,
    objectCaching: false,
    selectable: true,
    evented: true,
    lockRotation: true,
    lockScalingX: true,
    lockScalingY: true,
    hasControls: false,
    hasBorders: false,
    shadow: new fabric.Shadow({
      color: 'rgba(220, 38, 38, 0.35)',
      blur: 8,
      offsetX: 0,
      offsetY: 0,
    }),
  })

  enableVertexEditing(poly)
  canvas.add(poly)
  canvas.setActiveObject(poly)
  canvas.renderAll()
}

function enableVertexEditing(poly) {
  const lastIdx = poly.points.length - 1

  poly.cornerStyle = 'circle'
  poly.cornerColor = '#dc2626'
  poly.cornerStrokeColor = '#ffffff'
  poly.cornerSize = 14
  poly.cornerStrokeWidth = 2
  poly.hasBorders = false
  poly.hasControls = true

  poly.controls = poly.points.reduce((acc, _, index) => {
    acc[`p${index}`] = new fabric.Control({
      positionHandler: polygonPositionHandler,
      actionHandler: anchorWrapper(
        index > 0 ? index - 1 : lastIdx,
        actionHandler
      ),
      actionName: 'modifyPolygon',
      pointIndex: index,
      render: (ctx, left, top, _styleOverride, _fabricObject) => {
        const size = 14
        ctx.save()

        ctx.beginPath()
        ctx.arc(left, top, size / 2, 0, Math.PI * 2, false)
        ctx.fillStyle = '#dc2626'
        ctx.fill()
        ctx.lineWidth = 2
        ctx.strokeStyle = '#ffffff'
        ctx.stroke()

        ctx.beginPath()
        ctx.arc(left, top, size / 2 + 5, 0, Math.PI * 2, false)
        ctx.strokeStyle = 'rgba(220, 38, 38, 0.35)'
        ctx.lineWidth = 1
        ctx.stroke()

        ctx.restore()
      },
    })
    return acc
  }, {})
}

function getObjectSizeWithStroke(object) {
  const stroke = new fabric.Point(
    object.strokeUniform ? 1 / object.scaleX : 1,
    object.strokeUniform ? 1 / object.scaleY : 1
  ).multiply(object.strokeWidth)
  return new fabric.Point(object.width + stroke.x, object.height + stroke.y)
}

function polygonPositionHandler(dim, finalMatrix, fabricObject) {
  const point = fabricObject.points[this.pointIndex]
  const local = {
    x: point.x - fabricObject.pathOffset.x,
    y: point.y - fabricObject.pathOffset.y,
  }
  return fabric.util.transformPoint(
    local,
    fabric.util.multiplyTransformMatrices(
      fabricObject.canvas.viewportTransform,
      fabricObject.calcTransformMatrix()
    )
  )
}

function actionHandler(eventData, transform, x, y) {
  const poly = transform.target
  const control = poly.controls[poly.__corner]
  const mouseLocalPosition = poly.toLocalPoint(
    new fabric.Point(x, y),
    'center',
    'center'
  )
  const polygonBaseSize = getObjectSizeWithStroke(poly)
  const size = poly._getTransformedDimensions(0, 0)
  const finalPointPosition = {
    x: (mouseLocalPosition.x * polygonBaseSize.x) / size.x + poly.pathOffset.x,
    y: (mouseLocalPosition.y * polygonBaseSize.y) / size.y + poly.pathOffset.y,
  }
  poly.points[control.pointIndex] = finalPointPosition
  return true
}

function anchorWrapper(anchorIndex, fn) {
  return function (eventData, transform, x, y) {
    const fabricObject = transform.target
    const absolutePoint = fabric.util.transformPoint(
      {
        x: fabricObject.points[anchorIndex].x - fabricObject.pathOffset.x,
        y: fabricObject.points[anchorIndex].y - fabricObject.pathOffset.y,
      },
      fabricObject.calcTransformMatrix()
    )
    const actionPerformed = fn(eventData, transform, x, y)
    const polygonBaseSize = getObjectSizeWithStroke(fabricObject)
    const newX = (fabricObject.points[anchorIndex].x - fabricObject.pathOffset.x) / polygonBaseSize.x
    const newY = (fabricObject.points[anchorIndex].y - fabricObject.pathOffset.y) / polygonBaseSize.y
    fabricObject.setPositionByOrigin(absolutePoint, newX + 0.5, newY + 0.5)
    return actionPerformed
  }
}
