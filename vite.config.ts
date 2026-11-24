import fs from 'node:fs';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const certFile = env.SSL_CRT_FILE || env.SSL_CERT_FILE;
  const keyFile = env.SSL_KEY_FILE;

  const https =
    certFile && keyFile && fs.existsSync(certFile) && fs.existsSync(keyFile)
      ? {
          cert: fs.readFileSync(certFile),
          key: fs.readFileSync(keyFile),
        }
      : undefined;

  const host = env.HOST || (https ? '0.0.0.0' : undefined);

  return {
    plugins: [react()],
    server: {
      host,
      https,
    },
    preview: {
      host,
      https,
    },
  };
});
