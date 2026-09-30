/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#080d19",
        ink: "#f8fafc",
        accent: "#6366f1",
        accentSoft: "#1e293b",
        panel: "#111827",
        warning: "#f59e0b",
        danger: "#dc2626",
      },
      fontFamily: {
        heading: ["'Manrope'", "sans-serif"],
        body: ["'DM Sans'", "sans-serif"],
      },
      boxShadow: {
        lift: "0 20px 60px -35px rgba(0, 0, 0, 0.8)",
      },
      backgroundImage: {
        haze: "radial-gradient(circle at 10% 0%, rgba(79,70,229,.16), transparent 30%), radial-gradient(circle at 92% 8%, rgba(6,182,212,.11), transparent 27%)",
      },
    },
  },
  plugins: [],
};
