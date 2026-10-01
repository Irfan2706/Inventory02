/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#f8fafc",
        ink: "#0f172a",
        accent: "#0d9488",
        accentSoft: "#f0fdf4",
        panel: "#ffffff",
        warning: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        heading: ["'Plus Jakarta Sans'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
      },
      boxShadow: {
        lift: "0 10px 30px -10px rgba(0, 0, 0, 0.08)",
      },
    },
  },
  plugins: [],
};
