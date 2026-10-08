import { access, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const value = process.env.NETLIFY_API_ORIGIN?.trim();
const instructions = 'Set NETLIFY_API_ORIGIN to your hosted HTTPS backend origin, for example https://nellai-api.onrender.com (without /api/v1). See docs/netlify.md.';

try {
  if (!value || /\s/.test(value)) throw new Error(instructions);
  let origin;
  try {
    origin = new URL(value);
  } catch {
    throw new Error(instructions);
  }
  if (origin.protocol !== 'https:' || origin.username || origin.password ||
      origin.pathname !== '/' || origin.search || origin.hash ||
      origin.hostname === 'localhost' || origin.hostname.endsWith('.localhost') ||
      origin.hostname === '[::1]' || /^127\./.test(origin.hostname)) {
    throw new Error(instructions);
  }
  const dist = new URL('../web/dist/', import.meta.url);
  await access(new URL('index.html', dist));
  await writeFile(new URL('_redirects', dist), [
    `/api/* ${origin.origin}/api/:splat 200!`,
    `/health ${origin.origin}/health 200!`,
    '',
  ].join('\n'));
  console.log(`Netlify API proxy configured in ${fileURLToPath(new URL('_redirects', dist))}`);
} catch (error) {
  console.error(`Netlify configuration failed: ${error.message}`);
  process.exitCode = 1;
}
