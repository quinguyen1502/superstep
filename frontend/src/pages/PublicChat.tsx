import { useParams, useSearchParams } from 'react-router-dom'
import { DirectPublicChatPage } from './public-chat-direct'
import { EmbeddedChatPage } from './embedded-chat'
export function PublicChatPage() {
  const [params] = useSearchParams()
  const { slug } = useParams()
  return params.get('embed') === '1' ? <EmbeddedChatPage key={slug} widget={params.get('widget') === '1'} /> : <DirectPublicChatPage key={slug} />
}
