/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        background: '#131313',
        surface: '#1E1E1E',
        primary: '#00bfff', // Bleu bouton start
        accent: '#f2ff00', // Jaune Espagnol
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'sans-serif'],
      }
    }
  },
  plugins: [],
}


