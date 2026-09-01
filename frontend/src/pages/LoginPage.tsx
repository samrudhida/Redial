import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound, Mail } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import { AuthLayout } from '../landing/AuthLayout'

const loginSchema = z.object({
  email: z.string().trim().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean(),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginPage() {
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '', rememberMe: false },
  })

  function onSubmit() {
    // No authentication backend exists yet — this intentionally does not
    // fabricate a real session. It only unlocks the existing, already-open
    // /dashboard route, clearly framed as a demo rather than a real login.
    toast.success('Welcome back', { description: 'Entering the demo dashboard — no live authentication is connected yet.' })
    navigate('/dashboard')
  }

  function handleForgotPassword() {
    toast('Password recovery isn’t connected yet', { description: 'This will call a real endpoint once auth ships.' })
  }

  return (
    <AuthLayout title="Welcome back" description="Sign in to access the recovery operations console.">
      <form onSubmit={event => void handleSubmit(onSubmit)(event)} noValidate>
        <div className="form-field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} />
          {errors.email && <span className="form-error">{errors.email.message}</span>}
        </div>

        <div className="form-field">
          <label htmlFor="password">Password</label>
          <input id="password" type="password" autoComplete="current-password" placeholder="••••••••" {...register('password')} />
          {errors.password && <span className="form-error">{errors.password.message}</span>}
        </div>

        <div className="auth-row">
          <label className="auth-checkbox">
            <input type="checkbox" {...register('rememberMe')} />
            <span>Remember me</span>
          </label>
          <button type="button" className="auth-link-button" onClick={handleForgotPassword}>Forgot password?</button>
        </div>

        <button type="submit" className="primary-button auth-submit" disabled={isSubmitting}>
          {isSubmitting ? 'Signing in...' : 'Sign in'}
        </button>

        <div className="auth-divider"><span>or continue with</span></div>

        <div className="auth-social-row">
          <button type="button" className="secondary-button" disabled title="Social login isn't connected yet">
            <Mail size={15} /> Google
          </button>
          <button type="button" className="secondary-button" disabled title="Social login isn't connected yet">
            <KeyRound size={15} /> GitHub
          </button>
        </div>

        <p className="auth-switch">Don&apos;t have an account? <Link to="/signup">Sign up</Link></p>
      </form>
    </AuthLayout>
  )
}
