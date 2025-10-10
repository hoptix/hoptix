import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/components/providers'
import { GlobalLayout } from '@/components/global-layout'

export const metadata: Metadata = {
  title: 'Analytics Dashboard',
  description: 'Analytics Dashboard Application',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <Providers>
          <GlobalLayout>
            {children}
          </GlobalLayout>
        </Providers>
      </body>
    </html>
  )
}
