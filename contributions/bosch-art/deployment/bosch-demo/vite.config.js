import { defineConfig } from 'vite';
export default defineConfig({
  base: './',
  define: { 'import.meta.env.VITE_STATIC': JSON.stringify('1'), 'import.meta.env.VITE_DEFAULT_SCENE': JSON.stringify('bosch-demo') },
  build: { target: 'es2022' },
});
