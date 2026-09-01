import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Voxera — Hotel Conversation Intelligence",
  description:
    "Analyze hotel guest conversations: upload an audio URL, get a transcript and structured analysis.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className="h-full antialiased">{children}</body>
    </html>
  );
}
