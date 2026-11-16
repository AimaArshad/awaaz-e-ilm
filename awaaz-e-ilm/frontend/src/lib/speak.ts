/**
 * speak.ts — SpeechSynthesis wrapper for spoken UI feedback.
 *
 * Used to announce UI events to users who may not use a screen reader
 * but benefit from audio cues (e.g., "Chapter 3 loaded", "Paused").
 *
 * Features:
 * - Language-aware (uses 'en-US' or 'ur-PK' voices when available)
 * - Cancels the previous utterance before speaking a new one
 * - Falls back gracefully if SpeechSynthesis is not available
 * - Respects the user's speech rate preference
 */

let _lang = 'en-US'
let _rate = 1.0

/** Configure the global speak settings. */
export function configureSpeech(lang: string, rate = 1.0) {
  _lang = lang === 'ur' ? 'ur-PK' : 'en-US'
  _rate = rate
}

/**
 * Speak a message using the Web Speech API.
 *
 * @param text     - Text to speak
 * @param priority - 'polite' (waits for current utterance) or 'assertive' (interrupts)
 */
export function speak(text: string, priority: 'polite' | 'assertive' = 'polite'): void {
  if (!('speechSynthesis' in window)) return

  if (priority === 'assertive') {
    window.speechSynthesis.cancel()
  }

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = _lang
  utterance.rate = _rate

  // Try to pick a voice that matches the language
  const voices = window.speechSynthesis.getVoices()
  const match = voices.find(v => v.lang.startsWith(_lang.split('-')[0]))
  if (match) utterance.voice = match

  window.speechSynthesis.speak(utterance)
}

/** Cancel any ongoing speech. */
export function cancelSpeech(): void {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}
