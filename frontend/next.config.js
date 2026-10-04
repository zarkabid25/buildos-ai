/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // The browser tests build into their own folder so they never share (and
  // corrupt) the .next folder a running `next dev` is using.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

module.exports = nextConfig;
