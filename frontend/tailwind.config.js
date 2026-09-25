/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bccl: {
          dark: '#0B0F17',
          surface: '#131B2A',
          card: '#1A2438',
          border: '#24324D',
          gold: '#D97706',
          amber: '#F59E0B',
          accent: '#3B82F6',
          text: '#F1F5F9',
          muted: '#94A3B8'
        }
      }
    },
  },
  plugins: [],
}
