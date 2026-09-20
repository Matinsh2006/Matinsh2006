/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './apps/**/*.py',
    './static/js/**/*.js',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Vazirmatn', 'system-ui', 'Segoe UI', 'Tahoma', 'sans-serif'],
      },
      colors: {
        brand: {
          50: '#fff1f3', 100: '#ffe4e8', 200: '#fecdd6', 300: '#fda4b6',
          400: '#fb7191', 500: '#f43f6e', 600: '#e11d54', 700: '#be1246',
          800: '#9f1240', 900: '#88133c',
        },
      },
    },
  },
  plugins: [],
};
