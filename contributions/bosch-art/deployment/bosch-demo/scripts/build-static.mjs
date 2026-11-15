// Portable production build: preserve the existing prototype's app code, with
// no dev-server APIs, certificate setup, local asset symlinks or model secrets.
process.env.VITE_STATIC = '1';
process.env.VITE_DEFAULT_SCENE = 'bosch-demo';
const { build } = await import('vite');
await build({
  configFile: false,
  base: './',
  publicDir: 'public',
  build: { target: 'es2022', outDir: 'dist', emptyOutDir: true },
});
