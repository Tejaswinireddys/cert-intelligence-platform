import type { Metadata } from 'next';
import './globals.css';
import { AppProvider } from '@/components/AppContext';
import Sidebar from '@/components/Sidebar';
import Topbar from '@/components/Topbar';

export const metadata: Metadata = {
  title: 'Certificate Intelligence Platform — Operations',
  description:
    'Automated TLS certificate lifecycle management. Fleet health, expiry risk, renewal velocity and audit for an enterprise certificate-management system.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <div className="app-shell bg-soc">
            <Sidebar />
            <div className="flex min-w-0 flex-col overflow-hidden">
              <Topbar />
              <main className="scroll-area flex-1 px-5 py-6 lg:px-8">
                <div className="mx-auto w-full max-w-[1400px]">{children}</div>
              </main>
            </div>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}
