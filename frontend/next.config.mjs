/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy /api calls to the FastAPI backend (local or production cloud)
  async rewrites() {
    const rawBackendUrl =
      process.env.BACKEND_API_URL ||
      (process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.startsWith('http')
        ? process.env.NEXT_PUBLIC_API_URL
        : null) ||
      'http://127.0.0.1:8000/api';

    const cleanUrl = rawBackendUrl.replace(/\/+$/, '');
    const destination = cleanUrl.endsWith('/api')
      ? `${cleanUrl}/:path*`
      : `${cleanUrl}/api/:path*`;

    return [
      {
        source: '/api/:path*',
        destination,
      },
    ];
  },
};

export default nextConfig;
