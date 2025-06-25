/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  distDir: 'out',
  trailingSlash: true,
  images: { 
    unoptimized: true 
  },
  // GitHub Pagesのサブパス対応
  basePath: '/fan-platform-api',
  assetPrefix: '/fan-platform-api'
}

module.exports = nextConfig
