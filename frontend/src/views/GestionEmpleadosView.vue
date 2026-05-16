<script setup>
import { computed, reactive, ref } from 'vue'

const employees = ref([
  { id: 1, name: 'Laura', surname: 'Martinez Soto' },
  { id: 2, name: 'Carlos', surname: 'Navarro Gil' },
  { id: 3, name: 'Nuria', surname: 'Lopez Pardo' },
  { id: 4, name: 'Hugo', surname: 'Ramirez Vega' },
  { id: 5, name: 'Marta', surname: 'Serra Ruiz' },
  { id: 6, name: 'Sergio', surname: 'Campos Mora' },
  { id: 7, name: 'Aina', surname: 'Torres Vidal' },
  { id: 8, name: 'Pau', surname: 'Ferrer Soler' },
])

const newEmployee = reactive({
  name: '',
  surname: '',
})

const weekSchedule = reactive([
  {
    day: 'Lunes',
    morning: [1, 2, 3],
    afternoon: [4, 5],
  },
  {
    day: 'Martes',
    morning: [6, 1],
    afternoon: [7, 8, 2],
  },
  {
    day: 'Miercoles',
    morning: [3, 4],
    afternoon: [5, 6, 7],
  },
  {
    day: 'Jueves',
    morning: [8, 1, 5],
    afternoon: [2, 3],
  },
  {
    day: 'Viernes',
    morning: [4, 7],
    afternoon: [6, 8, 1],
  },
  {
    day: 'Sabado',
    morning: [2, 5, 6],
    afternoon: [3, 4],
  },
])

const totalAssignments = computed(() =>
  weekSchedule.reduce((total, day) => total + day.morning.length + day.afternoon.length, 0),
)

const getEmployee = (id) => employees.value.find((employee) => employee.id === id)

const addEmployee = () => {
  const name = newEmployee.name.trim()
  const surname = newEmployee.surname.trim()

  if (!name || !surname) return

  const employee = {
    id: Date.now(),
    name,
    surname,
  }

  employees.value.push(employee)
  weekSchedule[0].morning.push(employee.id)
  newEmployee.name = ''
  newEmployee.surname = ''
}

const moveEmployee = (day, shift, index, direction) => {
  const list = day[shift]
  const newIndex = index + direction

  if (newIndex < 0 || newIndex >= list.length) return

  const [employeeId] = list.splice(index, 1)
  list.splice(newIndex, 0, employeeId)
}
</script>

<template>
  <main class="employees-page">
    <section class="page-shell">
      <header class="hero">
        <RouterLink class="back-link" :to="{ name: 'menu' }">Volver al menu</RouterLink>
        <span class="kicker">SmartQ</span>
        <div class="hero-content">
          <div>
            <h1>Gestion de empleados</h1>
            <p>
              Organiza el personal por turnos de lunes a sabado. Los datos son temporales hasta
              conectar la base de datos.
            </p>
          </div>

          <div class="summary">
            <strong>{{ employees.length }}</strong>
            <span>empleados</span>
            <strong>{{ totalAssignments }}</strong>
            <span>asignaciones</span>
          </div>
        </div>
      </header>

      <form class="employee-form" @submit.prevent="addEmployee">
        <label>
          Nombre
          <input v-model="newEmployee.name" type="text" placeholder="Ej. Ana" />
        </label>

        <label>
          Apellidos
          <input v-model="newEmployee.surname" type="text" placeholder="Ej. Garcia Perez" />
        </label>

        <button type="submit">Anadir empleado</button>
      </form>

      <section class="schedule-grid" aria-label="Turnos semanales">
        <article v-for="day in weekSchedule" :key="day.day" class="day-card">
          <h2>{{ day.day }}</h2>

          <div class="shift-block">
            <div class="shift-heading">
              <h3>Manana</h3>
              <span>{{ day.morning.length }} empleados</span>
            </div>

            <ol class="employee-list">
              <li v-for="(employeeId, index) in day.morning" :key="employeeId">
                <span class="position">{{ index + 1 }}</span>
                <span class="employee-name">
                  {{ getEmployee(employeeId)?.name }} {{ getEmployee(employeeId)?.surname }}
                </span>
                <div class="order-actions">
                  <button
                    type="button"
                    aria-label="Subir empleado"
                    :disabled="index === 0"
                    @click="moveEmployee(day, 'morning', index, -1)"
                  >
                    ^
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.morning.length - 1"
                    @click="moveEmployee(day, 'morning', index, 1)"
                  >
                    v
                  </button>
                </div>
              </li>
            </ol>
          </div>

          <div class="shift-block afternoon">
            <div class="shift-heading">
              <h3>Tarde</h3>
              <span>{{ day.afternoon.length }} empleados</span>
            </div>

            <ol class="employee-list">
              <li v-for="(employeeId, index) in day.afternoon" :key="employeeId">
                <span class="position">{{ index + 1 }}</span>
                <span class="employee-name">
                  {{ getEmployee(employeeId)?.name }} {{ getEmployee(employeeId)?.surname }}
                </span>
                <div class="order-actions">
                  <button
                    type="button"
                    aria-label="Subir empleado"
                    :disabled="index === 0"
                    @click="moveEmployee(day, 'afternoon', index, -1)"
                  >
                    ^
                  </button>
                  <button
                    type="button"
                    aria-label="Bajar empleado"
                    :disabled="index === day.afternoon.length - 1"
                    @click="moveEmployee(day, 'afternoon', index, 1)"
                  >
                    v
                  </button>
                </div>
              </li>
            </ol>
          </div>
        </article>
      </section>
    </section>
  </main>
