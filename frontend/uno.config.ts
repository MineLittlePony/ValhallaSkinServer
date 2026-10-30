import { defineConfig, presetIcons, presetTypography, presetWebFonts, transformerDirectives } from 'unocss'
import { presetWind3 } from 'unocss/preset-wind3'

export default defineConfig({
  presets: [
    presetWind3({
      dark: 'media',
    }),
    presetIcons({
    }),
    presetTypography(),
    presetWebFonts({
      fonts: {
        mono: 'Roboto',
      },
    }),
  ],
  transformers: [
    transformerDirectives(),
  ],
})
