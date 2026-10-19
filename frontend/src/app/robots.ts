import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://www.buildos.ai";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      { userAgent: "*", allow: "/", disallow: ["/dashboard", "/platform-admin", "/supplier-portal", "/settings", "/support"] },
    ],
    sitemap: `${BASE_URL}/sitemap.xml`,
  };
}