</template>

<style scoped>
.employees-page {
  min-height: 100vh;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.16), transparent 28%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%);
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.page-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 24px;
}

.hero {
  display: grid;
  gap: 16px;
}

.back-link {
  width: fit-content;
  color: #d71920;
  font-weight: 800;
  text-decoration: none;
}

.kicker {
  width: fit-content;
  display: inline-flex;
  align-items: center;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid rgba(0, 132, 61, 0.2);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #007d3a;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-content {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: end;
}

h1 {
  margin: 0 0 10px;
  font-size: clamp(2.4rem, 6vw, 4.5rem);
  line-height: 1;
}

p {
  max-width: 720px;
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

.summary {
  min-width: 168px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 10px;
  padding: 18px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 16px 38px rgba(23, 51, 38, 0.1);
}

.summary strong {
  color: #00843d;
  font-size: 1.55rem;
  line-height: 1;
}

.summary span {
  align-self: center;
  color: #627267;
  font-size: 0.92rem;
}

.employee-form {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) minmax(220px, 1.3fr) auto;
  gap: 14px;
  align-items: end;
  padding: 20px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 18px 44px rgba(23, 51, 38, 0.1);
}

label {
  display: grid;
  gap: 8px;
  color: #506459;
  font-size: 0.9rem;
  font-weight: 800;
}

input {
  width: 100%;
  min-height: 46px;
  box-sizing: border-box;
  border: 1px solid rgba(23, 51, 38, 0.18);
  border-radius: 8px;
  padding: 0 14px;
  background: #ffffff;
  color: #173326;
  font: inherit;
}

input:focus {
  border-color: #00843d;
  outline: 3px solid rgba(0, 132, 61, 0.18);
}

button {
  min-height: 42px;
  border: 0;
  border-radius: 8px;
  background: #00843d;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.employee-form button {
  min-height: 46px;
  padding: 0 18px;
}

.schedule-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.day-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 18px 42px rgba(23, 51, 38, 0.1);
}

h2 {
  margin: 0;
  font-size: 1.35rem;
}

.shift-block {
  display: grid;
  gap: 10px;
}

.shift-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

h3 {
  margin: 0;
  color: #00843d;
  font-size: 0.95rem;
  text-transform: uppercase;
}

.afternoon h3 {
  color: #d71920;
}

.shift-heading span {
  color: #627267;
  font-size: 0.82rem;
  font-weight: 700;
}

.employee-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.employee-list li {
  min-height: 50px;
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border: 1px solid rgba(23, 51, 38, 0.1);
  border-radius: 8px;
  background: #ffffff;
}

.position {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: #f0f5ef;
  color: #00843d;
  font-weight: 900;
}

.employee-name {
  overflow-wrap: anywhere;
  font-weight: 800;
}

.order-actions {
  display: flex;
  gap: 6px;
}

.order-actions button {
  width: 34px;
  min-height: 34px;
  background: #173326;
}

@media (max-width: 980px) {
  .hero-content,
  .employee-form,
  .schedule-grid {
    grid-template-columns: 1fr;
  }

  .summary {
    width: fit-content;
  }
}

@media (max-width: 680px) {
  .employees-page {
    padding: 24px 18px;
  }

  .employee-list li {
    grid-template-columns: 34px minmax(0, 1fr);
  }

  .order-actions {
    grid-column: 2;
  }
}
</style>
