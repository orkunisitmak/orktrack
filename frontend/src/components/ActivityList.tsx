import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { 
  Clock, 
  Flame, 
  Heart, 
  MapPin, 
  ChevronDown,
  TrendingUp,
  TrendingDown,
  Mountain,
  Gauge,
  Timer,
  Zap,
  Activity,
  Sparkles,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ArrowUpRight,
  ArrowDownRight,
  Minus,
  Lightbulb,
  Target,
  BarChart3,
  Loader2,
  Wind,
  Brain,
  Footprints,
  BatteryCharging,
  ThermometerSun,
  CloudRain,
  RefreshCw,
} from 'lucide-react'
import { formatDuration, formatDistance, getActivityIcon, cn } from '@/lib/utils'
import { aiAPI } from '@/lib/api'

interface Activity {
  activityId: string | number
  activityName: string
  activityType?: { typeKey: string }
  startTimeLocal?: string
  duration?: number
  distance?: number
  calories?: number
  averageHR?: number
  maxHR?: number
  averageSpeed?: number
  maxSpeed?: number
  elevationGain?: number
  elevationLoss?: number
  steps?: number
  aerobicTrainingEffect?: number
  anaerobicTrainingEffect?: number
  trainingEffectAerobic?: number
  trainingEffectAnaerobic?: number
  averageRunningCadenceInStepsPerMinute?: number
  maxRunningCadenceInStepsPerMinute?: number
  vO2MaxValue?: number
  lactateThresholdHeartRate?: number
  lactateThresholdSpeed?: number
  // New metrics
  avgStressLevel?: number
  maxStressLevel?: number
  avgRespirationRate?: number
  maxRespirationRate?: number
  performanceCondition?: number
  firstBeatPerformanceCondition?: number
  avgStrideLength?: number
  avgPower?: number
  maxPower?: number
  normPower?: number
  trainingLoad?: number
  recoveryTimeInMinutes?: number
}

interface ActivityListProps {
  activities: Activity[]
  showAnalysis?: boolean
}

