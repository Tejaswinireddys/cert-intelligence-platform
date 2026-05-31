import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0a1622',
          850: '#0d1b2a',
          800: '#0f1c2e',
          750: '#13243a',
          700: '#16294180',
          card: '#101f33',
          border: '#1e3050',
        },
        teal: {
          accent: '#2dd4bf',
          deep: '#14a098',
        },
        cyan: {
          accent: '#22d3ee',
        },
        tier: {
          p1: '#ef4444',
          p2: '#f59e0b',
          p3: '#22c55e',
          ok: '#64748b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(0,0,0,0.3), 0 8px 24px -12px rgba(0,0,0,0.5)',
        glow: '0 0 0 1px rgba(45,212,191,0.18), 0 8px 32px -8px rgba(45,212,191,0.18)',
      },
      backgroundImage: {
        'grid-faint':
          'linear-gradient(rgba(45,212,191,0.04) 1px, transparent 1px), linear-gradient(90deg, rgba(45,212,191,0.04) 1px, transparent 1px)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};

export default config;
