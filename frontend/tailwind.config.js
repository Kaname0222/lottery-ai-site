/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#2563eb',
        danger: '#dc2626',
        success: '#16a34a',
        warning: '#d97706',
      },
    },
  },
  plugins: [],
}
