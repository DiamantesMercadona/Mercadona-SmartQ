import {getRandomFace} from "@/utils/getFace"

class Cliente {
  id = Date.now()
  imagen = getRandomFace()
  color = 0xffffff * Math.random()
}

export default Cliente
