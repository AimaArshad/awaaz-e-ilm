/**
 * earcons.ts — earcon (audio icon) playback utility.
 *
 * Earcons are short, non-speech audio cues that provide context-sensitive
 * feedback to visually impaired users. Examples:
 * - 'chapter_start' — played when a new chapter begins
 * - 'command_ok'    — played when a voice command is recognised
 * - 'command_fail'  — played when a command is not understood
 * - 'upload_done'   — played when document processing completes
 * - 'boundary'      — paragraph boundary tone
 *
 * Audio files are stored in /public/earcons/ and loaded lazily.
 * Falls back silently if the file is missing or playback fails.
 */

type EarconName = 'chapter_start' | 'command_ok' | 'command_fail' | 'upload_done' | 'boundary'

const _cache = new Map<EarconName, HTMLAudioElement>()

function _load(name: EarconName): HTMLAudioElement {
  if (_cache.has(name)) return _cache.get(name)!
  const audio = new Audio(`/earcons/${name}.mp3`)
  audio.preload = 'auto'
  _cache.set(name, audio)
  return audio
}

/**
 * Play an earcon sound.
 *
 * @param name    - Earcon identifier
 * @param volume  - Volume level 0.0–1.0 (default 0.7)
 */
export async function playEarcon(name: EarconName, volume = 0.7): Promise<void> {
  try {
    const audio = _load(name)
    audio.volume = volume
    audio.currentTime = 0
    await audio.play()
  } catch {
    // Silently ignore: file may not exist yet or autoplay may be blocked
  }
}

/** Preload all earcons so they play without latency. */
export function preloadEarcons(): void {
  const names: EarconName[] = ['chapter_start', 'command_ok', 'command_fail', 'upload_done', 'boundary']
  names.forEach(_load)
}
