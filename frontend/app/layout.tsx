import type { Metadata } from "next";
import { Inter, Fraunces } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  axes: ["opsz"],   // optical size axis for display-sized use
});

export const metadata: Metadata = {
  title: "CineVault — AI-Powered Cinema Discovery",
  description: "Discover movies and TV shows through AI-powered recommendations tailored to your taste.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${inter.variable} ${fraunces.variable} font-sans bg-bg-base text-text-primary antialiased`}
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}
