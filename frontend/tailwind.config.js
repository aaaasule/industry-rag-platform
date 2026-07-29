/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 工业场景多在车间强光或昏暗环境下使用，主色取饱和度偏低的蓝，
        // 避免长时间阅读疲劳
        brand: {
          50: '#eef4ff',
          100: '#d9e5ff',
          500: '#3b6bd4',
          600: '#2f56ad',
          700: '#264488',
        },
      },
      fontFamily: {
        sans: ['system-ui', '-apple-system', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
