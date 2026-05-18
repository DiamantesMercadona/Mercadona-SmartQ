<template>
  <div class="test-view">
    <h2>Backend Test</h2>

    <section>
      <h3>GET /queues</h3>
      <p class="description">Obtiene todas las colas del sistema</p>
      <button @click="testGetQueues">Ejecutar</button>
    </section>

    <section>
      <h3>GET /queues/:id</h3>
      <p class="description">Obtiene el estado de una cola por ID</p>
      <label>
        ID de cola
        <input v-model.number="queueId" type="number" min="1" placeholder="1" />
      </label>
      <button @click="testGetQueue">Ejecutar</button>
    </section>

    <section>
      <h3>POST /queues/:id</h3>
      <p class="description">Actualiza la longitud y estado de una cola</p>
      <label>
        ID de cola
        <input v-model.number="updateId" type="number" min="1" placeholder="1" />
      </label>
      <label>
        Longitud
        <input v-model.number="updateLength" type="number" min="0" placeholder="0" />
      </label>
      <label>
        Estado
        <select v-model="updateStatus">
          <option value="activa">activa</option>
          <option value="cerrada">cerrada</option>
        </select>
      </label>
      <button @click="testUpdateQueue">Ejecutar</button>
    </section>

    <section>
      <h3>POST /video/events</h3>
      <p class="description">Publica un evento de vídeo con el estado de una caja</p>
      <label>
        ID de caja
        <input v-model.number="eventCajaId" type="number" min="1" placeholder="1" />
      </label>
      <label>
        Personas en cola
        <input v-model.number="eventPeople" type="number" min="0" placeholder="0" />
      </label>
      <label>
        Estado
        <select v-model="eventStatus">
          <option value="activa">activa</option>
          <option value="cerrada">cerrada</option>
        </select>
      </label>
      <button @click="testVideoEvent">Ejecutar</button>
    </section>

    <section>
      <h3>GET /redis/health</h3>
      <p class="description">Comprueba la conexión con Redis</p>
      <button @click="testHealth">Ejecutar</button>
    </section>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import {
  getQueues,
  getQueue,
  updateQueue,
  publishVideoEvent,
  checkHealth,
} from '../services/backendApi.js'

const queueId = ref(1)
const updateId = ref(1)
const updateLength = ref(0)
const updateStatus = ref('activa')
const eventCajaId = ref(1)
const eventPeople = ref(0)
const eventStatus = ref('activa')

async function testGetQueues() {
  try {
    const data = await getQueues()
    console.log('[GET /queues]', data)
  } catch (e) {
    console.error('[GET /queues] Error:', e)
  }
}

async function testGetQueue() {
  try {
    const data = await getQueue(queueId.value)
    console.log(`[GET /queues/${queueId.value}]`, data)
  } catch (e) {
    console.error(`[GET /queues/${queueId.value}] Error:`, e)
  }
}

async function testUpdateQueue() {
  try {
    const data = await updateQueue(updateId.value, updateLength.value, updateStatus.value)
    console.log(`[POST /queues/${updateId.value}]`, data)
  } catch (e) {
    console.error(`[POST /queues/${updateId.value}] Error:`, e)
  }
}

async function testVideoEvent() {
  try {
    const data = await publishVideoEvent(eventCajaId.value, eventPeople.value, eventStatus.value)
    console.log('[POST /video/events]', data)
  } catch (e) {
    console.error('[POST /video/events] Error:', e)
  }
}

async function testHealth() {
  try {
    const data = await checkHealth()
    console.log('[GET /redis/health]', data)
  } catch (e) {
    console.error('[GET /redis/health] Error:', e)
  }
}
</script>

<style scoped>
.test-view {
  padding: 24px;
  font-family: monospace;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

h2 {
  margin: 0;
}

section {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

h3 {
  margin: 0;
  width: 100%;
  font-size: 13px;
  color: #888;
}

.description {
  margin: 0;
  width: 100%;
  font-size: 12px;
  color: #555;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: #aaa;
}

input,
select {
  padding: 4px 8px;
  border: 1px solid #444;
  border-radius: 4px;
  background: #1e1e1e;
  color: #eee;
  font-size: 13px;
  width: 100px;
}

button {
  padding: 4px 14px;
  border: 1px solid #555;
  border-radius: 4px;
  background: #2d2d2d;
  color: #eee;
  cursor: pointer;
  font-size: 13px;
}

button:hover {
  background: #3d3d3d;
}
</style>
