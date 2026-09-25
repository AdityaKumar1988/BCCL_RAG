import React from 'react';
import './globals.css';
import Navbar from '../components/Navbar';

export const metadata = {
  title: 'BCCL Enterprise AI Knowledge Retrieval System',
  description: 'Grounded RAG Platform for Official BCCL Documents & CDA Rules',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-bccl-dark min-h-screen text-bccl-text flex flex-col antialiased">
        <Navbar />
        <main className="flex-1 flex overflow-hidden">{children}</main>
      </body>
    </html>
  );
}
