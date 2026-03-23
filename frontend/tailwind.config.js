/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  safelist: [
    'bg-reds-red', 'text-reds-red', 'border-reds-red',
    'bg-reds-dark', 'text-reds-dark',
    'bg-reds-surface', 'text-white',
  ],
  theme: {
    extend: {
      colors: {
        'reds-red':    '#C6011F',
        'reds-red-light': '#e8284a',
        'reds-dark':   '#0f0f0f',
        'reds-surface':'#1a1a1a',
        'reds-cream':  '#f5e6d3',
        'reds-gold':   '#d4a843',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body:    ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
