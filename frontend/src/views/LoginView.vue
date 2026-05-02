<template>
  <div>
    <h1>Login</h1>
    <form @submit.prevent="$router.push('/simulacion')">
      <input type="text" placeholder="Usuario" />
      <input type="password" placeholder="Contraseña" />
      <button type="submit">Entrar</button>
    </form>
  </div>
</template>
