import type { Metadata, Viewport } from "next";
import Link from "next/link";
import { Clapperboard } from "lucide-react";
import "./globals.css";

export const metadata: Metadata = {
  title: "ReelForge",
  description: "Convertí videos largos en clips verticales con IA",
  appleWebApp: { capable: true, title: "ReelForge", statusBarStyle: "black-translucent" },
};

export const viewport: Viewport = {
  themeColor: "#09090d",
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className="min-h-screen antialiased">
        <header className="sticky top-0 z-30 border-b border-white/10 bg-[#09090d]/80 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-[1400px] items-center px-4">
            <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-500">
                <Clapperboard className="h-4 w-4 text-white" />
              </span>
              ReelForge
            </Link>
          </div>
        </header>
        <div className="mx-auto max-w-[1400px] px-4 py-6">{children}</div>
      </body>
    </html>
  );
}
