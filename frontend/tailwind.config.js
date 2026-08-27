/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#1D4ED8',
          600: '#1D4ED8',
          700: '#1E40AF',
        },
        canvas: '#F1F5F9',
        surface: '#FFFFFF',
        elevated: '#F8FAFC',
        ink: {
          DEFAULT: '#0F172A',
          muted: '#64748B',
          faint: '#94A3B8',
        },
        line: '#E2E8F0',
        accent: {
          DEFAULT: '#1D4ED8',
          hover: '#1E40AF',
          soft: '#EFF6FF',
        },
        ok: '#15803D',
        warn: '#B45309',
        danger: '#B91C1C',
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          '"Noto Sans SC"',
          'system-ui',
          '-apple-system',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          'sans-serif',
        ],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      borderRadius: {
        sm: '6px',
        DEFAULT: '8px',
        md: '8px',
        lg: '8px',
        full: '9999px',
      },
      boxShadow: {
        panel: '0 1px 0 rgba(15, 23, 42, 0.06)',
        elevated: '0 1px 3px rgba(15, 23, 42, 0.08)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(6px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-up': 'fade-up 200ms ease-out both',
      },
    },
  },
  plugins: [],
};
