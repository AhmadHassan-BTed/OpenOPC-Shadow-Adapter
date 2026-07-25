/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'opc-bg': 'var(--opc-bg, #0c111b)',
        'opc-elevated': 'var(--opc-elevated, #141b2b)',
        'opc-secondary': 'var(--opc-secondary, #1a2332)',
        'opc-surface': 'var(--opc-surface, rgba(20, 27, 43, 0.75))',
        'opc-text': 'var(--opc-text, #e2e8f0)',
        'opc-text-secondary': 'var(--opc-text-secondary, #8494a7)',
        'opc-text-dim': 'var(--opc-text-dim, #64748b)',
        'opc-accent': 'var(--opc-accent, #14b8a6)',
        'opc-accent-hover': 'var(--opc-accent-hover, #0d9488)',
        'opc-accent-soft': 'var(--opc-accent-soft, rgba(20, 184, 166, 0.15))',
        'opc-indigo': '#6366f1',
        'opc-indigo-soft': 'rgba(99, 102, 241, 0.15)',
        'opc-border': 'var(--opc-border, rgba(148, 163, 184, 0.12))',
        'opc-border-hover': 'var(--opc-border-hover, rgba(148, 163, 184, 0.28))',
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
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'opc-glow': '0 0 20px -5px rgba(20, 184, 166, 0.25)',
        'opc-card': '0 4px 20px -2px rgba(0, 0, 0, 0.4)',
      },
    },
  },
  plugins: [],
};
