import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import alpinejs from '@astrojs/alpinejs';

// https://astro.build/config
export default defineConfig({
  integrations: [
    tailwind({
      applyBaseStyles: false,
    }),
    alpinejs({
      entrypoint: '/src/entrypoint'
    })
  ],
  server: {
    host: '0.0.0.0',
    port: 9321
  },
  vite: {
    server: {
      allowedHosts: ['mcp-vultr.l.supported.systems', 'localhost'],
      proxy: {
        '/api': {
          target: 'http://localhost:8001',
          changeOrigin: true,
          secure: false
        }
      }
    }
  },
  build: {
    assets: 'assets'
  },
  output: 'server',
  site: 'https://mcp-vultr.l.supported.systems',
  compressHTML: true,
  experimental: {
    contentCollectionCache: true
  },
  prefetch: true
});