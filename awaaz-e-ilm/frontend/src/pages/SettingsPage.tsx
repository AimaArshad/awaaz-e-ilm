/**
 * SettingsPage — user preferences.
 *
 * Settings
 * --------
 * - Preferred language (English / Urdu)
 * - TTS voice / engine selection
 * - Playback speed
 * - Whisper model size (affects accuracy vs. speed)
 * - High-contrast mode toggle
 *
 * Settings are persisted to localStorage (API persistence in Milestone 5).
 */
import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

interface UserSettings {
  language: 'en' | 'ur'
  speed: number
  whisperModel: 'tiny' | 'base' | 'small' | 'medium' | 'large'
  ttsEnEngine: 'kokoro' | 'piper'
  ttsUrEngine: 'mms' | 'edge_tts'
  highContrast: boolean
}

const DEFAULT_SETTINGS: UserSettings = {
  language: 'en',
  speed: 1.0,
  whisperModel: 'small',
  ttsEnEngine: 'kokoro',
  ttsUrEngine: 'mms',
  highContrast: false,
}

const STORAGE_KEY = 'awaaz-settings'

export default function SettingsPage() {
  const [settings, setSettings] = useState<UserSettings>(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      return stored ? { ...DEFAULT_SETTINGS, ...JSON.parse(stored) } : DEFAULT_SETTINGS
    } catch {
      return DEFAULT_SETTINGS
    }
  })
  const [saved, setSaved] = useState(false)

  const update = <K extends keyof UserSettings>(key: K, value: UserSettings[K]) => {
    setSettings(prev => ({ ...prev, [key]: value }))
    setSaved(false)
  }

  const save = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings))
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <main id="main" className="max-w-2xl mx-auto px-4 py-10">
      <h1 className="text-3xl font-bold text-white mb-8">⚙️ Settings</h1>

      <form
        onSubmit={(e) => { e.preventDefault(); save() }}
        aria-label="User preferences"
        className="space-y-6"
      >
        {/* Language */}
        <fieldset className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <legend className="text-sm font-semibold text-gray-300 mb-3">Language</legend>
          <div className="flex gap-4">
            {(['en', 'ur'] as const).map((lang) => (
              <label key={lang} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="language"
                  value={lang}
                  checked={settings.language === lang}
                  onChange={() => update('language', lang)}
                  className="accent-violet-500 w-4 h-4"
                />
                <span className="text-white">{lang === 'en' ? 'English' : 'اردو (Urdu)'}</span>
              </label>
            ))}
          </div>
        </fieldset>

        {/* Playback speed */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <label htmlFor="speed" className="block text-sm font-semibold text-gray-300 mb-3">
            Playback Speed: <span className="text-violet-400 font-bold">{settings.speed.toFixed(1)}×</span>
          </label>
          <input
            id="speed"
            type="range"
            min="0.5"
            max="3.0"
            step="0.1"
            value={settings.speed}
            onChange={(e) => update('speed', parseFloat(e.target.value))}
            className="w-full accent-violet-500"
            aria-valuemin={0.5}
            aria-valuemax={3.0}
            aria-valuenow={settings.speed}
            aria-valuetext={`${settings.speed.toFixed(1)} times`}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.5×</span><span>1.0×</span><span>2.0×</span><span>3.0×</span>
          </div>
        </div>

        {/* Whisper model */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <label htmlFor="whisper-model" className="block text-sm font-semibold text-gray-300 mb-2">
            Whisper Model Size
          </label>
          <select
            id="whisper-model"
            value={settings.whisperModel}
            onChange={(e) => update('whisperModel', e.target.value as UserSettings['whisperModel'])}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-400"
          >
            <option value="tiny">Tiny — fastest, lowest accuracy</option>
            <option value="base">Base — fast, decent accuracy</option>
            <option value="small">Small — balanced (recommended)</option>
            <option value="medium">Medium — accurate, slower</option>
            <option value="large">Large — most accurate, requires GPU</option>
          </select>
        </div>

        {/* TTS engines */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700">
          <p className="text-sm font-semibold text-gray-300 mb-3">TTS Engines</p>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label htmlFor="tts-en" className="block text-xs text-gray-400 mb-1">English</label>
              <select
                id="tts-en"
                value={settings.ttsEnEngine}
                onChange={(e) => update('ttsEnEngine', e.target.value as UserSettings['ttsEnEngine'])}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-400"
              >
                <option value="kokoro">Kokoro (default)</option>
                <option value="piper">Piper</option>
              </select>
            </div>
            <div>
              <label htmlFor="tts-ur" className="block text-xs text-gray-400 mb-1">Urdu</label>
              <select
                id="tts-ur"
                value={settings.ttsUrEngine}
                onChange={(e) => update('ttsUrEngine', e.target.value as UserSettings['ttsUrEngine'])}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-violet-400"
              >
                <option value="mms">MMS Urdu (offline)</option>
                <option value="edge_tts">Edge TTS (online)</option>
              </select>
            </div>
          </div>
        </div>

        {/* High contrast toggle */}
        <div className="bg-gray-800 rounded-xl p-5 border border-gray-700 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-gray-300">High Contrast Mode</p>
            <p className="text-xs text-gray-500 mt-0.5">Increases visual contrast for low-vision users</p>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={settings.highContrast}
            onClick={() => update('highContrast', !settings.highContrast)}
            className={`relative w-12 h-6 rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-violet-400
              ${settings.highContrast ? 'bg-violet-600' : 'bg-gray-600'}`}
          >
            <span
              className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform
                ${settings.highContrast ? 'translate-x-7' : 'translate-x-1'}`}
            />
          </button>
        </div>

        {/* Save button */}
        <button
          type="submit"
          className="w-full py-3 bg-violet-700 hover:bg-violet-600 text-white font-semibold rounded-xl transition-colors focus:outline-none focus:ring-2 focus:ring-violet-400"
        >
          {saved ? '✅ Saved!' : 'Save Settings'}
        </button>
      </form>

      <p className="mt-6 text-center">
        <Link to="/" className="text-gray-400 hover:text-white underline">← Back to Library</Link>
      </p>
    </main>
  )
}
