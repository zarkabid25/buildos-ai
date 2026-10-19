import type { MetadataRoute } from "next";

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? "https://www.buildos.ai";

export default function sitemap(): MetadataRoute.Sitemap {
  const routes = ["", "/features", "/construction-erp", "/supplier-network", "/pricing", "/about", "/contact", "/register", "/request-demo", "/become-a-supplier"];
  return routes.map((route) => ({
    url: `${BASE_URL}${route}`,
    lastModified: new Date(),
    changeFrequency: "weekly" as const,
    priority: route === "" ? 1 : 0.7,
  }));
}
