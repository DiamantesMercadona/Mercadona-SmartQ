import axios from 'axios'

const http = axios.create({ baseURL: import.meta.env.VITE_API_PREFIX || '/api/v1' })

export async function getQueues() {
  const res = await http.get('/queues')
  return res.data
}

export async function getQueue(queueId) {
  const res = await http.get(`/queues/${queueId}`)
  return res.data
}

export async function updateQueue(queueId, length, status) {
  const res = await http.post(`/queues/${queueId}`, { length, status })
  return res.data
}

export async function publishVideoEvent(cajaId, peopleCount, queueStatus) {
  const res = await http.post('/video/events', {
    camera_id: 'simulador-3d',
    zone: `Caja_${cajaId}`,
    people_count: peopleCount,
    metadata: { status: queueStatus },
  })
  return res.data
}

export async function checkHealth() {
  const res = await http.get('/redis/health')
  return res.data
}
