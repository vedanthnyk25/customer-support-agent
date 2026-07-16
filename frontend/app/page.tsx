import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-black text-white overflow-hidden">
      {/* Navigation */}
      <nav className="border-b-2 border-white px-6 py-4 md:px-12 md:py-6 flex items-center justify-between">
        <div className="text-2xl md:text-3xl font-black tracking-tighter">
          SUPPORT.AI
        </div>
        <Link
          href="/chat"
          className="border-2 border-white px-6 py-2 font-bold hover:bg-white hover:text-black transition-colors"
        >
          TRY NOW
        </Link>
      </nav>

      {/* Hero Section */}
      <div className="border-b-2 border-white px-6 py-16 md:px-12 md:py-24 lg:py-32">
        <div className="max-w-6xl">
          {/* Main Headline */}
          <div className="mb-12 md:mb-16">
            <h1 className="text-5xl md:text-7xl lg:text-8xl font-black leading-[1.1] tracking-tighter mb-6">
              AI CUSTOMER <span style={{ color: 'var(--accent-primary)' }}>SUPPORT</span>
            </h1>
            <h2 className="text-3xl md:text-4xl font-bold text-gray-400 mb-8">
              That actually works
            </h2>
            <p className="text-lg md:text-xl text-gray-300 max-w-2xl leading-relaxed mb-8">
              Intelligent support agent that understands your products, policies, and customers. No hallucinations. No templates. Just honest AI.
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 mb-16">
            <Link
              href="/chat"
              className="border-3 border-white bg-white text-black px-8 py-4 font-black text-lg hover:bg-black hover:text-white transition-colors"
            >
              START CHAT →
            </Link>
            <button className="border-3 border-white text-white px-8 py-4 font-black text-lg hover:bg-white hover:text-black transition-colors">
              VIEW FEATURES
            </button>
          </div>

          {/* Badge */}
          <div className="inline-block border-2 border-white px-4 py-2 font-mono text-sm">
            <span style={{ color: 'var(--accent-green)' }}>●</span> LIVE DEMO AVAILABLE
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="px-6 py-16 md:px-12 md:py-24">
        <div className="max-w-6xl">
          <h3 className="text-3xl md:text-4xl font-black mb-12 tracking-tight">FEATURES</h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            {/* Feature 1 */}
            <div className="border-3 border-white p-8 bg-black">
              <div className="flex items-start gap-4 mb-4">
                <div
                  className="w-4 h-4 mt-1 flex-shrink-0"
                  style={{ backgroundColor: 'var(--accent-yellow)' }}
                ></div>
                <h4 className="text-2xl font-black">Order Lookup</h4>
              </div>
              <p className="text-gray-300 font-medium">
                Real-time order tracking. Integrates with your systems to provide accurate, instant responses.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="border-3 border-white p-8 bg-black">
              <div className="flex items-start gap-4 mb-4">
                <div
                  className="w-4 h-4 mt-1 flex-shrink-0"
                  style={{ backgroundColor: 'var(--accent-secondary)' }}
                ></div>
                <h4 className="text-2xl font-black">Product Info</h4>
              </div>
              <p className="text-gray-300 font-medium">
                Comprehensive product knowledge. From specs to recommendations, your AI knows your catalog.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="border-3 border-white p-8 bg-black">
              <div className="flex items-start gap-4 mb-4">
                <div
                  className="w-4 h-4 mt-1 flex-shrink-0"
                  style={{ backgroundColor: 'var(--accent-primary)' }}
                ></div>
                <h4 className="text-2xl font-black">Policy Engine</h4>
              </div>
              <p className="text-gray-300 font-medium">
                Knows your return, refund, and shipping policies. Always enforces the right rules.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="border-3 border-white p-8 bg-black">
              <div className="flex items-start gap-4 mb-4">
                <div
                  className="w-4 h-4 mt-1 flex-shrink-0"
                  style={{ backgroundColor: 'var(--accent-green)' }}
                ></div>
                <h4 className="text-2xl font-black">Ticket Creation</h4>
              </div>
              <p className="text-gray-300 font-medium">
                Escalates complex issues to your support team. Works with your existing ticketing system.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Section */}
      <div className="border-t-2 border-white px-6 py-16 md:px-12 md:py-24">
        <div className="max-w-6xl grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="border-2 border-white p-6">
            <div className="text-4xl md:text-5xl font-black mb-2">99%</div>
            <p className="text-gray-400 font-bold">Uptime SLA</p>
          </div>
          <div className="border-2 border-white p-6">
            <div className="text-4xl md:text-5xl font-black mb-2">&lt;100ms</div>
            <p className="text-gray-400 font-bold">Response Time</p>
          </div>
          <div className="border-2 border-white p-6">
            <div className="text-4xl md:text-5xl font-black mb-2">24/7</div>
            <p className="text-gray-400 font-bold">Available</p>
          </div>
          <div className="border-2 border-white p-6">
            <div className="text-4xl md:text-5xl font-black mb-2">0</div>
            <p className="text-gray-400 font-bold">Hallucinations*</p>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-6 max-w-2xl">
          * Within your defined knowledge base. If something isn&apos;t in your system, we tell you.
        </p>
      </div>

      {/* CTA Section */}
      <div className="border-t-2 border-white px-6 py-16 md:px-12 md:py-24 bg-black">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl md:text-6xl font-black mb-8 tracking-tight">
            Ready to transform your support?
          </h2>
          <p className="text-lg text-gray-300 mb-12">
            Start with a free demo. No credit card required.
          </p>
          <Link
            href="/chat"
            className="inline-block border-3 border-white bg-white text-black px-10 py-5 font-black text-xl hover:bg-black hover:text-white hover:border-white transition-colors"
          >
            LAUNCH CHAT NOW
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t-2 border-white px-6 py-8 md:px-12 md:py-12">
        <div className="max-w-6xl flex flex-col md:flex-row justify-between items-center gap-6">
          <p className="text-gray-500 font-mono text-sm">© 2024 SUPPORT.AI. Built with no apologies.</p>
          <div className="flex gap-6 font-bold">
            <a href="#" className="hover:text-white transition-colors">
              DOCS
            </a>
            <a href="#" className="hover:text-white transition-colors">
              PRICING
            </a>
            <a href="#" className="hover:text-white transition-colors">
              CONTACT
            </a>
          </div>
        </div>
      </footer>
    </div>
  )
}
