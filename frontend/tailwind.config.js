/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        strava: {
          orange: '#FC4C02',
          dark: '#222222',
          gray: '#F5F5F5',
        },
      },
    },
  },
  plugins: [],
}
