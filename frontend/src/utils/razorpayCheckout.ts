/**
 * Loads Razorpay's hosted Checkout script on demand — no npm package exists
 * for this (Razorpay ships it as a plain <script> tag), and pulling it in
 * only when a real order exists keeps it out of the initial bundle.
 */

const CHECKOUT_SRC = 'https://checkout.razorpay.com/v1/checkout.js'

interface RazorpayCheckoutOptions {
  key: string
  amount: number
  currency: string
  order_id: string
  name: string
  description?: string
  prefill?: { name?: string; email?: string; contact?: string }
  theme?: { color?: string }
  handler?: (response: { razorpay_payment_id: string; razorpay_order_id: string; razorpay_signature: string }) => void
  modal?: { ondismiss?: () => void }
}

interface RazorpayCheckoutInstance {
  open: () => void
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => RazorpayCheckoutInstance
  }
}

let loadPromise: Promise<void> | null = null

function loadCheckoutScript(): Promise<void> {
  if (window.Razorpay) return Promise.resolve()
  if (loadPromise) return loadPromise

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script')
    script.src = CHECKOUT_SRC
    script.onload = () => resolve()
    script.onerror = () => reject(new Error('Failed to load Razorpay Checkout — check your network connection.'))
    document.body.appendChild(script)
  })
  return loadPromise
}

/** Opens real Razorpay Test/Live Mode Checkout for one order. Never finalizes payment state itself — the webhook does that. */
export async function openRazorpayCheckout(options: RazorpayCheckoutOptions): Promise<void> {
  await loadCheckoutScript()
  if (!window.Razorpay) throw new Error('Razorpay Checkout did not load correctly.')
  new window.Razorpay(options).open()
}
