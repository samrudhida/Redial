import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'
import { useCreateMandate } from '../hooks/useCreateMandate'
import { extractErrorMessage } from '../utils/apiError'
import { Modal } from './Modal'

const createMandateSchema = z.object({
  customer_id: z.string().trim().min(1, 'Customer ID is required'),
  mandate_reference: z.string().trim().min(1, 'Mandate reference is required'),
  amount: z
    .string()
    .trim()
    .min(1, 'Amount is required')
    .refine(value => Number.isFinite(Number(value)) && Number(value) > 0, 'Amount must be greater than 0'),
  currency: z
    .string()
    .trim()
    .optional()
    .refine(value => !value || value.length === 3, 'Currency must be a 3-letter code (e.g. INR)'),
  bank_name: z.string().trim().optional(),
  account_last4: z
    .string()
    .trim()
    .optional()
    .refine(value => !value || /^\d{4}$/.test(value), 'Must be exactly 4 digits'),
})

type CreateMandateFormValues = z.infer<typeof createMandateSchema>

const DEFAULT_VALUES: CreateMandateFormValues = {
  customer_id: '',
  mandate_reference: '',
  amount: '',
  currency: '',
  bank_name: '',
  account_last4: '',
}

export function CreateMandateModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<CreateMandateFormValues>({
    resolver: zodResolver(createMandateSchema),
    defaultValues: DEFAULT_VALUES,
  })
  const createMandate = useCreateMandate()

  useEffect(() => {
    if (open) reset(DEFAULT_VALUES)
  }, [open, reset])

  function onSubmit(values: CreateMandateFormValues) {
    createMandate.mutate(
      {
        customer_id: values.customer_id,
        mandate_reference: values.mandate_reference,
        amount: values.amount,
        currency: values.currency || undefined,
        bank_name: values.bank_name || undefined,
        account_last4: values.account_last4 || undefined,
      },
      {
        onSuccess: () => {
          toast.success('Mandate created', { description: `${values.mandate_reference} is now active.` })
          onClose()
        },
        onError: error => {
          toast.error('Failed to create mandate', { description: extractErrorMessage(error) })
        },
      },
    )
  }

  return (
    <Modal open={open} onClose={onClose} title="Create mandate">
      <form onSubmit={event => void handleSubmit(onSubmit)(event)}>
        <div className="modal-body">
          <div className="form-field">
            <label htmlFor="customer_id">Customer ID</label>
            <input id="customer_id" type="text" {...register('customer_id')} />
            {errors.customer_id && <span className="form-error">{errors.customer_id.message}</span>}
          </div>

          <div className="form-field">
            <label htmlFor="mandate_reference">Mandate Reference</label>
            <input id="mandate_reference" type="text" {...register('mandate_reference')} />
            {errors.mandate_reference && <span className="form-error">{errors.mandate_reference.message}</span>}
          </div>

          <div className="form-row">
            <div className="form-field">
              <label htmlFor="amount">Amount</label>
              <input id="amount" type="text" inputMode="decimal" placeholder="500.00" {...register('amount')} />
              {errors.amount && <span className="form-error">{errors.amount.message}</span>}
            </div>
            <div className="form-field">
              <label htmlFor="currency">Currency</label>
              <input id="currency" type="text" placeholder="INR" maxLength={3} {...register('currency')} />
              {errors.currency && <span className="form-error">{errors.currency.message}</span>}
            </div>
          </div>

          <div className="form-field">
            <label htmlFor="bank_name">Bank Name (optional)</label>
            <input id="bank_name" type="text" {...register('bank_name')} />
          </div>

          <div className="form-field">
            <label htmlFor="account_last4">Account Last 4 Digits (optional)</label>
            <input id="account_last4" type="text" inputMode="numeric" maxLength={4} placeholder="1234" {...register('account_last4')} />
            {errors.account_last4 && <span className="form-error">{errors.account_last4.message}</span>}
          </div>
        </div>

        <div className="modal-footer">
          <button type="button" className="secondary-button" onClick={onClose} disabled={createMandate.isPending}>Cancel</button>
          <button type="submit" className="primary-button" disabled={createMandate.isPending}>
            {createMandate.isPending ? 'Creating...' : 'Create mandate'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
