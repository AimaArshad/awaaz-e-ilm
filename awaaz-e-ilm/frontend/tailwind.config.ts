import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // High-contrast accessibility palette
        hc: {
          bg: '#0a0a0a',         // near-black background
          surface: '#1a1a2e',    // card/panel background
          border: '#2d2d4a',     // subtle borders
          text: '#f0f0f0',       // primary text (high contrast)
          muted: '#a0a0b0',      // secondary text
          accent: '#7c3aed',     // violet accent (focus rings, active states)
          'accent-hover': '#6d28d9',
          success: '#22c55e',    // green for ready states
          warning: '#f59e0b',    // amber for processing
          danger: '#ef4444',     // red for errors
          info: '#38bdf8',       // sky blue for info
        },
      },
      fontFamily: {
        // Urdu-compatible font stack
        urdu: ['Noto Nastaliq Urdu', 'Jameel Noori Nastaleeq', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        pulse: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
      ringWidth: {
        3: '3px',
      },
    },
  },
  plugins: [],
} satisfies Config
