import { motion } from 'framer-motion'
import { LucideIcon, TrendingUp, TrendingDown } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MetricCardProps {
  title: string
  value: string
  subtitle?: string
  icon: LucideIcon
  trend?: number
  color?: 'primary' | 'green' | 'red' | 'orange' | 'purple' | 'blue' | 'cyan'
  loading?: boolean
}

const colorClasses = {
  primary: {
    bg: 'bg-primary/20',
    text: 'text-primary',
    glow: 'shadow-primary/20',
  },
  green: {
    bg: 'bg-green-500/20',
    text: 'text-green-500',
    glow: 'shadow-green-500/20',
  },
  red: {
    bg: 'bg-red-500/20',
    text: 'text-red-500',
    glow: 'shadow-red-500/20',
  },
  orange: {
    bg: 'bg-orange-500/20',
    text: 'text-orange-500',
    glow: 'shadow-orange-500/20',
  },
  purple: {
    bg: 'bg-purple-500/20',
    text: 'text-purple-500',
    glow: 'shadow-purple-500/20',
  },
  blue: {
    bg: 'bg-blue-500/20',
    text: 'text-blue-500',
    glow: 'shadow-blue-500/20',
  },
  cyan: {
    bg: 'bg-cyan-500/20',
    text: 'text-cyan-500',
    glow: 'shadow-cyan-500/20',
  },
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = 'primary',
  loading = false,
}: MetricCardProps) {
  const colors = colorClasses[color]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ y: -4, boxShadow: '0 20px 40px -20px rgba(0,0,0,0.3)' }}
      className={cn(
        'p-6 rounded-2xl bg-card border border-border',
        'transition-all duration-300',
        `hover:shadow-lg hover:${colors.glow}`
      )}
    >
      <div className="flex items-start justify-between mb-4">
        <div className={cn('p-3 rounded-xl', colors.bg)}>
          <Icon className={cn('w-5 h-5', colors.text)} />
        </div>
        {trend !== undefined && (
          <div
            className={cn(
              'flex items-center gap-1 text-sm font-medium',
              trend >= 0 ? 'text-green-500' : 'text-red-500'
            )}
          >
            {trend >= 0 ? (
              <TrendingUp className="w-4 h-4" />
            ) : (
              <TrendingDown className="w-4 h-4" />
            )}
            {Math.abs(trend)}%
          </div>
        )}
      </div>

      {loading ? (
        <div className="space-y-2">
          <div className="h-8 w-24 bg-muted rounded animate-pulse" />
          <div className="h-4 w-16 bg-muted rounded animate-pulse" />
        </div>
      ) : (
        <>
          <h3 className="text-2xl font-bold mb-1">{value}</h3>
          <p className="text-sm text-muted-foreground">{subtitle || title}</p>
        </>
      )}
    </motion.div>
  )
}
