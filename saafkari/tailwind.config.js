/** تنظیمات تیلویند برای سایت مغازه صافکاری (راست‌چین و فونت فارسی) */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./static/js/**/*.js",
    "./**/forms.py",
    "./**/models.py",
    "./**/views.py",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Vazirmatn", "Tahoma", "Iranian Sans", "system-ui", "sans-serif"],
      },
      colors: {
        brand: {
          50: "#fffbeb",
          100: "#fef3c7",
          300: "#fcd34d",
          500: "#f59e0b",
          600: "#d97706",
          700: "#b45309",
        },
      },
      boxShadow: {
        card: "0 10px 30px -12px rgb(15 23 42 / 0.18)",
      },
    },
  },
  plugins: [],
};
