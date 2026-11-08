export type ChatLocale = 'en' | 'vi'

const copy = {
  en: {
    send: 'Send',
    message: 'Message',
    answer: 'Answer',
    answerLabel: 'Your answer',
    approve: 'Approve',
    reject: 'Reject',
    attach: 'Attach a file',
    remove: 'Remove',
    helpful: 'Helpful',
    notHelpful: 'Not helpful',
    waitingReviewer: 'Waiting for a reviewer',
    needsAnswer: 'This step needs an answer',
    you: 'You',
    assistant: 'Assistant',
    choose: 'Choose',
    stop: 'Stop',
    required: 'Required',
  },
  vi: {
    send: 'Gửi',
    message: 'Tin nhắn',
    answer: 'Trả lời',
    answerLabel: 'Câu trả lời của bạn',
    approve: 'Chấp nhận',
    reject: 'Từ chối',
    attach: 'Đính kèm tệp',
    remove: 'Gỡ',
    helpful: 'Hữu ích',
    notHelpful: 'Không hữu ích',
    waitingReviewer: 'Đang chờ người duyệt',
    needsAnswer: 'Bước này cần câu trả lời',
    you: 'Bạn',
    assistant: 'Trợ lý',
    choose: 'Chọn',
    stop: 'Dừng',
    required: 'Bắt buộc',
  },
} as const

export type LabelKey = keyof typeof copy.en

export function text(locale: ChatLocale | undefined, key: LabelKey): string {
  return copy[locale === 'vi' ? 'vi' : 'en'][key]
}
