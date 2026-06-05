import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // M8.10 terminal surfaces — near-black app, charcoal elevation ramp.
        // Separation comes from fill + space, not heavy borders.
        background: '#0a0c10', // app, darkest
        panel: '#11151c', // module surface (+1 elevation)
        panel2: '#171c25', // elevated / nested (+2)
        panel3: '#1e242f', // hover / active fill (+3)
        // borders are near-invisible hairlines; rarely the separator of record
        border: '#1b212b',
        borderStrong: '#2a323f',
        grid: '#161b22',
        // text ramp
        foreground: '#e6e9ef', // soft white, not pure
        mutedForeground: '#98a2b3', // secondary gray
        faint: '#5b6573', // faint gray
        // semantic — calm/institutional, not crypto-neon
        up: '#3fb950', // calm terminal green
        down: '#e5534b', // institutional red
        warn: '#d6a121', // muted warning gold
        accent: '#4c8dff', // Bloomberg-ish active blue, interactive/secondary
        teal: '#2bb6a3', // optional accent, sparing
        // brand — the gold compass star from the logo. Signature accent: active
        // nav, primary insight, focus. Used with intent, never decoration.
        gold: '#f5b73d',
        goldBright: '#ffd982',
        goldMuted: '#c4922b',
        // back-compat aliases (legacy /live components still reference these)
        card: '#11151c',
        cardForeground: '#e6e9ef',
        muted: '#171c25',
        accentForeground: '#e6e9ef',
      },
      fontFamily: {
        sans: ['var(--font-ui)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-mono)', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '0.95rem', letterSpacing: '0.01em' }],
      },
      letterSpacing: {
        label: '0.06em',
      },
      borderRadius: {
        // terminals: tight, consistent corners
        DEFAULT: '0.25rem',
        sm: '0.1875rem',
        md: '0.3125rem',
        lg: '0.4375rem',
        xl: '0.5625rem',
      },
      boxShadow: {
        // very subtle lift for the one primary module per screen
        panel: '0 1px 0 0 rgba(255,255,255,0.02) inset, 0 1px 2px 0 rgba(0,0,0,0.4)',
        elev: '0 2px 8px -2px rgba(0,0,0,0.5), 0 1px 0 0 rgba(255,255,255,0.03) inset',
        // soft gold glow for the active/brand element — barely there
        gold: '0 0 0 1px rgba(245,183,61,0.20), 0 2px 12px -4px rgba(245,183,61,0.25)',
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        'fade-rise': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        shimmer: 'shimmer 1.4s infinite',
        'fade-rise': 'fade-rise 0.32s cubic-bezier(0.22, 1, 0.36, 1) both',
      },
    },
  },
  plugins: [],
}
export default config
