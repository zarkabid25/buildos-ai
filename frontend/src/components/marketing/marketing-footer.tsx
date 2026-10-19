import Link from "next/link";

export function MarketingFooter() {
  return (
    <footer className="border-t border-white/10 bg-slate-950 py-12 text-slate-400">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-2 gap-8 sm:grid-cols-4">
          <div className="col-span-2 sm:col-span-1">
            <p className="text-lg font-semibold text-white">BuildOS AI</p>
            <p className="mt-2 text-sm">Know what happened. Know what&apos;s happening. Know what&apos;s next.</p>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Product</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/features" className="hover:text-white">Features</Link></li>
              <li><Link href="/construction-erp" className="hover:text-white">Construction ERP</Link></li>
              <li><Link href="/supplier-network" className="hover:text-white">Supplier Network</Link></li>
              <li><Link href="/pricing" className="hover:text-white">Pricing</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Company</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/about" className="hover:text-white">About</Link></li>
              <li><Link href="/contact" className="hover:text-white">Contact</Link></li>
              <li><Link href="/become-a-supplier" className="hover:text-white">Become a supplier</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-white">Get started</p>
            <ul className="mt-3 space-y-2 text-sm">
              <li><Link href="/register" className="hover:text-white">Start free trial</Link></li>
              <li><Link href="/request-demo" className="hover:text-white">Request a demo</Link></li>
              <li><Link href="/login" className="hover:text-white">Sign in</Link></li>
            </ul>
          </div>
        </div>
        <div className="mt-10 border-t border-white/10 pt-6 text-xs">
          &copy; {new Date().getFullYear()} BuildOS AI. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
