import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import {
  Footprints,
  Flame,
  Heart,
  Moon,
  Timer,
  TrendingUp,
  Activity,
  RefreshCw,
  AlertCircle,
  Zap,
  Target,
  Trophy,
  Gauge,
  Battery,
  Brain,
  Wind,
  ThermometerSun,
  Cloud,
  CloudOff,
  Check,
  Loader2,
} from 'lucide-react'
import { healthAPI, activitiesAPI, aiAPI } from '@/lib/api'
import { formatNumber, formatDuration, cn } from '@/lib/utils'
import MetricCard from '@/components/MetricCard'
import StepsChart from '@/components/charts/StepsChart'
import HeartRateChart from '@/components/charts/HeartRateChart'
import SleepChart from '@/components/charts/SleepChart'
import ActivityList from '@/components/ActivityList'

export default function Dashboard() {
  const queryClient = useQueryClient()
  
  const { data: summary, isLoading: summaryLoading, error: summaryError } = useQuery({
    queryKey: ['health-summary'],
    queryFn: () => healthAPI.getSummary(7),
    retry: 1,
    staleTime: 300000, // 5 minutes - serve from cache
  })

  const { data: dailyStats, isLoading: dailyLoading, error: dailyError, refetch: refetchDaily } = useQuery({
    queryKey: ['daily-stats'],
    queryFn: () => healthAPI.getDailyStats(14),
    retry: 2,
    staleTime: 300000, // 5 minutes
  })

  const { data: sleepData, isLoading: sleepLoading, error: sleepError, refetch: refetchSleep } = useQuery({
    queryKey: ['sleep-data'],
    queryFn: () => healthAPI.getSleep(14),
    retry: 2,
    staleTime: 300000, // 5 minutes
  })

  const { data: activities, isLoading: activitiesLoading, error: activitiesError, refetch: refetchActivities } = useQuery({
    queryKey: ['recent-activities'],
    queryFn: () => activitiesAPI.getRecent(15),
    retry: 2,
    staleTime: 300000, // 5 minutes
  })

  const { data: activityStats } = useQuery({
    queryKey: ['activity-stats'],
    queryFn: () => activitiesAPI.getStats(30),
    retry: 1,
    staleTime: 300000, // 5 minutes
  })

  // Fetch performance metrics (VO2max, race predictions, etc.)
  const { data: performanceMetrics, isLoading: performanceLoading } = useQuery({
    queryKey: ['performance-metrics'],
    queryFn: () => healthAPI.getPerformanceMetrics(),
    retry: 1,
    staleTime: 300000, // 5 minutes
  })

  // Fetch today's readiness
  const { data: todayReadiness, isLoading: readinessLoading } = useQuery({
    queryKey: ['today-readiness'],
    queryFn: () => aiAPI.getTodayReadiness(),
    retry: 1,
    staleTime: 300000, // 5 minutes
  })

  // Fetch body battery details
  const { data: bodyBattery, isLoading: bodyBatteryLoading } = useQuery({
    queryKey: ['body-battery-detailed'],
    queryFn: () => healthAPI.getBodyBatteryDetailed(),
    retry: 1,
    staleTime: 300000, // 5 minutes
  })

  // Sync status
  const { data: syncStatus } = useQuery({
    queryKey: ['sync-status'],
    queryFn: () => healthAPI.getSyncStatus(),
    staleTime: 30000, // Check every 30 seconds
  })

  // Sync mutation
  const syncMutation = useMutation({
    mutationFn: () => healthAPI.syncData(),
    onSuccess: () => {
      // Invalidate all queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['health-summary'] })
      queryClient.invalidateQueries({ queryKey: ['daily-stats'] })
      queryClient.invalidateQueries({ queryKey: ['sleep-data'] })
      queryClient.invalidateQueries({ queryKey: ['recent-activities'] })
      queryClient.invalidateQueries({ queryKey: ['activity-stats'] })
      queryClient.invalidateQueries({ queryKey: ['performance-metrics'] })
      queryClient.invalidateQueries({ queryKey: ['today-readiness'] })
      queryClient.invalidateQueries({ queryKey: ['body-battery-detailed'] })
      queryClient.invalidateQueries({ queryKey: ['sync-status'] })
    },
  })

  const handleSync = () => {
    syncMutation.mutate()
  }

  const hasErrors = dailyError || sleepError || activitiesError
  
  // Format last sync time
  const getLastSyncTime = () => {
    const statuses = syncStatus?.sync_status
    if (!statuses) return null
    
    const times = Object.values(statuses)
      .filter(s => s.last_sync_at)
      .map(s => new Date(s.last_sync_at!).getTime())
    
    if (times.length === 0) return null
    
    const lastSync = new Date(Math.max(...times))
    const now = new Date()
    const diffMs = now.getTime() - lastSync.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    return lastSync.toLocaleDateString()
  }

  // Extract performance data
  const vo2max = performanceMetrics?.max_metrics?.generic?.vo2MaxValue || 
                 performanceMetrics?.max_metrics?.cycling?.vo2MaxValue || null
  const fitnessAge = performanceMetrics?.fitness_age?.fitnessAge || null
  const racePredictions = performanceMetrics?.race_predictions || null
  const enduranceScore = performanceMetrics?.endurance_score?.overallScore || null
  const hillScore = performanceMetrics?.hill_score?.hillScore || null
  const personalRecords = performanceMetrics?.personal_records || []

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-bold">Dashboard</h1>
          <p className="text-sm text-muted-foreground">
            Your health and fitness overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Last Sync Status */}
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            {syncStatus?.sync_status ? (
              <>
                <Cloud className="w-4 h-4 text-green-500" />
                <span>Synced {getLastSyncTime()}</span>
              </>
            ) : (
              <>
                <CloudOff className="w-4 h-4 text-yellow-500" />
                <span>Not synced</span>
              </>
            )}
          </div>
          
          {/* Sync Button */}
          <button
            onClick={handleSync}
            disabled={syncMutation.isPending}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-xl transition-all",
              syncMutation.isPending 
                ? "bg-muted text-muted-foreground cursor-not-allowed"
                : "bg-primary text-primary-foreground hover:bg-primary/90"
            )}
          >
            {syncMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Syncing...
              </>
            ) : syncMutation.isSuccess ? (
              <>
                <Check className="w-4 h-4" />
                Synced
              </>
            ) : (
              <>
                <RefreshCw className="w-4 h-4" />
                Sync Now
              </>
            )}
          </button>
        </div>
      </div>

      {/* Error banner */}
      {hasErrors && (
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center gap-3 p-4 rounded-xl bg-yellow-500/20 border border-yellow-500/30"
        >
          <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
          <p className="text-sm text-yellow-200">
            Some data couldn't be loaded. This might happen after a session timeout. 
            Try clicking "Retry" or reconnecting to Garmin.
          </p>
        </motion.div>
      )}

      {/* Today's Readiness Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-6 rounded-2xl bg-gradient-to-br from-primary/20 via-card to-card border border-primary/30"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-lg bg-primary/20">
            <Brain className="w-5 h-5 text-primary" />
          </div>
          <h2 className="text-xl font-semibold">Today's Readiness</h2>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Body Battery */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Battery className={cn(
                "w-4 h-4",
                (todayReadiness?.body_battery || 0) > 60 ? "text-green-500" :
                (todayReadiness?.body_battery || 0) > 30 ? "text-yellow-500" : "text-red-500"
              )} />
              <span className="text-sm text-muted-foreground">Body Battery</span>
            </div>
            <p className="text-2xl font-bold">
              {readinessLoading ? "..." : todayReadiness?.body_battery || "--"}
              <span className="text-sm font-normal text-muted-foreground">/100</span>
            </p>
          </div>

          {/* Sleep Score */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Moon className="w-4 h-4 text-purple-500" />
              <span className="text-sm text-muted-foreground">Sleep Score</span>
            </div>
            <p className="text-2xl font-bold">
              {readinessLoading ? "..." : todayReadiness?.sleep_score || "--"}
              <span className="text-sm font-normal text-muted-foreground">/100</span>
            </p>
          </div>

          {/* Resting HR */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Heart className="w-4 h-4 text-red-500" />
              <span className="text-sm text-muted-foreground">Resting HR</span>
            </div>
            <p className="text-2xl font-bold">
              {readinessLoading ? "..." : todayReadiness?.resting_hr || "--"}
              <span className="text-sm font-normal text-muted-foreground"> bpm</span>
            </p>
          </div>

          {/* Readiness Score */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Zap className={cn(
                "w-4 h-4",
                (todayReadiness?.readiness_score || 0) > 70 ? "text-green-500" :
                (todayReadiness?.readiness_score || 0) > 40 ? "text-yellow-500" : "text-red-500"
              )} />
              <span className="text-sm text-muted-foreground">Readiness</span>
            </div>
            <p className="text-2xl font-bold">
              {readinessLoading ? "..." : Math.round(todayReadiness?.readiness_score || 0)}
              <span className="text-sm font-normal text-muted-foreground">/100</span>
            </p>
          </div>

          {/* Stress Level */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Brain className={cn(
                "w-4 h-4",
                (todayReadiness?.stress_level || 0) < 30 ? "text-green-500" :
                (todayReadiness?.stress_level || 0) < 50 ? "text-yellow-500" : "text-orange-500"
              )} />
              <span className="text-sm text-muted-foreground">Stress</span>
            </div>
            <p className="text-2xl font-bold">
              {readinessLoading ? "..." : todayReadiness?.stress_level || "--"}
              <span className="text-sm font-normal text-muted-foreground">/100</span>
            </p>
          </div>

          {/* HRV Status */}
          <div className="p-4 rounded-xl bg-background/50">
            <div className="flex items-center gap-2 mb-2">
              <Activity className={cn(
                "w-4 h-4",
                todayReadiness?.hrv_status === "BALANCED" ? "text-green-500" :
                todayReadiness?.hrv_status === "HIGH" ? "text-blue-500" : "text-yellow-500"
              )} />
              <span className="text-sm text-muted-foreground">HRV Status</span>
            </div>
            <p className="text-lg font-bold">
              {readinessLoading ? "..." : todayReadiness?.hrv_status || "--"}
            </p>
            {todayReadiness?.hrv_avg && (
              <p className="text-xs text-muted-foreground">{todayReadiness.hrv_avg} ms</p>
            )}
          </div>
        </div>

        {/* Readiness advice */}
        {todayReadiness?.adjustment_reason && (
          <div className={cn(
            "mt-4 p-3 rounded-lg text-sm",
            todayReadiness.should_rest ? "bg-red-500/20 text-red-300" :
            todayReadiness.should_reduce_intensity ? "bg-yellow-500/20 text-yellow-300" :
            "bg-green-500/20 text-green-300"
          )}>
            <strong>{todayReadiness.should_rest ? "⚠️ Rest recommended:" : 
                     todayReadiness.should_reduce_intensity ? "📊 Consider lighter workout:" : 
                     "✅ Ready to train:"}</strong> {todayReadiness.adjustment_reason}
          </div>
        )}
      </motion.div>

      {/* Performance Metrics Section */}
      {(vo2max || fitnessAge || enduranceScore || racePredictions) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
        >
          <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
            <Trophy className="w-5 h-5 text-yellow-500" />
            Performance Metrics
          </h2>
          
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {/* VO2 Max */}
            {vo2max && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <TrendingUp className="w-4 h-4 text-green-500" />
                  <span className="text-xs text-muted-foreground">VO2 Max</span>
                </div>
                <p className="text-2xl font-bold text-green-500">{vo2max}</p>
                <p className="text-xs text-muted-foreground">ml/kg/min</p>
              </div>
            )}

            {/* Fitness Age */}
            {fitnessAge && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Activity className="w-4 h-4 text-blue-500" />
                  <span className="text-xs text-muted-foreground">Fitness Age</span>
                </div>
                <p className="text-2xl font-bold text-blue-500">{Math.round(fitnessAge)}</p>
                <p className="text-xs text-muted-foreground">years</p>
              </div>
            )}

            {/* Endurance Score */}
            {enduranceScore && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Gauge className="w-4 h-4 text-purple-500" />
                  <span className="text-xs text-muted-foreground">Endurance</span>
                </div>
                <p className="text-2xl font-bold text-purple-500">{enduranceScore}</p>
                <p className="text-xs text-muted-foreground">score</p>
              </div>
            )}

            {/* Hill Score */}
            {hillScore && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-4 h-4 text-orange-500" />
                  <span className="text-xs text-muted-foreground">Hill Score</span>
                </div>
                <p className="text-2xl font-bold text-orange-500">{hillScore}</p>
                <p className="text-xs text-muted-foreground">score</p>
              </div>
            )}

            {/* Race Predictions - 5K */}
            {racePredictions?.time5K && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Timer className="w-4 h-4 text-cyan-500" />
                  <span className="text-xs text-muted-foreground">5K Prediction</span>
                </div>
                <p className="text-xl font-bold text-cyan-500">
                  {formatRaceTime(racePredictions.time5K)}
                </p>
              </div>
            )}

            {/* Race Predictions - 10K */}
            {racePredictions?.time10K && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Timer className="w-4 h-4 text-teal-500" />
                  <span className="text-xs text-muted-foreground">10K Prediction</span>
                </div>
                <p className="text-xl font-bold text-teal-500">
                  {formatRaceTime(racePredictions.time10K)}
                </p>
              </div>
            )}

            {/* Race Predictions - Half Marathon */}
            {racePredictions?.timeHalfMarathon && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Trophy className="w-4 h-4 text-yellow-500" />
                  <span className="text-xs text-muted-foreground">Half Marathon</span>
                </div>
                <p className="text-xl font-bold text-yellow-500">
                  {formatRaceTime(racePredictions.timeHalfMarathon)}
                </p>
              </div>
            )}

            {/* Race Predictions - Marathon */}
            {racePredictions?.timeMarathon && (
              <div className="p-4 rounded-xl bg-card border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <Trophy className="w-4 h-4 text-amber-500" />
                  <span className="text-xs text-muted-foreground">Marathon</span>
                </div>
                <p className="text-xl font-bold text-amber-500">
                  {formatRaceTime(racePredictions.timeMarathon)}
                </p>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Key metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Daily Steps"
          value={formatNumber(summary?.avg_steps || 0)}
          subtitle="7-day average"
          icon={Footprints}
          trend={+5.2}
          color="primary"
          loading={summaryLoading}
        />
        <MetricCard
          title="Calories"
          value={formatNumber(summary?.total_calories || 0)}
          subtitle="This week"
          icon={Flame}
          color="orange"
          loading={summaryLoading}
        />
        <MetricCard
          title="Resting HR"
          value={summary?.avg_resting_hr ? `${summary.avg_resting_hr} bpm` : '--'}
          subtitle="7-day average"
          icon={Heart}
          trend={-2}
          color="red"
          loading={summaryLoading}
        />
        <MetricCard
          title="Sleep"
          value={`${(summary?.avg_sleep_hours || 0).toFixed(1)}h`}
          subtitle="Average duration"
          icon={Moon}
          color="purple"
          loading={summaryLoading}
        />
      </div>

      {/* Activity summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard
          title="Active Minutes"
          value={formatNumber(summary?.total_active_minutes || 0)}
          subtitle="This week"
          icon={Timer}
          color="green"
          loading={summaryLoading}
        />
        <MetricCard
          title="Workouts"
          value={activityStats?.total_activities?.toString() || '0'}
          subtitle="Last 30 days"
          icon={Activity}
          color="blue"
        />
        <MetricCard
          title="Distance"
          value={`${(activityStats?.total_distance_km || 0).toFixed(1)} km`}
          subtitle="Last 30 days"
          icon={TrendingUp}
          color="cyan"
        />
      </div>

      {/* Charts section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Steps chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-6 rounded-2xl bg-card border border-border"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Daily Steps</h3>
            {dailyLoading && (
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          {dailyError ? (
            <DataErrorState onRetry={refetchDaily} />
          ) : (
            <StepsChart data={dailyStats?.stats || []} />
          )}
        </motion.div>

        {/* Heart rate chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="p-6 rounded-2xl bg-card border border-border"
        >
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">Resting Heart Rate</h3>
            {dailyLoading && (
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </div>
          {dailyError ? (
            <DataErrorState onRetry={refetchDaily} />
          ) : (
            <HeartRateChart data={dailyStats?.stats || []} />
          )}
        </motion.div>
      </div>

      {/* Sleep chart */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="p-6 rounded-2xl bg-card border border-border"
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Sleep Analysis</h3>
          {sleepLoading && (
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        {sleepError ? (
          <DataErrorState onRetry={refetchSleep} />
        ) : (
          <SleepChart data={sleepData?.sleep || []} />
        )}
      </motion.div>

      {/* Recent activities with AI analysis */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="p-6 rounded-2xl bg-card border border-border"
      >
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold">Recent Activities</h3>
            <p className="text-sm text-muted-foreground">Click on an activity for AI-powered analysis</p>
          </div>
          {activitiesLoading && (
            <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
          )}
        </div>
        {activitiesError ? (
          <DataErrorState onRetry={refetchActivities} />
        ) : (
          <ActivityList activities={activities?.activities || []} showAnalysis />
        )}
      </motion.div>
    </div>
  )
}

function DataErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="h-[250px] flex flex-col items-center justify-center text-center">
      <AlertCircle className="w-10 h-10 text-muted-foreground mb-3" />
      <p className="text-muted-foreground mb-4">Failed to load data</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-muted hover:bg-muted/80 text-sm transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Retry
      </button>
    </div>
  )
}

// Helper function to format race times
function formatRaceTime(seconds: number): string {
  if (!seconds) return '--'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = Math.floor(seconds % 60)
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`
}
