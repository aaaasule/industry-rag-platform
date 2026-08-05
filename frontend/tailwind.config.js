/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 工业控制台：铁青强调色（映射既有 brand-*，避免双色并存）
        brand: {
          50: '#E4F0F2',
          100: '#C8E0E5',
          500: '#2F6F7E',
          600: '#2F6F7E',
          700: '#275A66',
        },
        canvas: '#F2F1ED',
        surface: '#FFFEFB',
        ink: {
          DEFAULT: '#1A1F24',
          muted: '#5C6570',
          faint: '#8A929A',
        },
        line: '#D5D8DC',
        ok: '#3D6B4F',
        warn: '#B8792A',
        danger: '#A33B2B',
      },
      fontFamily: {
        sans: [
          '"IBM Plex Sans"',
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
        sm: '4px',
        DEFAULT: '6px',
        md: '6px',
        lg: '6px',
      },
      boxShadow: {
        panel: '0 1px 0 rgba(26, 31, 36, 0.06)',
      },
      keyframes: {
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(4px)' },
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
