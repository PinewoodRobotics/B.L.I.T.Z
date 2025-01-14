import { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `http://localhost:5006/:path*`, // Forward as expected
      },
    ];
  },
};

export default nextConfig;
