/**
 * useKeyboardShortcuts — global keyboard shortcut handler for the player.
 *
 * Shortcuts
 * ---------
 * K         → play/pause toggle
 * J         → back 30 seconds
 * L         → forward 30 seconds
 * N         → next chapter
 * P         → previous chapter (note: 'p' may conflict with browser "print"; handled carefully)
 * ?         → open help modal
 * Space     → push-to-talk (handled by VoiceButton separately)
 *
 * Skips events that originate from input/textarea/select/button elements
 * to avoid interfering with user typing.
 */
import { useEffect } from 'react'

interface ShortcutHandlers {
  onPlayPause?: () => void
  onSeekBack?: () => void
  onSeekForward?: () => void
  onNextChapter?: () => void
  onPrevChapter?: () => void
  onHelp?: () => void
}

function isInputTarget(e: KeyboardEvent): boolean {
  const tag = (e.target as HTMLElement)?.tagName?.toUpperCase()
  return ['INPUT', 'TEXTAREA', 'SELECT', 'BUTTON'].includes(tag)
}

export function useKeyboardShortcuts(handlers: ShortcutHandlers) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isInputTarget(e) || e.metaKey || e.ctrlKey || e.altKey) return

      switch (e.key.toLowerCase()) {
        case 'k':
          e.preventDefault()
          handlers.onPlayPause?.()
          break
        case 'j':
          e.preventDefault()
          handlers.onSeekBack?.()
          break
        case 'l':
          e.preventDefault()
          handlers.onSeekForward?.()
          break
        case 'n':
          e.preventDefault()
          handlers.onNextChapter?.()
          break
        case 'p':
          e.preventDefault()
          handlers.onPrevChapter?.()
          break
        case '?':
          e.preventDefault()
          handlers.onHelp?.()
          break
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [handlers])
}
