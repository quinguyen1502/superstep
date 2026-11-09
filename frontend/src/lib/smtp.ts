/** SMTP credential settings, as stored on a credential (backend engine/providers.py `Smtp.clean_settings`). */
export type SmtpSettings = { host?: string; port?: number; security?: 'starttls' | 'ssl' | 'none'; username?: string; from_email?: string; from_name?: string }
export const SMTP_DEFAULTS: SmtpSettings = { host: '', port: 587, security: 'starttls', username: '', from_email: '', from_name: '' }
