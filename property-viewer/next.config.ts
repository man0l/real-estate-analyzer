import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    domains: [
      'imotstatic1.focus.bg',
      'imotstatic2.focus.bg',
      'imotstatic3.focus.bg',
      'imotstatic4.focus.bg',
      'imotstatic5.focus.bg',
      'cdn1.focus.bg',
      'cdn2.focus.bg',
      'cdn3.focus.bg',
      'cdn4.focus.bg',
      'cdn5.focus.bg',
      'mbqpxqpvjpimntzjthcc.supabase.co'  // Supabase Storage domain
    ],
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'mbqpxqpvjpimntzjthcc.supabase.co',
        pathname: '/storage/v1/object/public/properties/**',
      }
    ]
  },
};

export default nextConfig;
