/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        festiva: {
          50: "#fdf8f6",
          100: "#f2e8e5",
          200: "#eaddd7",
          300: "#e0cec7",
          400: "#d2bab0",
          500: "#bfa094",
          600: "#a18073",
          700: "#846356",
          800: "#604439",
          900: "#432e26",
          gold: "#D4AF37",
          saffron: "#FF7722",
        },
      },
    },
  },
  plugins: [],
};
