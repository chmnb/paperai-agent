import request from './index'

export const uploadPaper = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/v1/papers/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
}

export const getPaperList = (params?: { skip?: number; limit?: number; status?: string; search?: string }) =>
  request.get('/api/v1/papers', { params })

export const getPaper = (paperId: string) => request.get(`/api/v1/papers/${paperId}`)

export const getPaperSections = (paperId: string) => request.get(`/api/v1/papers/${paperId}/sections`)

export const askPaperQuestion = (paperId: string, question: string) =>
  request.post(`/api/v1/papers/${paperId}/qa`, { question })

export const deletePaper = (paperId: string) => request.delete(`/api/v1/papers/${paperId}`)

export const updateReadingStatus = (paperId: string, data: { status?: string; progress?: number; favorite?: boolean }) =>
  request.patch(`/api/v1/papers/${paperId}/status`, data)