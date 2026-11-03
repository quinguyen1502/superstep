// Compiled against the package declarations by the acceptance runner.
import { Rating, type ChatController } from '@superstep/react'
export function renderStoreRating(chat: ChatController) {
  const turn = chat.turns.at(-1)
  return turn ? <Rating turn={turn} /> : null
}
