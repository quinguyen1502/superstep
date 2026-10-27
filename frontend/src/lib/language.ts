/** UI language + the account's chat language (TASK-0022 follow-up): approval requests and verification codes sent
 *  to Slack/Telegram use the language the user works in, stored as `lang` in the notification preferences. */
import i18n from '@/lib/i18n'
import { api, signedIn } from '@/lib/api'
import { loadMe } from '@/lib/rbac'

const SYNCED = 'lgs_lang_synced'
// a read-only account (the demo visitor) keeps the language in this browser only: the server would refuse the save
const save = (lang: string) => { if (signedIn()) loadMe().then(me => { if (!me.read_only) return api('/api/notifications/preferences', { method: 'PUT', json: { lang } }).then(() => sessionStorage.setItem(SYNCED, lang)) }).catch(() => {}) }

export function setLanguage(lang: string) { i18n.changeLanguage(lang); save(lang) }

/** Once per browser session after sign-in: tell the server which language this user sees. */
export function syncLanguage() { const l = i18n.resolvedLanguage; if (l && sessionStorage.getItem(SYNCED) !== l) save(l) }
