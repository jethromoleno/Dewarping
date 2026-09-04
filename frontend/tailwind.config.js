/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0a0a0a',
          dark: '#111111',
          card: '#1a1a1a',
          elevated: '#222222',
          border: '#333333',
          hover: '#3a3a3a',
        },
        accent: {
          DEFAULT: '#dc2626',
          light: '#ef4444',
          dark: '#b91c1c',
          glow: 'rgba(220, 38, 38, 0.3)',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      animation: {
        'fade-in': 'fadeIn 0.4s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
        'pulse-glow': 'pulseGlow 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        pulseGlow: {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(220, 38, 38, 0)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(220, 38, 38, 0.15)' },
        },
      },
    },
  },
  plugins: [],
}
