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
  Zap,
  Target,
  Award,
  BarChart3,
  Battery,
  Gauge,
  Clock,
  ArrowUp,
  ArrowDown,
  Minus,
} from 'lucide-react'
import { aiAPI, healthAPI } from '@/lib/api'
import { cn, getScoreColor, getScoreBgColor } from '@/lib/utils'

export default function Insights() {
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week')
  const [insights, setInsights] = useState<any>(null)

  const { data: summary } = useQuery({
    queryKey: ['health-summary', period],
    queryFn: () => healthAPI.getSummary(period === 'day' ? 1 : period === 'week' ? 7 : 30),
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
            onClick={() => setPeriod('day')}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              period === 'day'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 hover:bg-muted'
            )}
          >
            Today
          </button>
          <button
            onClick={() => setPeriod('week')}
            className={cn(
              'px-4 py-2 rounded-lg transition-colors',
              period === 'week'
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted/50 hover:bg-muted'
            )}
          >
            Last 7 Days
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
            Last 30 Days
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
            for the last {period === 'week' ? '7 days' : '30 days'}.
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

          {/* Period Summary */}
          {insights.period_summary && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="grid grid-cols-2 md:grid-cols-5 gap-4"
            >
              <SummaryCard
                label="Activities"
                value={insights.period_summary.total_activities || 0}
                icon={Activity}
              />
              <SummaryCard
                label="Duration"
                value={`${(insights.period_summary.total_duration_hours || 0).toFixed(1)}h`}
                icon={Clock}
              />
              <SummaryCard
                label="Distance"
                value={`${(insights.period_summary.total_distance_km || 0).toFixed(1)}km`}
                icon={TrendingUp}
              />
              <SummaryCard
                label="Avg Sleep"
                value={`${(insights.period_summary.avg_sleep_hours || 0).toFixed(1)}h`}
                icon={Moon}
              />
              <SummaryCard
                label="Sleep Score"
                value={`${Math.round(insights.period_summary.avg_sleep_score || 0)}`}
                icon={Gauge}
              />
            </motion.div>
          )}

          {/* Detailed analysis - First Row */}
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
                extraData={
                  insights.sleep_analysis.sleep_stages && (
                    <div className="mt-3 p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-2">Sleep Stages</p>
                      <div className="flex gap-2 text-xs">
                        <span className="px-2 py-1 bg-purple-500/20 rounded">
                          Deep: {(insights.sleep_analysis.sleep_stages.deep_hours || 0).toFixed(1)}h
                        </span>
                        <span className="px-2 py-1 bg-blue-500/20 rounded">
                          REM: {(insights.sleep_analysis.sleep_stages.rem_hours || 0).toFixed(1)}h
                        </span>
                        <span className="px-2 py-1 bg-gray-500/20 rounded">
                          Light: {(insights.sleep_analysis.sleep_stages.light_hours || 0).toFixed(1)}h
                        </span>
                      </div>
                    </div>
                  )
                }
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
                extraData={
                  insights.activity_analysis.intensity_distribution && (
                    <div className="mt-3 p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground mb-2">Intensity Distribution</p>
                      <div className="flex gap-1 h-3 rounded-full overflow-hidden">
                        <div 
                          className="bg-green-500" 
                          style={{ width: `${insights.activity_analysis.intensity_distribution.low_percentage || 0}%` }}
                        />
                        <div 
                          className="bg-yellow-500" 
                          style={{ width: `${insights.activity_analysis.intensity_distribution.moderate_percentage || 0}%` }}
                        />
                        <div 
                          className="bg-red-500" 
                          style={{ width: `${insights.activity_analysis.intensity_distribution.high_percentage || 0}%` }}
                        />
                      </div>
                      <div className="flex justify-between text-xs mt-1">
                        <span className="text-green-500">Low {insights.activity_analysis.intensity_distribution.low_percentage || 0}%</span>
                        <span className="text-yellow-500">Mod {insights.activity_analysis.intensity_distribution.moderate_percentage || 0}%</span>
                        <span className="text-red-500">High {insights.activity_analysis.intensity_distribution.high_percentage || 0}%</span>
                      </div>
                    </div>
                  )
                }
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
                extraData={
                  <div className="mt-3 p-3 bg-muted/30 rounded-lg space-y-2">
                    {insights.recovery_analysis.hrv_analysis && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">HRV</span>
                        <span className="flex items-center gap-1">
                          {insights.recovery_analysis.hrv_analysis.avg_hrv || '--'} ms
                          <TrendIcon trend={insights.recovery_analysis.hrv_analysis.hrv_trend} />
                        </span>
                      </div>
                    )}
                    {insights.recovery_analysis.body_battery_analysis && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Body Battery</span>
                        <span className="flex items-center gap-1">
                          {insights.recovery_analysis.body_battery_analysis.current_level || '--'}/100
                          <TrendIcon trend={insights.recovery_analysis.body_battery_analysis.trend} />
                        </span>
                      </div>
                    )}
                    {insights.recovery_analysis.recovery_time_hours && (
                      <div className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">Recovery Time</span>
                        <span>{insights.recovery_analysis.recovery_time_hours}h</span>
                      </div>
                    )}
                  </div>
                }
              />
            )}
          </div>

          {/* Second Row - Performance & Stress */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Performance Analysis */}
            {insights.performance_analysis && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3 }}
                className="p-6 rounded-2xl bg-card border border-border"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-amber-500/20 text-amber-500">
                    <Award className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold">Performance Metrics</h3>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mb-4">
                  {insights.performance_analysis.vo2_max && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">VO2 Max</p>
                      <p className="text-xl font-bold text-amber-500">
                        {typeof insights.performance_analysis.vo2_max === 'number' 
                          ? insights.performance_analysis.vo2_max.toFixed(1) 
                          : insights.performance_analysis.vo2_max}
                      </p>
                      {insights.performance_analysis.vo2_max_trend && (
                        <p className="text-xs flex items-center gap-1 mt-1">
                          <TrendIcon trend={insights.performance_analysis.vo2_max_trend} />
                          {insights.performance_analysis.vo2_max_trend}
                        </p>
                      )}
                    </div>
                  )}
                  {insights.performance_analysis.fitness_age && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Fitness Age</p>
                      <p className="text-xl font-bold text-green-500">
                        {Math.round(insights.performance_analysis.fitness_age)}
                      </p>
                      {insights.performance_analysis.fitness_age_vs_actual && (
                        <p className="text-xs text-muted-foreground mt-1">
                          {insights.performance_analysis.fitness_age_vs_actual > 0 ? '+' : ''}
                          {insights.performance_analysis.fitness_age_vs_actual} vs actual
                        </p>
                      )}
                    </div>
                  )}
                  {insights.performance_analysis.endurance_score && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Endurance Score</p>
                      <p className="text-xl font-bold text-blue-500">
                        {insights.performance_analysis.endurance_score}
                      </p>
                    </div>
                  )}
                  {insights.performance_analysis.training_status && (
                    <div className="p-3 bg-muted/30 rounded-lg">
                      <p className="text-xs text-muted-foreground">Training Status</p>
                      <p className="text-sm font-semibold">
                        {insights.performance_analysis.training_status}
                      </p>
                    </div>
                  )}
                </div>

                {insights.performance_analysis.insights?.length > 0 && (
                  <div className="space-y-1">
                    {insights.performance_analysis.insights.slice(0, 2).map((insight: string, i: number) => (
                      <p key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                        <span>•</span> {insight}
                      </p>
                    ))}
                  </div>
                )}
              </motion.div>
            )}

            {/* Stress Analysis */}
            {insights.stress_analysis && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.35 }}
                className="p-6 rounded-2xl bg-card border border-border"
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 rounded-lg bg-orange-500/20 text-orange-500">
                    <Zap className="w-5 h-5" />
                  </div>
                  <h3 className="font-semibold">Stress Analysis</h3>
                </div>

                <div className="flex items-center gap-6 mb-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Avg Stress</p>
                    <p className={cn(
                      "text-3xl font-bold",
                      (insights.stress_analysis.avg_stress_level || 0) < 30 ? "text-green-500" :
                      (insights.stress_analysis.avg_stress_level || 0) < 50 ? "text-yellow-500" :
                      "text-red-500"
                    )}>
                      {insights.stress_analysis.avg_stress_level || '--'}
                    </p>
                    <p className="text-xs text-muted-foreground">/100</p>
                  </div>
                  <div className="flex-1">
                    <div className="h-3 bg-muted rounded-full overflow-hidden">
                      <div 
                        className={cn(
                          "h-full rounded-full transition-all",
                          (insights.stress_analysis.avg_stress_level || 0) < 30 ? "bg-green-500" :
                          (insights.stress_analysis.avg_stress_level || 0) < 50 ? "bg-yellow-500" :
                          "bg-red-500"
                        )}
                        style={{ width: `${insights.stress_analysis.avg_stress_level || 0}%` }}
                      />
                    </div>
                    {insights.stress_analysis.stress_trend && (
                      <p className="text-xs mt-1 flex items-center gap-1">
                        <TrendIcon trend={insights.stress_analysis.stress_trend} />
                        Trend: {insights.stress_analysis.stress_trend}
                      </p>
                    )}
                  </div>
                </div>

                {insights.stress_analysis.insights?.length > 0 && (
                  <div className="space-y-1 mb-3">
                    {insights.stress_analysis.insights.slice(0, 2).map((insight: string, i: number) => (
                      <p key={i} className="text-sm text-muted-foreground flex items-start gap-2">
                        <span>•</span> {insight}
                      </p>
                    ))}
                  </div>
                )}

                {insights.stress_analysis.recommendations?.length > 0 && (
                  <div className="p-3 bg-orange-500/10 rounded-lg">
                    <p className="text-xs font-medium text-orange-500 mb-1">Recommendation</p>
                    <p className="text-sm">{insights.stress_analysis.recommendations[0]}</p>
                  </div>
                )}
              </motion.div>
            )}
          </div>

          {/* Action Plan */}
          {insights.action_plan?.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4 }}
              className="p-6 rounded-2xl bg-card border border-border"
            >
              <h3 className="font-semibold mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                Action Plan
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {insights.action_plan.map((action: any, index: number) => (
                  <div 
                    key={index}
                    className="p-4 rounded-xl bg-muted/30 border border-border"
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <span className={cn(
                        "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold",
                        action.priority === 1 ? "bg-red-500/20 text-red-500" :
                        action.priority === 2 ? "bg-yellow-500/20 text-yellow-500" :
                        "bg-green-500/20 text-green-500"
                      )}>
                        {action.priority}
                      </span>
                      <span className="text-xs text-muted-foreground uppercase">{action.area}</span>
                    </div>
                    <p className="font-medium mb-1">{action.action}</p>
                    {action.timing && (
                      <p className="text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {action.timing}
                      </p>
                    )}
                    {action.expected_impact && (
                      <p className="text-xs text-primary mt-2">{action.expected_impact}</p>
                    )}
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {/* Weekly focus & motivation */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {insights.weekly_focus && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.45 }}
                className="p-6 rounded-2xl bg-primary/10 border border-primary/30"
              >
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  <TrendingUp className="w-5 h-5 text-primary" />
                  Your Focus Area
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

          {/* Data Sources */}
          {insights.data_sources && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6 }}
              className="flex items-center justify-center gap-4 text-xs text-muted-foreground"
            >
              <span>Data analyzed:</span>
              <span>{insights.data_sources.sleep_nights} nights sleep</span>
              <span>•</span>
              <span>{insights.data_sources.activities_count} activities</span>
              <span>•</span>
              <span>{insights.data_sources.hrv_days} days HRV</span>
              <span>•</span>
              <span>{insights.data_sources.body_battery_days} days body battery</span>
            </motion.div>
          )}
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

function SummaryCard({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string | number
  icon: React.ElementType
}) {
  return (
    <div className="p-4 rounded-xl bg-card border border-border flex items-center gap-3">
      <div className="p-2 rounded-lg bg-muted">
        <Icon className="w-4 h-4 text-muted-foreground" />
      </div>
      <div>
        <p className="text-lg font-bold">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  )
}

function TrendIcon({ trend }: { trend?: string }) {
  if (!trend) return null
  
  if (trend === 'improving' || trend === 'increasing') {
    return <ArrowUp className="w-3 h-3 text-green-500" />
  }
  if (trend === 'declining' || trend === 'decreasing' || trend === 'worsening') {
    return <ArrowDown className="w-3 h-3 text-red-500" />
  }
  return <Minus className="w-3 h-3 text-muted-foreground" />
}

function AnalysisCard({
  title,
  icon: Icon,
  rating,
  insights,
  recommendations,
  color,
  extraData,
}: {
  title: string
  icon: React.ElementType
  rating: string
  insights: string[]
  recommendations: string[]
  color: 'purple' | 'green' | 'red'
  extraData?: React.ReactNode
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

      {extraData}

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
