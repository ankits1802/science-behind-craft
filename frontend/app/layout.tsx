import type { Metadata, Viewport } from "next";

import { AdminViewProvider } from "@/components/AdminViewProvider";
import { AuthProvider } from "@/components/AuthProvider";
import { ThemeProvider } from "@/components/ThemeProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { PREFERENCES_BOOT_SCRIPT, THEME_COLOR } from "@/lib/preferences";
import { FirstScreenFaces } from "./FirstScreenFaces";
import { LATIN_FONT_VARIABLES } from "./latinFonts";
import { READING_SCRIPT_FONT_VARIABLES } from "./readingScriptFonts";
import { SCRIPT_FONT_VARIABLES } from "./scriptFonts";
import "./globals.css";
import "./component-views.css";

export const metadata: Metadata = {
  title: {
    default: "KalaVigyan",
    template: "%s · KalaVigyan"
  },
  description: "The science behind India's crafts: materials, process stages and the chemistry at every stage, every sentence cited."
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: THEME_COLOR.light },
    { media: "(prefers-color-scheme: dark)", color: THEME_COLOR.dark }
  ]
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html className={`${LATIN_FONT_VARIABLES} ${SCRIPT_FONT_VARIABLES} ${READING_SCRIPT_FONT_VARIABLES}`} lang="en" suppressHydrationWarning>
      <body className="font-sans">
        <FirstScreenFaces />
        <script dangerouslySetInnerHTML={{ __html: PREFERENCES_BOOT_SCRIPT }} />
        <AuthProvider>
          <ThemeProvider>
            <ToastProvider>
              <AdminViewProvider>{children}</AdminViewProvider>
            </ToastProvider>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
