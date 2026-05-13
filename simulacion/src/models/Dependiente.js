import { getFacesRandomDependiente } from '../utils/imagesUtils.js'

class Dependiente {
  id = `${Date.now()}-${Math.floor(Math.random() * 1000000)}`
  imagen = getFacesRandomDependiente()
  color = 0xffffff * Math.random()
}

export default Dependiente
