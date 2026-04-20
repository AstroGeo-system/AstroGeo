import './globals.css'
import { AppShellProvider } from '@/components/providers/AppShellProvider'
import DashboardLayout from '@/components/dashboard/DashboardLayout'
import ChatWidget from '@/components/ChatWidget'
import PersonaShell from '@/components/providers/PersonaShell'

export const metadata = {
  title: 'AstroGeo — Space Intelligence',
  description: 'Futuristic aerospace intelligence dashboard UI',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className="relative min-h-screen overflow-x-hidden bg-astro-bg font-body text-slate-100 antialiased">
        <div className="stars-bg" aria-hidden />
        <div className="nebula-overlay" aria-hidden />
        <AppShellProvider>
          <PersonaShell>
            <div className="relative z-10">
              <DashboardLayout>{children}</DashboardLayout>
            </div>
          </PersonaShell>
        </AppShellProvider>
        {/* Floating AI chat widget — present on all pages */}
        <ChatWidget />
      </body>
    </html>
  )
}


