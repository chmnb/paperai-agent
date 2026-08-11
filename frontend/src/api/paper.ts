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

export const askPaperQuestionStream = (
  paperId: string,
  question: string,
  onToken: (token: string) => void,
  onDone: (data: { intent: string; qa_id?: string }) => void,
  onError: (err: Error) => void,
): AbortController => {
  const controller = new AbortController()

  fetch(`/api/v1/papers/${paperId}/qa/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
    },
    body: JSON.stringify({ question }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response body')

      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (data.done) {
              onDone(data)
            } else if (data.token) {
              onToken(data.token)
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') onError(err)
    })

  return controller
}

export const deletePaper = (paperId: string) => request.delete(`/api/v1/papers/${paperId}`)

export const updateReadingStatus = (paperId: string, data: { status?: string; progress?: number; favorite?: boolean }) =>
  request.patch(`/api/v1/papers/${paperId}/status`, data)