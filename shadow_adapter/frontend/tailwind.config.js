/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'opc-bg': '#0c111b',
        'opc-elevated': '#141b2b',
        'opc-secondary': '#1a2332',
        'opc-surface': 'rgba(20, 27, 43, 0.7)',
        'opc-text': '#e2e8f0',
        'opc-text-secondary': '#8494a7',
        'opc-text-dim': '#64748b',
        'opc-accent': '#6366f1',
        'opc-accent-hover': '#4f46e5',
        'opc-accent-soft': 'rgba(99, 102, 241, 0.15)',
        'opc-border': 'rgba(148, 163, 184, 0.12)',
        'opc-border-hover': 'rgba(148, 163, 184, 0.25)',
        'opc-green': '#34d399',
        'opc-yellow': '#fbbf24',
        'opc-red': '#f87171',
        'opc-blue': '#60a5fa',
      },
      borderRadius: {
        'opc': '12px',
        'opc-sm': '8px',
        'opc-xs': '6px',
      },
      fontFamily: {
        sans: ['Inter', 'SF Pro Display', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
