/** @type {import('next').NextConfig} */
const nextConfig = {
  // Static export so the dashboard can be served as a static site (demo with mock data),
  // and also runs as a normal dev server via `next dev`.
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
  reactStrictMode: true,
  // Relative asset paths so the export works when served from an arbitrary
  // sub-path (e.g. behind the deploy proxy), not just from the domain root.
  assetPrefix: process.env.NEXT_PUBLIC_ASSET_PREFIX || undefined,
};

module.exports = nextConfig;
