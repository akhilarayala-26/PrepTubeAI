import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

export async function uploadSyllabus(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}

export async function startAnalysis(filePath) {
  const res = await api.post(`/analyze?file_path=${encodeURIComponent(filePath)}`)
  return res.data
}

export async function getStatus(jobId) {
  const res = await api.get(`/status/${jobId}`)
  return res.data
}

export async function getResults(jobId) {
  const res = await api.get(`/results/${jobId}`)
  return res.data
}

export async function getNotes(jobId) {
  const res = await api.get(`/notes/${jobId}`)
  return res.data
}

export async function getTopics(jobId) {
  const res = await api.get(`/topics/${jobId}`)
  return res.data
}

export default api
