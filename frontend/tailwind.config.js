/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EEF2FF',
          100: '#E0E7FF',
          500: '#4F46E5',
          600: '#4F46E5',
          700: '#4338CA',
        },
        canvas: '#F8FAFC',
        surface: '#FFFFFF',
        elevated: '#F1F5F9',
        ink: {
          DEFAULT: '#0F172A',
          muted: '#64748B',
          faint: '#94A3B8',
        },
        line: '#E2E8F0',
        accent: {
          DEFAULT: '#4F46E5',
          hover: '#4338CA',
          soft: '#EEF2FF',
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
        sm: '8px',
        DEFAULT: '12px',
        md: '12px',
        lg: '16px',
        xl: '16px',
        '2xl': '20px',
        full: '9999px',
      },
      boxShadow: {
        panel: '0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 12px rgba(15, 23, 42, 0.03)',
        elevated: '0 4px 16px rgba(15, 23, 42, 0.08)',
        composer: '0 8px 24px rgba(15, 23, 42, 0.06), 0 0 0 1px rgba(226, 232, 240, 0.8)',
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
