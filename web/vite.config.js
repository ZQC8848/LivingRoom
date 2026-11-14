import { defineConfig } from 'vite';
import basicSsl from '@vitejs/plugin-basic-ssl';

// WebXR needs a secure context. The Quest reaches this over LAN, so `npm run dev` serves
// HTTPS (self-signed) on all interfaces. `npm run dev:local` serves plain HTTP for desktop
// checks — localhost counts as a secure context without a certificate.
const plainHttp = process.env.LR_HTTP === '1';

export default defineConfig({
  plugins: plainHttp ? [] : [basicSsl()],
  server: { host: true, port: 5174, strictPort: true },
});
