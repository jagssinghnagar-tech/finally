/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d1117', panel: '#131a24', raised: '#1a2332', line: '#252f3d',
        ink: '#d5dde8', dim: '#7d8b9d', accent: '#ecad0a', blue: '#209dd7',
        purple: '#753991', up: '#2ecc71', down: '#f0483e',
      },
      fontFamily: {
        mono: ['"IBM Plex Mono"', '"Cascadia Mono"', 'Consolas', 'ui-monospace', 'monospace'],
        sans: ['"IBM Plex Sans"', '"Segoe UI"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
