export const metadata = {
  title: "News Intelligence India",
  description: "Bilingual Hindi-English news sentiment and framing platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, padding: "2rem", maxWidth: 640 }}>
        {children}
      </body>
    </html>
  );
}
