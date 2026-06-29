import Link from 'next/link'
import './globals.css'

export default function NotFound() {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0a0a0f] text-white antialiased">
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-9xl font-bold text-emerald-500">404</h1>
            <p className="text-2xl font-semibold mt-4">Page Not Found</p>
            <p className="text-gray-400 mt-2 mb-8">
              The page you're looking for doesn't exist.
            </p>
            <div className="flex gap-4 justify-center">
              <Link
                href="/"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-emerald-500 text-white font-semibold hover:bg-emerald-600 transition-colors"
              >
                Go Home
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-gray-800 hover:bg-gray-700 transition-colors"
              >
                Dashboard
              </Link>
            </div>
          </div>
        </div>
      </body>
    </html>
  )
}

