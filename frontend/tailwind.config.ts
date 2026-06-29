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
        bg: '#12100e',
        surface: '#1c1a16',
        elevated: '#252118',
        gold: {
          DEFAULT: '#d4a853',
          bright: '#e8c56a',
          dim: '#7a5e28',
        },
        mint: '#5ebd8a',
        cream: '#e8dcc8',
        mist: '#8a7d6a',
        fog: '#4a4236',
      },
      fontFamily: {
        display: ['var(--font-playfair)', 'Georgia', 'serif'],
        sans: ['var(--font-mulish)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-fira)', 'Courier New', 'monospace'],
      },
      animation: {
        'fade-up': 'fadeUp 0.65s cubic-bezier(0.16,1,0.3,1) both',
        'fade-in': 'fadeIn 0.5s ease-out both',
        'glow': 'glow 4s ease-in-out infinite',
        'slide-right': 'slideRight 0.8s cubic-bezier(0.16,1,0.3,1) both',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(18px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        fadeIn: {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        glow: {
          '0%, 100%': { opacity: '0.3' },
          '50%': { opacity: '0.6' },
        },
        slideRight: {
          from: { opacity: '0', transform: 'translateX(-20px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
      },
      boxShadow: {
        'gold': '0 0 30px rgba(212, 168, 83, 0.12)',
        'gold-sm': '0 0 12px rgba(212, 168, 83, 0.1)',
      },
    },
  },
  plugins: [],
}

export default config