export default function ActivityList({ activities, showAnalysis = false }: ActivityListProps) {
  const [expandedId, setExpandedId] = useState<string | number | null>(null)
  const [analysisId, setAnalysisId] = useState<string | number | null>(null)

  if (activities.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        No activities found
      </div>
    )
  }

  const toggleExpand = (id: string | number) => {
    setExpandedId(expandedId === id ? null : id)
    if (expandedId === id) {
      setAnalysisId(null)
    }
  }

  const handleAnalyze = (e: React.MouseEvent, id: string | number) => {
    e.stopPropagation()
    setAnalysisId(analysisId === id ? null : id)
  }

  return (
    <div className="space-y-3">
      {activities.map((activity, index) => {
        const type = activity.activityType?.typeKey || 'other'
        const name = activity.activityName || type.replace('_', ' ')
        const startTime = activity.startTimeLocal
          ? new Date(activity.startTimeLocal).toLocaleDateString('en-US', {
              weekday: 'short',
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })
          : ''
        const isExpanded = expandedId === activity.activityId
        const showingAnalysis = analysisId === activity.activityId
        const durationMins = (activity.duration || 0) / 60
        const distanceKm = (activity.distance || 0) / 1000
        
        // Calculate pace for running activities
        let paceStr = ''
        if (distanceKm > 0 && durationMins > 0 && 
            ['running', 'walking', 'trail_running', 'treadmill_running'].includes(type)) {
          const pace = durationMins / distanceKm
          const paceMins = Math.floor(pace)
          const paceSecs = Math.round((pace - paceMins) * 60)
          paceStr = `${paceMins}:${paceSecs.toString().padStart(2, '0')}/km`
        }

        // Get training effect values
        const teAerobic = activity.aerobicTrainingEffect || activity.trainingEffectAerobic || 0
        const teAnaerobic = activity.anaerobicTrainingEffect || activity.trainingEffectAnaerobic || 0

        return (
          <motion.div
            key={activity.activityId}
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.05 }}
            className={cn(
              'rounded-xl bg-muted/30 overflow-hidden transition-all cursor-pointer',
              isExpanded ? 'ring-2 ring-primary/50' : 'hover:bg-muted/50'
            )}
            onClick={() => toggleExpand(activity.activityId)}
          >
            {/* Main row */}
            <div className="flex items-center gap-4 p-4">
              {/* Activity icon */}
              <div className="text-2xl">{getActivityIcon(type)}</div>

              {/* Activity info */}
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold truncate capitalize">{name}</h4>
                <p className="text-sm text-muted-foreground">{startTime}</p>
              </div>

              {/* Quick stats */}
              <div className="flex items-center gap-6 text-sm">
                {activity.duration && (
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Clock className="w-4 h-4" />
                    <span>{formatDuration(durationMins)}</span>
                  </div>
                )}
                {distanceKm > 0 && (
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <MapPin className="w-4 h-4" />
                    <span>{formatDistance(distanceKm)}</span>
                  </div>
                )}
                {activity.averageHR && (
                  <div className="flex items-center gap-1.5 text-red-500">
                    <Heart className="w-4 h-4" />
                    <span>{activity.averageHR}</span>
                  </div>
                )}
              </div>

              {/* Expand icon */}
              <motion.div
                animate={{ rotate: isExpanded ? 180 : 0 }}
                transition={{ duration: 0.2 }}
              >
                <ChevronDown className="w-5 h-5 text-muted-foreground" />
              </motion.div>
            </div>

            {/* Expanded details */}
            <AnimatePresence>
              {isExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="overflow-hidden"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="px-4 pb-4 pt-2 border-t border-border/50">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {/* Duration */}
                      <DetailItem
                        icon={Timer}
                        label="Duration"
                        value={formatDuration(durationMins)}
                        color="blue"
                      />

                      {/* Distance */}
                      {distanceKm > 0 && (
                        <DetailItem
                          icon={MapPin}
                          label="Distance"
                          value={formatDistance(distanceKm)}
                          color="green"
                        />
                      )}

                      {/* Pace */}
                      {paceStr && (
                        <DetailItem
                          icon={Gauge}
                          label="Avg Pace"
                          value={paceStr}
                          color="purple"
                        />
                      )}

                      {/* Calories */}
                      {activity.calories && (
                        <DetailItem
                          icon={Flame}
                          label="Calories"
                          value={`${activity.calories}`}
                          color="orange"
                        />
                      )}

                      {/* Avg Heart Rate */}
                      {activity.averageHR && (
                        <DetailItem
                          icon={Heart}
                          label="Avg HR"
                          value={`${activity.averageHR} bpm`}
                          color="red"
                        />
                      )}

                      {/* Max Heart Rate */}
                      {activity.maxHR && (
                        <DetailItem
                          icon={Heart}
                          label="Max HR"
                          value={`${activity.maxHR} bpm`}
                          color="red"
                          highlight
                        />
                      )}

                      {/* Elevation Gain */}
                      {(activity.elevationGain ?? 0) > 0 && (
                        <DetailItem
                          icon={Mountain}
                          label="Elevation"
                          value={`↑${activity.elevationGain.toFixed(0)}m`}
                          color="cyan"
                        />
                      )}

                      {/* Steps */}
                      {(activity.steps ?? 0) > 100 && (
                        <DetailItem
                          icon={Activity}
                          label="Steps"
                          value={activity.steps.toLocaleString()}
                          color="primary"
                        />
                      )}

                      {/* Aerobic Training Effect */}
                      {teAerobic > 0 && (
                        <DetailItem
                          icon={TrendingUp}
                          label="Aerobic TE"
                          value={teAerobic.toFixed(1)}
                          color="green"
                        />
                      )}

                      {/* Anaerobic Training Effect */}
                      {teAnaerobic > 0 && (
                        <DetailItem
                          icon={Zap}
                          label="Anaerobic TE"
                          value={teAnaerobic.toFixed(1)}
                          color="yellow"
                        />
                      )}

                      {/* Cadence */}
                      {(activity.averageRunningCadenceInStepsPerMinute ?? 0) > 10 && (
                        <DetailItem
                          icon={Activity}
                          label="Cadence"
                          value={`${Math.round(activity.averageRunningCadenceInStepsPerMinute)} spm`}
                          color="purple"
                        />
                      )}

                      {/* VO2 Max */}
                      {activity.vO2MaxValue && (
                        <DetailItem
                          icon={TrendingUp}
                          label="VO2 Max"
                          value={`${activity.vO2MaxValue}`}
                          color="green"
                          highlight
                        />
                      )}

                      {/* Stress Level */}
                      {(activity.avgStressLevel ?? 0) > 0 && (
                        <DetailItem
                          icon={Brain}
                          label="Avg Stress"
                          value={`${activity.avgStressLevel}`}
                          color={activity.avgStressLevel < 40 ? "green" : activity.avgStressLevel < 60 ? "yellow" : "orange"}
                        />
                      )}

                      {/* Max Stress */}
                      {(activity.maxStressLevel ?? 0) > 0 && activity.maxStressLevel !== activity.avgStressLevel && (
                        <DetailItem
                          icon={Brain}
                          label="Max Stress"
                          value={`${activity.maxStressLevel}`}
                          color="orange"
                        />
                      )}

                      {/* Respiration Rate */}
                      {(activity.avgRespirationRate ?? 0) > 0 && (
                        <DetailItem
                          icon={Wind}
                          label="Avg Respiration"
                          value={`${activity.avgRespirationRate.toFixed(1)} brpm`}
                          color="cyan"
                        />
                      )}

                      {/* Max Respiration */}
                      {(activity.maxRespirationRate ?? 0) > 0 && activity.maxRespirationRate !== activity.avgRespirationRate && (
                        <DetailItem
                          icon={Wind}
                          label="Max Respiration"
                          value={`${activity.maxRespirationRate.toFixed(1)} brpm`}
                          color="cyan"
                          highlight
                        />
                      )}

                      {/* Performance Condition */}
                      {(activity.performanceCondition !== undefined && activity.performanceCondition !== null) || 
                       (activity.firstBeatPerformanceCondition !== undefined && activity.firstBeatPerformanceCondition !== null) ? (
                        <DetailItem
                          icon={Gauge}
                          label="Performance"
                          value={`${(activity.performanceCondition ?? activity.firstBeatPerformanceCondition ?? 0) > 0 ? '+' : ''}${activity.performanceCondition ?? activity.firstBeatPerformanceCondition}`}
                          color={(activity.performanceCondition ?? activity.firstBeatPerformanceCondition ?? 0) >= 0 ? "green" : "red"}
                          highlight
                        />
                      ) : null}

                      {/* Stride Length */}
                      {(activity.avgStrideLength ?? 0) > 0 && (
                        <DetailItem
                          icon={Footprints}
                          label="Stride Length"
                          value={`${(activity.avgStrideLength / 100).toFixed(2)} m`}
                          color="blue"
                        />
                      )}

                      {/* Power */}
                      {(activity.avgPower ?? 0) > 0 && (
                        <DetailItem
                          icon={Zap}
                          label="Avg Power"
                          value={`${activity.avgPower} W`}
                          color="yellow"
                        />
                      )}

                      {/* Normalized Power */}
                      {(activity.normPower ?? 0) > 0 && (
                        <DetailItem
                          icon={Zap}
                          label="Norm Power"
                          value={`${activity.normPower} W`}
                          color="yellow"
                          highlight
                        />
                      )}

                      {/* Training Load */}
                      {(activity.trainingLoad ?? 0) > 0 && (
                        <DetailItem
                          icon={BatteryCharging}
                          label="Training Load"
                          value={`${activity.trainingLoad}`}
                          color="purple"
                        />
                      )}

                      {/* Recovery Time */}
                      {(activity.recoveryTimeInMinutes ?? 0) > 0 && (
                        <DetailItem
                          icon={Timer}
                          label="Recovery"
                          value={activity.recoveryTimeInMinutes >= 60 
                            ? `${Math.floor(activity.recoveryTimeInMinutes / 60)}h ${activity.recoveryTimeInMinutes % 60}m`
                            : `${activity.recoveryTimeInMinutes}m`}
                          color="green"
                        />
                      )}
                    </div>

                    {/* Training Effect Bar */}
                    {(teAerobic > 0 || teAnaerobic > 0) && (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        <p className="text-xs text-muted-foreground mb-2">Training Effect</p>
                        <div className="flex gap-4">
                          <div className="flex-1">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-green-500">Aerobic</span>
                              <span>{teAerobic.toFixed(1)}</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-green-500 rounded-full transition-all"
                                style={{ width: `${(teAerobic / 5) * 100}%` }}
                              />
                            </div>
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between text-xs mb-1">
                              <span className="text-yellow-500">Anaerobic</span>
                              <span>{teAnaerobic.toFixed(1)}</span>
                            </div>
                            <div className="h-2 bg-muted rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-yellow-500 rounded-full transition-all"
                                style={{ width: `${(teAnaerobic / 5) * 100}%` }}
                              />
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* AI Analysis Button */}
                    {showAnalysis && (
                      <div className="mt-4 pt-4 border-t border-border/50">
                        <button
                          onClick={(e) => handleAnalyze(e, activity.activityId)}
                          className={cn(
                            "w-full flex items-center justify-center gap-2 py-3 rounded-lg font-medium transition-all",
                            showingAnalysis 
                              ? "bg-primary/20 text-primary border border-primary/30" 
                              : "bg-gradient-to-r from-primary/10 to-purple-500/10 hover:from-primary/20 hover:to-purple-500/20 border border-primary/20"
                          )}
                        >
                          <Sparkles className="w-4 h-4" />
                          {showingAnalysis ? "Hide AI Analysis" : "Analyze with AI"}
                        </button>

                        {/* AI Analysis Results */}
                        <AnimatePresence>
                          {showingAnalysis && (
                            <ActivityAnalysis activityId={String(activity.activityId)} />
                          )}
                        </AnimatePresence>
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        )
      })}
    </div>
  )
}

function ActivityAnalysis({ activityId }: { activityId: string }) {
  const [isRegenerating, setIsRegenerating] = useState(false)
  const queryClient = useQueryClient()
  
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['activity-analysis', activityId],
    queryFn: () => aiAPI.analyzeActivity(activityId, false),
    staleTime: Infinity, // Always use cache since we save to DB
    retry: 1,
    refetchOnWindowFocus: false,
  })

  const handleRegenerate = async () => {
    setIsRegenerating(true)
    try {
      // Call the API with regenerate=true directly
      const newAnalysis = await aiAPI.analyzeActivity(activityId, true)
      // Update the cache with the new data
      queryClient.setQueryData(['activity-analysis', activityId], newAnalysis)
    } catch (error) {
      console.error('Failed to regenerate analysis:', error)
    } finally {
      setIsRegenerating(false)
    }
  }

  if (isLoading || isRegenerating) {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="mt-4 p-6 rounded-xl bg-gradient-to-br from-primary/5 to-purple-500/5 border border-primary/20"
      >
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-5 h-5 animate-spin text-primary" />
          <span className="text-muted-foreground">
            {isRegenerating ? "Regenerating analysis with AI..." : "Analyzing activity with AI..."}
          </span>
        </div>
      </motion.div>
    )
  }

  if (error) {
    return (
      <motion.div
        initial={{ opacity: 0, height: 0 }}
        animate={{ opacity: 1, height: 'auto' }}
        exit={{ opacity: 0, height: 0 }}
        className="mt-4 p-4 rounded-xl bg-red-500/10 border border-red-500/20"
      >
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-4 h-4" />
          <span>Failed to analyze activity. Please try again.</span>
        </div>
      </motion.div>
    )
  }

  if (!data?.analysis) return null

  const analysis = data.analysis
  const comparison = analysis.comparison_to_history

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="mt-4 space-y-4"
    >
      {/* Overall Score */}
      <div className="p-4 rounded-xl bg-gradient-to-br from-primary/10 to-purple-500/10 border border-primary/20">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className={cn(
                "w-12 h-12 rounded-full flex items-center justify-center text-lg font-bold",
                analysis.overall_score >= 80 ? "bg-green-500/20 text-green-500" :
                analysis.overall_score >= 60 ? "bg-yellow-500/20 text-yellow-500" :
                "bg-red-500/20 text-red-500"
              )}>
                {analysis.overall_score}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Overall Score</p>
                <p className={cn(
                  "font-semibold",
                  analysis.overall_score >= 80 ? "text-green-500" :
                  analysis.overall_score >= 60 ? "text-yellow-500" :
                  "text-red-500"
                )}>
                  {analysis.overall_rating}
                </p>
              </div>
            </div>
          </div>
          
          {/* Comparison Trend */}
          {comparison?.trend && comparison.trend !== "no_data" && (
            <div className={cn(
              "px-3 py-1.5 rounded-lg flex items-center gap-1.5 text-sm",
              comparison.trend === "improving" ? "bg-green-500/20 text-green-400" :
              comparison.trend === "declining" ? "bg-red-500/20 text-red-400" :
              "bg-muted text-muted-foreground"
            )}>
              {comparison.trend === "improving" ? <ArrowUpRight className="w-4 h-4" /> :
               comparison.trend === "declining" ? <ArrowDownRight className="w-4 h-4" /> :
               <Minus className="w-4 h-4" />}
              vs. history
            </div>
          )}
        </div>
        
        {/* One-liner */}
        <p className="mt-3 text-sm italic text-muted-foreground">
          "{analysis.one_liner}"
        </p>
      </div>

      {/* What Went Well */}
      {analysis.what_went_well && analysis.what_went_well.length > 0 && (
        <div className="p-4 rounded-xl bg-green-500/5 border border-green-500/20">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-green-400 mb-3">
            <CheckCircle className="w-4 h-4" />
            What Went Well
          </h4>
          <ul className="space-y-2">
            {analysis.what_went_well.map((item: any, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="text-green-500 mt-1">•</span>
                <div>
                  <span className="font-medium">{item.observation}</span>
                  {item.metric && (
                    <span className="ml-2 px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">
                      {item.metric}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* What Needs Improvement */}
      {analysis.what_needs_improvement && analysis.what_needs_improvement.length > 0 && (
        <div className="p-4 rounded-xl bg-yellow-500/5 border border-yellow-500/20">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-yellow-400 mb-3">
            <AlertTriangle className="w-4 h-4" />
            Areas for Improvement
          </h4>
          <ul className="space-y-3">
            {analysis.what_needs_improvement.map((item: any, i: number) => (
              <li key={i} className="text-sm">
                <div className="flex items-start gap-2">
                  <span className="text-yellow-500 mt-1">•</span>
                  <div>
                    <span className="font-medium">{item.observation}</span>
                    {item.metric && (
                      <span className="ml-2 px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400 text-xs">
                        {item.metric}
                      </span>
                    )}
                    {item.recommendation && (
                      <p className="text-muted-foreground mt-1">
                        <span className="text-yellow-400">→</span> {item.recommendation}
                      </p>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Key Takeaways */}
      {analysis.key_takeaways && analysis.key_takeaways.length > 0 && (
        <div className="p-4 rounded-xl bg-primary/5 border border-primary/20">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-primary mb-3">
            <Lightbulb className="w-4 h-4" />
            Key Takeaways
          </h4>
          <ul className="space-y-2">
            {analysis.key_takeaways.map((takeaway: string, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className="text-primary font-bold">{i + 1}.</span>
                <span>{takeaway}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Recommendations */}
      {analysis.recommendations_for_next_time && analysis.recommendations_for_next_time.length > 0 && (
        <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20">
          <h4 className="flex items-center gap-2 text-sm font-semibold text-blue-400 mb-3">
            <Target className="w-4 h-4" />
            Recommendations for Next Time
          </h4>
          <ul className="space-y-2">
            {analysis.recommendations_for_next_time.map((rec: any, i: number) => (
              <li key={i} className="flex items-start gap-2 text-sm">
                <span className={cn(
                  "mt-0.5 px-1.5 py-0.5 rounded text-xs font-medium",
                  rec.priority === "high" ? "bg-red-500/20 text-red-400" :
                  rec.priority === "medium" ? "bg-yellow-500/20 text-yellow-400" :
                  "bg-green-500/20 text-green-400"
                )}>
                  {rec.priority}
                </span>
                <div>
                  <span className="font-medium">{rec.action}</span>
                  {rec.expected_benefit && (
                    <p className="text-muted-foreground text-xs mt-0.5">
                      Expected: {rec.expected_benefit}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Training Effect Assessment */}
      {analysis.training_effect_assessment && (
        <div className="p-4 rounded-xl bg-muted/30 border border-border/50">
          <h4 className="flex items-center gap-2 text-sm font-semibold mb-3">
            <BarChart3 className="w-4 h-4 text-purple-400" />
            Training Effect Assessment
          </h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Aerobic</p>
              <p className={cn(
                "font-semibold",
                analysis.training_effect_assessment.aerobic_rating === "Excellent" ? "text-green-500" :
                analysis.training_effect_assessment.aerobic_rating === "Good" ? "text-blue-500" :
                "text-yellow-500"
              )}>
                {analysis.training_effect_assessment.aerobic_rating}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {analysis.training_effect_assessment.aerobic_insight}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground">Anaerobic</p>
              <p className={cn(
                "font-semibold",
                analysis.training_effect_assessment.anaerobic_rating === "Excellent" ? "text-green-500" :
                analysis.training_effect_assessment.anaerobic_rating === "Good" ? "text-blue-500" :
                analysis.training_effect_assessment.anaerobic_rating === "N/A" ? "text-muted-foreground" :
                "text-yellow-500"
              )}>
                {analysis.training_effect_assessment.anaerobic_rating}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {analysis.training_effect_assessment.anaerobic_insight}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recovery Suggestion */}
      {analysis.recovery_suggestion && (
        <div className="p-3 rounded-lg bg-muted/50 text-sm">
          <span className="font-medium">🛌 Recovery: </span>
          <span className="text-muted-foreground">{analysis.recovery_suggestion}</span>
        </div>
      )}

      {/* Generated info & Regenerate Button */}
      <div className="flex items-center justify-between mt-4 pt-3 border-t border-border/30">
        <p className="text-xs text-muted-foreground">
          {data.cached && (
            <span className="inline-flex items-center gap-1 mr-2 px-2 py-0.5 rounded bg-muted text-muted-foreground">
              Cached
            </span>
          )}
          Analyzed by {analysis.ai_model || 'AI'} • {data.comparison_activities_count || 0} similar activities compared
        </p>
        <button
          onClick={handleRegenerate}
          disabled={isRegenerating || isFetching}
          className={cn(
            "text-xs px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-all",
            "border border-primary/30 hover:bg-primary/10 text-primary",
            (isRegenerating || isFetching) && "opacity-50 cursor-not-allowed"
          )}
        >
          <RefreshCw className={cn("w-3 h-3", (isRegenerating || isFetching) && "animate-spin")} />
          {isRegenerating ? "Regenerating..." : "Regenerate"}
        </button>
      </div>
    </motion.div>
  )
}

function DetailItem({ 
  icon: Icon, 
  label, 
  value, 
  color,
  highlight = false
}: { 
  icon: React.ElementType
  label: string
  value: string
  color: 'primary' | 'green' | 'red' | 'orange' | 'purple' | 'blue' | 'cyan' | 'yellow'
  highlight?: boolean
}) {
  const colorClasses = {
    primary: 'text-primary',
    green: 'text-green-500',
    red: 'text-red-500',
    orange: 'text-orange-500',
    purple: 'text-purple-500',
    blue: 'text-blue-500',
    cyan: 'text-cyan-500',
    yellow: 'text-yellow-500',
  }

  return (
    <div className={cn(
      'p-3 rounded-lg bg-background/50',
      highlight && 'ring-1 ring-primary/30'
    )}>
      <div className="flex items-center gap-2 mb-1">
        <Icon className={cn('w-4 h-4', colorClasses[color])} />
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className={cn('font-semibold', highlight && colorClasses[color])}>{value}</p>
    </div>
  )
}
