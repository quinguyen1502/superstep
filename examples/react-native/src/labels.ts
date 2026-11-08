export type ExampleLocale = 'en' | 'vi'

const copy = {
  en: {
    title: 'Superstep chat',
    demo: 'Sample host only. Sign in as one of the two demo people.',
    loading: 'Loading the sample host',
    signIn: 'Sign in as',
    signOut: 'Sign out',
    english: 'English',
    vietnamese: 'Vietnamese',
    language: 'Language',
    missing: 'The sample host did not return a studio URL. Start it with CHAT_HOST_DEMO=1.',
    cookie: 'The sample host session cookie was not readable. Stay on http://localhost:5188.',
  },
  vi: {
    title: 'Chat Superstep',
    demo: 'Chỉ máy chủ mẫu. Đăng nhập bằng một trong hai người dùng thử.',
    loading: 'Đang tải máy chủ mẫu',
    signIn: 'Đăng nhập với',
    signOut: 'Đăng xuất',
    english: 'Tiếng Anh',
    vietnamese: 'Tiếng Việt',
    language: 'Ngôn ngữ',
    missing: 'Máy chủ mẫu không trả về URL studio. Hãy chạy với CHAT_HOST_DEMO=1.',
    cookie: 'Không đọc được cookie phiên của máy chủ mẫu. Giữ nguyên http://localhost:5188.',
  },
} as const

export type ExampleKey = keyof typeof copy.en

export function line(locale: ExampleLocale, key: ExampleKey): string {
  return copy[locale][key]
}
