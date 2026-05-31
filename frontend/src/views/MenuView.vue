<template>
  <main class="menu-page">
    <section class="menu-shell">
      <div class="brand-block">
        <div class="brand-card">
          <div class="logo-container">
            <img class="menu-logo" src="/assets/logo_menu.png" alt="Mercadona" />
          </div>
          <div class="brand-separator"></div>
          <div class="smartq-badge">
            <span class="smartq-text">Smart<span class="q-highlight">Q</span></span>
            <span class="smartq-tag">Queue Manager</span>
          </div>
        </div>
        <h1>Panel de Control</h1>
        <p>Elige el módulo con el que deseas trabajar y accede a las herramientas de gestión de la tienda.</p>
      </div>

      <div class="actions-list">
        <RouterLink class="menu-action simulation" :to="{ name: 'simulacion' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" style="width: 28px; height: 28px;">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 17.25v1.007a3 3 0 01-.879 2.122L7.5 21h9l-.621-.621A3 3 0 0115 18.257V17.25m6-12V15a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 15V5.25m18 0A2.25 2.25 0 0018.75 3H5.25A2.25 2.25 0 003 5.25m18 0V12a2.25 2.25 0 01-2.25 2.25H5.25A2.25 2.25 0 013 12V5.25" />
            </svg>
          </span>
          <span>
            <strong>Monitor de colas</strong>
            <small>Visualiza el flujo de clientes, el estado de las colas en tiempo real, y ejecuta acciones manuales.</small>
          </span>
        </RouterLink>

        <RouterLink class="menu-action staff" :to="{ name: 'gestion-empleados' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="width: 28px; height: 28px;">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
          </span>
          <span>
            <strong>Gestión de empleados</strong>
            <small>Consulta y modifica la plantilla de empleados y su asignación de turnos.</small>
          </span>
        </RouterLink>
        <RouterLink class="menu-action graficas" :to="{ name: 'graficas-view' }">
          <span class="action-icon">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.2" stroke="currentColor" style="width: 28px; height: 28px;">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
            </svg>
          </span>
          <span>
            <strong>Gráficas y estadísticas</strong>
            <small>Consulta información histórica sobre tiempos de espera, tendencias, y métricas por caja y fecha.</small>
          </span>
        </RouterLink>
      </div>
    </section>
  </main>
</template>

<style scoped>
.menu-page {
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

.menu-shell {
  width: min(920px, 100%);
  display: grid;
  gap: 28px;
}

.brand-block {
  max-width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 16px;
  margin-bottom: 12px;
}

.brand-card {
  display: inline-flex;
  align-items: center;
  gap: 36px;
  padding: 24px 44px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.384);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(0, 132, 61, 0.12);
  box-shadow: 0 12px 32px rgba(0, 132, 61, 0.05);
  margin-bottom: 0;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.brand-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 16px 40px rgba(0, 132, 61, 0.08);
  border-color: rgba(0, 132, 61, 0.25);
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
}

.menu-logo {
  height: 80px;
  width: auto;
  object-fit: contain;
}

.brand-separator {
  width: 1px;
  height: 84px;
  background: linear-gradient(180deg, transparent, rgba(0, 132, 61, 0.25), transparent);
}

.smartq-badge {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.smartq-text {
  font-size: 3.2rem;
  font-weight: 850;
  letter-spacing: -0.03em;
  line-height: 1;
  color: #173326;
}

.q-highlight {
  background: linear-gradient(135deg, #00843d 0%, #00b050 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.smartq-tag {
  font-size: 0.88rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: #00843d;
  background: rgba(0, 132, 61, 0.08);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}

h1 {
  margin: 48px 0 0;
  font-size: clamp(1.8rem, 4vw, 2.5rem);
  line-height: 1;
}

p {
  margin: 0;
  color: #506459;
  font-size: 1.08rem;
  line-height: 1.6;
}

/* Stack on small screens */
@media (max-width: 600px) {
  .brand-card {
    flex-direction: column;
    gap: 16px;
    padding: 20px 24px;
    width: 100%;
    max-width: 320px;
  }
  
  .brand-separator {
    width: 80%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0, 132, 61, 0.25), transparent);
  }
  
  .smartq-badge {
    align-items: center;
  }
}

.actions-list {
  display: grid;
  gap: 14px;
}

.menu-action {
  min-height: 118px;
  display: flex;
  align-items: center;
  gap: 18px;
  padding: 22px 24px;
  border: 1px solid rgba(23, 51, 38, 0.12);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 22px 50px rgba(23, 51, 38, 0.12);
  color: inherit;
  text-decoration: none;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.menu-action:hover {
  transform: translateY(-4px);
  border-color: rgba(0, 132, 61, 0.42);
  box-shadow: 0 28px 60px rgba(23, 51, 38, 0.16);
}

.menu-action:focus-visible {
  outline: 3px solid rgba(0, 132, 61, 0.28);
  outline-offset: 4px;
}

.action-icon {
  flex: 0 0 54px;
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  color: white;
  font-size: 1.35rem;
  font-weight: 900;
}

.simulation .action-icon {
  background: #00843d;
}

.staff .action-icon {
  background: #ffa101;
}

.graficas .action-icon {
  background: #173326;
}

strong {
  display: block;
  margin-bottom: 8px;
  font-size: 1.25rem;
}

small {
  display: block;
  color: #627267;
  font-size: 0.94rem;
  line-height: 1.45;
}

@media (max-width: 680px) {
  .menu-page {
    place-items: start;
    padding: 24px 18px;
  }

  .menu-action {
    min-height: 128px;
    padding: 20px;
  }
}
</style>
