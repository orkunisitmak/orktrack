import { useState } from 'react'
import { motion } from 'framer-motion'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  Brain,
  TrendingUp,
  TrendingDown,
  Moon,
  Activity,
  Heart,
  Loader2,
  CheckCircle,
  AlertTriangle,
  Info,
  Sparkles,
  RefreshCw,
} from 'lucide-react'
import { aiAPI, healthAPI } from '@/lib/api'
import { cn, getScoreColor, getScoreBgColor } from '@/lib/utils'

export default function Insights() {
  const [period, setPeriod] = useState<'week' | 'month'>('week')
  const [insights, setInsights] = useState<any>(null)

  const { data: summary } = useQuery({
    queryKey: ['health-summary', period],
    queryFn: () => healthAPI.getSummary(period === 'week' ? 7 : 30),
  })

  const generateMutation = useMutation({
    mutationFn: () => aiAPI.generateInsights(period),
    onSuccess: (data) => setInsights(data),
  })

  const highlightIcons: Record<string, React.ReactNode> = {
    positive: <CheckCircle className="w-5 h-5 text-green-500" />,
    warning: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
    info: <Info className="w-5 h-5 text-blue-500" />,
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2">Health Insights</h1>
          <p className="text-muted-foreground">
            AI-powered analysis of your health and fitness data
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setPeriod('week')}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              period === 'week'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 hover:bg-muted'
            )}
          >
            Week
          </button>
          <button
            onClick={() => setPeriod('month')}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              period === 'month'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 hover:bg-muted'
            )}
          >
            Month
          </button>
        </div>
      </div>

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <QuickStat
          label="Avg Steps"
          value={summary?.avg_steps?.toLocaleString() || '--'}
          icon={Activity}
          color="primary"
        />
        <QuickStat
          label="Avg Sleep"
          value={`${summary?.avg_sleep_hours?.toFixed(1) || '--'}h`}
          icon={Moon}
          color="purple"
        />
        <QuickStat
          label="Resting HR"
          value={summary?.avg_resting_hr ? `${summary.avg_resting_hr} bpm` : '--'}
          icon={Heart}
          color="red"
        />
        <QuickStat
          label="Active Mins"
          value={summary?.total_active_minutes?.toLocaleString() || '--'}
          icon={TrendingUp}
          color="green"
        />
      </div>

      {/* Generate insights */}
      {!insights ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-8 rounded-2xl bg-card border border-border text-center"
        >
          <div className="p-4 rounded-2xl bg-primary/20 inline-flex mb-4">
            <Brain className="w-10 h-10 text-primary" />
          </div>
          <h3 className="text-xl font-semibold mb-2">Generate AI Insights</h3>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Get personalized health insights based on your Garmin data analysis
            for the past {period === 'week' ? 'week' : 'month'}.
          </p>
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => generateMutation.mutate()}
            disabled={generateMutation.isPending}
            className={cn(
              'px-8 py-4 rounded-xl font-semibold',
              'bg-gradient-to-r from-primary to-purple-500',
              'text-white shadow-lg shadow-primary/30',
              'disabled:opacity-50 disabled:cursor-not-allowed',
              'flex items-center gap-2 mx-auto'
            )}
          >
            {generateMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing your data...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                Generate Insights
              </>
            )}
          </motion.button>
        </motion.div>
      ) : (
        <div className="space-y-6">
          {/* Overall score */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="p-6 rounded-2xl bg-card border border-border"
          >
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">Overall Health Score</h3>
              <button
                onClick={() => generateMutation.mutate()}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <RefreshCw
                  className={cn(
                    'w-5 h-5',
                    generateMutation.isPending && 'animate-spin'
                  )}
                />
              </button>
            </div>
            <div className="flex items-center gap-6">
              <div
                className={cn(
                  'text-5xl font-bold',
                  getScoreColor(insights.overall_score)
                )}
              >
                {insights.overall_score}
              </div>
              <div className="flex-1">
                <div className="h-4 bg-muted rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${insights.overall_score}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                    className={cn(
                      'h-full rounded-full',
                      insights.overall_score >= 70
                        ? 'bg-green-500'
                        : insights.overall_score >= 50
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    )}
                  />
                </div>
                <p className="text-muted-foreground mt-2">
                  {insights.overall_assessment}
                </p>
              </div>
            </div>
          </motion.div>

          {/* Highlights */}
          {insights.highlights?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              {insights.highlights.map((highlight: any, index: number) => (
                <div
                  key={index}
                  className={cn(
                    'p-4 rounded-xl border',
                    highlight.type === 'positive' &&
                      'bg-green-500/10 border-green-500/30',
                    highlight.type === 'warning' &&
                      'bg-yellow-500/10 border-yellow-500/30',
                    highlight.type === 'info' && 'bg-blue-500/10 border-blue-500/30'
                  )}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {highlightIcons[highlight.type]}
                    <span className="font-semibold">{highlight.title}</span>
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {highlight.description}
                  </p>
                  {highlight.value && (
                    <p className="text-lg font-bold mt-2">
                      {highlight.metric}: {highlight.value}
                    </p>
                  )}
                </div>
              ))}
            </motion.div>
          )}

          {/* Detailed analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Sleep */}
            {insights.sleep_analysis && (
              <AnalysisCard
                title="Sleep Analysis"
                icon={Moon}
                rating={insights.sleep_analysis.quality_rating}
                insights={insights.sleep_analysis.insights}
                recommendations={insights.sleep_analysis.recommendations}
                color="purple"
              />
            )}

            {/* Activity */}
            {insights.activity_analysis && (
              <AnalysisCard
                title="Activity Analysis"
                icon={Activity}
                rating={insights.activity_analysis.consistency_rating}
                insights={insights.activity_analysis.insights}
                recommendations={insights.activity_analysis.recommendations}
                color="green"
              />
            )}

            {/* Recovery */}
            {insights.recovery_analysis && (
              <AnalysisCard
                title="Recovery Status"
                icon={Heart}
                rating={insights.recovery_analysis.status}
                insights={insights.recovery_analysis.insights}
                recommendations={insights.recovery_analysis.recommendations}
                color="red"
              />
            )}
          </div>

          {/* Weekly focus & motivation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {insights.weekly_focus && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 }}
                className="p-6 rounded-2xl bg-primary/10 border border-primary/30"
              >
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  This Week's Focus
                </h3>
                <p className="text-lg">{insights.weekly_focus}</p>
              </motion.div>
            )}

            {insights.motivational_message && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5 }}
                className="p-6 rounded-2xl bg-gradient-to-br from-purple-500/20 to-primary/20 border border-purple-500/30"
              >
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-purple-500" />
                  Keep Going!
                </h3>
                <p className="text-lg">{insights.motivational_message}</p>
              </motion.div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function QuickStat({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  icon: React.ElementType
  color: 'primary' | 'purple' | 'red' | 'green'
}) {
  const colorClasses = {
    primary: 'bg-primary/20 text-primary',
    purple: 'bg-purple-500/20 text-purple-500',
    red: 'bg-red-500/20 text-red-500',
    green: 'bg-green-500/20 text-green-500',
  }

  return (
    <div className="p-4 rounded-xl bg-card border border-border">
      <div
        className={cn('p-2 rounded-lg inline-flex mb-3', colorClasses[color])}
      >
        <Icon className="w-4 h-4" />
      </div>
      <p className="text-2xl font-bold">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  )
}

function AnalysisCard({
  title,
  icon: Icon,
  rating,
  insights,
  recommendations,
  color,
}: {
  title: string
  icon: React.ElementType
  rating: string
  insights: string[]
  recommendations: string[]
  color: 'purple' | 'green' | 'red'
}) {
  const colorClasses = {
    purple: 'bg-purple-500/20 text-purple-500',
    green: 'bg-green-500/20 text-green-500',
    red: 'bg-red-500/20 text-red-500',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 }}
      className="p-6 rounded-2xl bg-card border border-border"
    >
      <div className="flex items-center gap-3 mb-4">
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold">{title}</h3>
          <span
            className={cn(
              'text-xs px-2 py-0.5 rounded',
              rating === 'Excellent' && 'bg-green-500/20 text-green-500',
              rating === 'Good' && 'bg-blue-500/20 text-blue-500',
              rating === 'Fair' && 'bg-yellow-500/20 text-yellow-500',
              (rating === 'Poor' || rating === 'Needs Attention') &&
                'bg-red-500/20 text-red-500'
            )}
          >
            {rating}
          </span>
        </div>
      </div>

      {insights?.length > 0 && (
        <div className="mb-4">
          <p className="text-xs text-muted-foreground uppercase mb-2">
            Key Insights
          </p>
          <ul className="space-y-1">
            {insights.slice(0, 3).map((insight: string, i: number) => (
              <li key={i} className="text-sm flex items-start gap-2">
                <span className="text-muted-foreground">•</span>
                {insight}
              </li>
            ))}
          </ul>
        </div>
      )}

      {recommendations?.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground uppercase mb-2">
            Recommendations
          </p>
          <ul className="space-y-1">
            {recommendations.slice(0, 2).map((rec: string, i: number) => (
              <li
                key={i}
                className="text-sm flex items-start gap-2 text-primary"
              >
                <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </motion.div>
  )
}
