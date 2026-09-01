import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound, Mail } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { z } from 'zod'
import { AuthLayout } from '../landing/AuthLayout'

const signupSchema = z
  .object({
    fullName: z.string().trim().min(1, 'Full name is required'),
    email: z.string().trim().min(1, 'Email is required').email('Enter a valid email address'),
    password: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Confirm your password'),
  })
  .refine(values => values.password === values.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })

type SignupFormValues = z.infer<typeof signupSchema>

export function SignupPage() {
  const navigate = useNavigate()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SignupFormValues>({
    resolver: zodResolver(signupSchema),
    defaultValues: { fullName: '', email: '', password: '', confirmPassword: '' },
  })

  function onSubmit() {
    // Same honest framing as LoginPage: no backend account is actually
    // created. This only unlocks the existing, already-open /dashboard route.
    toast.success('Account created', { description: 'Entering the demo dashboard — no live authentication is connected yet.' })
    navigate('/dashboard')
  }

  return (
    <AuthLayout title="Create your account" description="Set up access to the recovery operations console.">
      <form onSubmit={event => void handleSubmit(onSubmit)(event)} noValidate>
        <div className="form-field">
          <label htmlFor="fullName">Full name</label>
          <input id="fullName" type="text" autoComplete="name" placeholder="Sam Analyst" {...register('fullName')} />
          {errors.fullName && <span className="form-error">{errors.fullName.message}</span>}
        </div>

        <div className="form-field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" autoComplete="email" placeholder="you@company.com" {...register('email')} />
          {errors.email && <span className="form-error">{errors.email.message}</span>}
        </div>

        <div className="form-row">
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" autoComplete="new-password" placeholder="••••••••" {...register('password')} />
            {errors.password && <span className="form-error">{errors.password.message}</span>}
          </div>
          <div className="form-field">
            <label htmlFor="confirmPassword">Confirm password</label>
            <input id="confirmPassword" type="password" autoComplete="new-password" placeholder="••••••••" {...register('confirmPassword')} />
            {errors.confirmPassword && <span className="form-error">{errors.confirmPassword.message}</span>}
          </div>
        </div>

        <button type="submit" className="primary-button auth-submit" disabled={isSubmitting}>
          {isSubmitting ? 'Creating account...' : 'Sign up'}
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

        <p className="auth-switch">Already have an account? <Link to="/login">Sign in</Link></p>
      </form>
    </AuthLayout>
  )
}
