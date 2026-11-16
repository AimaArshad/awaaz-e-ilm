/**
 * useAnnouncer — ARIA live region announcer hook.
 *
 * Renders a visually hidden live region and exposes an `announce()` function.
 * The live region is announced to screen readers immediately (assertive) or
 * politely depending on the priority parameter.
 *
 * Usage:
 *   const { announce, AnnouncerRegion } = useAnnouncer()
 *   ...
 *   announce('Chapter 3 loaded')
 *   return <><AnnouncerRegion /><RestOfApp /></>
 */
import { useState, useCallback } from 'react'

type AnnouncePolicy = 'polite' | 'assertive'

export function useAnnouncer(defaultPolicy: AnnouncePolicy = 'polite') {
  const [politeMsg, setPoliteMsg] = useState('')
  const [assertiveMsg, setAssertiveMsg] = useState('')

  const announce = useCallback(
    (message: string, policy: AnnouncePolicy = defaultPolicy) => {
      if (policy === 'assertive') {
        setAssertiveMsg('')
        // Double-tick to force re-announcement of the same message
        setTimeout(() => setAssertiveMsg(message), 50)
      } else {
        setPoliteMsg('')
        setTimeout(() => setPoliteMsg(message), 50)
      }
    },
    [defaultPolicy],
  )

  function AnnouncerRegion() {
    return (
      <>
        <span
          aria-live="polite"
          aria-atomic="true"
          className="sr-only"
          data-testid="announcer-polite"
        >
          {politeMsg}
        </span>
        <span
          aria-live="assertive"
          aria-atomic="true"
          className="sr-only"
          data-testid="announcer-assertive"
        >
          {assertiveMsg}
        </span>
      </>
    )
  }

  return { announce, AnnouncerRegion }
}
