import { useSearchParams } from 'react-router-dom'
import { DirectPublicChatPage } from './public-chat-direct'
import { EmbeddedChatPage } from './embedded-chat'
export function PublicChatPage() {
  const [params] = useSearchParams()
  return params.get('embed') === '1' ? <EmbeddedChatPage widget={params.get('widget') === '1'} /> : <DirectPublicChatPage />
}
