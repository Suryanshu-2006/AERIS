/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        aeris: {
          bg: '#070b13',
          panel: '#0d131f',
          border: '#1a2436',
          card: '#111827',
          cyan: '#06b6d4',
          emerald: '#10b981',
          amber: '#f59e0b',
          crimson: '#ef4444',
          muted: '#64748b',
          text: '#e2e8f0',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Consolas', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
