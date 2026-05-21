<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

const router = useRouter()
const credentials = reactive({
  usuario: '',
  contrasena: '',
})

const loading = ref(false)
const errorMessage = ref('')

const login = async () => {
  errorMessage.value = ''

  const usuario = credentials.usuario.trim()
  const contrasena = credentials.contrasena

  if (!usuario || !contrasena) {
    errorMessage.value = 'Introduce usuario y contrasena.'
    return
  }

  loading.value = true

  try {
    const response = await fetch(`${API_BASE_URL}/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        usuario,
        contrasena,
        contraseña: contrasena,
      }),
    })

    if (response.status === 401) {
      throw new Error('Usuario o contrasena incorrectos.')
    }

    if (!response.ok) {
      throw new Error('No se ha podido iniciar sesion. Revisa que el backend exponga POST /api/v1/login.')
    }

    const data = await response.json()
    localStorage.setItem('smartq_user', JSON.stringify(data.usuario ?? data.user ?? data))
    await router.push({ name: 'menu' })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Error iniciando sesion.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <main class="login-page">
    <section class="login-shell">
      <span class="kicker">SmartQ</span>
      <h1>Login</h1>

      <form class="login-form" @submit.prevent="login">
        <label>
          Usuario
          <input v-model="credentials.usuario" type="text" autocomplete="username" />
        </label>

        <label>
          Contrasena
          <input v-model="credentials.contrasena" type="password" autocomplete="current-password" />
        </label>

        <p v-if="errorMessage" class="form-error" role="alert">{{ errorMessage }}</p>

        <button type="submit" :disabled="loading">
          {{ loading ? 'Entrando...' : 'Entrar' }}
        </button>
      </form>
    </section>
  </main>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 32px;
  background:
    radial-gradient(circle at top left, rgba(0, 132, 61, 0.16), transparent 30%),
    linear-gradient(135deg, #f5f8f3 0%, #e9f1ea 48%, #f8faf8 100%);
  color: #173326;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.login-shell {
  width: min(420px, 100%);
  display: grid;
  gap: 18px;
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

h1 {
  margin: 0;
  font-size: clamp(2.4rem, 10vw, 4.2rem);
  line-height: 1;
}

.login-form {
  display: grid;
  gap: 14px;
  padding: 22px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: 0 22px 50px rgba(23, 51, 38, 0.12);
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

.form-error {
  margin: 0;
  color: #b5161b;
  font-size: 0.92rem;
  font-weight: 700;
  line-height: 1.4;
}

button {
  min-height: 46px;
  border: 0;
  border-radius: 8px;
  background: #00843d;
  color: #ffffff;
  font: inherit;
  font-weight: 800;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.62;
}
</style>
