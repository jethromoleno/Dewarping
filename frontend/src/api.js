import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

export async function uploadImage(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function detectBoundaries(imageId) {
  const { data } = await api.post('/detect', { image_id: imageId })
  return data
}

export async function detectLabel(imageId) {
  const { data } = await api.post('/detect-label', { image_id: imageId })
  return data
}

export async function correctImage(imageId, corners, options = {}) {
  const { data } = await api.post('/correct', {
    image_id: imageId,
    corners,
    enable_nonlinear: options.enableNonlinear || false,
    mode: options.mode || 'automatic',
  })
  return data
}

export async function updateManualCorners(imageId, corners) {
  const { data } = await api.post('/manual-corners', {
    image_id: imageId,
    corners,
  })
  return data
}

export async function getProcessingInfo(imageId) {
  const { data } = await api.get(`/processing-info/${imageId}`)
  return data
}

export function getImageUrl(imageId, type = 'original') {
  return `/api/images/${imageId}/${type}`
}

export function getImageLabelUrl(imageId, index = 0) {
  return `/api/images/${imageId}/label/${index}`
}

export function getDownloadUrl(imageId) {
  return `/api/images/${imageId}/corrected-download`
}
