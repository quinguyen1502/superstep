/** UI language + the account's chat language (TASK-0022 follow-up): approval requests and verification codes sent
 *  to Slack/Telegram use the language the user works in, stored as `lang` in the notification preferences. */
import i18n from '@/lib/i18n'
import { api, signedIn } from '@/lib/api'
import { loadMe } from '@/lib/rbac'

const SYNCED = 'lgs_lang_synced'
// a read-only account (the demo visitor) keeps the language in this browser only: the server would refuse the save
// one save per language at a time: the sync after sign-in runs again when the switcher mounts twice (React StrictMode, a
// page with two switchers), and the second PUT is the same write (TASK-0209)
let saving: string | null = null
const save = (lang: string) => { if (!signedIn() || saving === lang) return; saving = lang
  loadMe().then(me => { if (!me.read_only) return api('/api/notifications/preferences', { method: 'PUT', json: { lang } }).then(() => sessionStorage.setItem(SYNCED, lang)) })
    .catch(() => {}).finally(() => { if (saving === lang) saving = null }) }

export function setLanguage(lang: string) { i18n.changeLanguage(lang); save(lang) }

/** Once per browser session after sign-in: tell the server which language this user sees. */
export function syncLanguage() { const l = i18n.resolvedLanguage; if (l && sessionStorage.getItem(SYNCED) !== l) save(l) }
