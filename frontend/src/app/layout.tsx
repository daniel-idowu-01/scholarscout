import type { Metadata } from 'next'
import { Playfair_Display, Mulish, Fira_Code } from 'next/font/google'
import './globals.css'
import Navbar from '@/components/Navbar'
import Footer from '@/components/Footer'
import { AuthProvider } from '@/lib/auth-context'

const playfair = Playfair_Display({
  subsets: ['latin'],
  variable: '--font-playfair',
  display: 'swap',
  weight: ['400', '600', '700'],
  style: ['normal', 'italic'],
})

const mulish = Mulish({
  subsets: ['latin'],
  variable: '--font-mulish',
  display: 'swap',
  weight: ['300', '400', '500', '600', '700'],
})

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-fira',
  display: 'swap',
  weight: ['400', '500'],
})

export const metadata: Metadata = {
  title: 'ScholarScout — Graduate Opportunity Intelligence',
  description:
    'Discover scholarships, funded PhDs, fellowships and assistantships from top universities worldwide. Continuously updated, AI-powered.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${playfair.variable} ${mulish.variable} ${firaCode.variable}`}>
      <body className="font-sans bg-bg text-cream min-h-screen flex flex-col">
        <AuthProvider>
          <Navbar />
          <div className="flex-1">{children}</div>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  )
}