/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mota: {
          50: '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          500: '#0284c7',
          600: '#0369a1',
          700: '#075985',
          800: '#0c4a6e',
          900: '#1e3a8a',
          950: '#0f172a',
        },
        tiranga: {
          saffron: '#f97316',
          white: '#ffffff',
          green: '#15803d',
          navy: '#1e3a8a'
        }
      }
    },
  },
  plugins: [],
}
