import { motion } from 'framer-motion'
import { formatConfidencePercent } from '../utils/format'
import { confidenceTone } from '../utils/statusPresentation'

/** Shared confidence visualization — a color-coded, animated fill bar reused across every AI surface in the app. */
export function ConfidenceMeter({ score }: { score: string }) {
  const tone = confidenceTone(score)
  const percent = formatConfidencePercent(score)
  return (
    <span className={`confidence ${tone !== 'info' ? `tone-${tone}` : ''}`}>
      <motion.span initial={{ width: 0 }} animate={{ width: percent }} transition={{ duration: 0.6, ease: 'easeOut' }} />
      {percent}
    </span>
  )
}
