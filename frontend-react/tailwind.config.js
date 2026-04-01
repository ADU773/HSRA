import forms from '@tailwindcss/forms';
import containerQueries from '@tailwindcss/container-queries';

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
          "inverse-primary": "#8debff",
          "on-background": "#2c3437",
          "surface-container": "#eaeff2",
          "surface-container-lowest": "#ffffff",
          "surface": "#f7f9fb",
          "on-secondary": "#f7f9ff",
          "tertiary-fixed": "#a9cdef",
          "on-primary-fixed-variant": "#00616f",
          "inverse-on-surface": "#9a9d9f",
          "on-secondary-fixed": "#314055",
          "surface-container-high": "#e3e9ed",
          "error-container": "#fa746f",
          "surface-tint": "#006978",
          "on-secondary-container": "#435368",
          "error-dim": "#67040d",
          "on-tertiary-fixed": "#03314c",
          "error": "#a83836",
          "on-primary-container": "#005763",
          "secondary-fixed-dim": "#c5d6f0",
          "secondary": "#506076",
          "on-error-container": "#6e0a12",
          "on-error": "#fff7f6",
          "outline": "#747c80",
          "primary-container": "#8debff",
          "surface-container-low": "#f0f4f7",
          "primary-fixed-dim": "#7fdcf0",
          "on-tertiary-fixed-variant": "#294e6a",
          "secondary-dim": "#44546a",
          "secondary-fixed": "#d3e4fe",
          "tertiary-dim": "#325673",
          "on-primary": "#eefbff",
          "tertiary-container": "#a9cdef",
          "primary-fixed": "#8debff",
          "on-surface-variant": "#596064",
          "on-secondary-fixed-variant": "#4d5d73",
          "primary-dim": "#005c69",
          "inverse-surface": "#0b0f10",
          "outline-variant": "#acb3b7",
          "on-tertiary": "#f6f9ff",
          "surface-dim": "#d4dbdf",
          "background": "#f7f9fb",
          "on-surface": "#2c3437",
          "secondary-container": "#d3e4fe",
          "on-tertiary-container": "#1f4561",
          "surface-bright": "#f7f9fb",
          "surface-variant": "#dce4e8",
          "tertiary": "#3f637f",
          "on-primary-fixed": "#00424c",
          "surface-container-highest": "#dce4e8",
          "tertiary-fixed-dim": "#9bc0e0",
          "primary": "#006978"
      },
      fontFamily: {
          "headline": ["Manrope", "sans-serif"],
          "body": ["Inter", "sans-serif"],
          "label": ["Inter", "sans-serif"]
      },
      borderRadius: { "DEFAULT": "0.125rem", "lg": "0.25rem", "xl": "0.5rem", "full": "0.75rem" },
    },
  },
  plugins: [
    forms,
    containerQueries
  ],
}
