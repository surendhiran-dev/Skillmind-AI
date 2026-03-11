/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#00d4ff",
        accent: "#00ffd4",
        "glass-border": "rgba(255, 255, 255, 0.08)",
      },
      backgroundImage: {
        glass: "rgba(255, 255, 255, 0.03)",
      },
    },
  },
  plugins: [],
}
