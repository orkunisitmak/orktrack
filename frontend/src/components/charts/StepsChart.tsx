import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { formatNumber } from '@/lib/utils'

interface StepsChartProps {
  data: Array<{
    date: string
    steps: number
  }>
}

export default function StepsChart({ data }: StepsChartProps) {
  const chartData = data
    .slice()
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      steps: d.steps,
    }))

  if (chartData.length === 0) {
    return (
      <div className="h-[250px] flex items-center justify-center text-muted-foreground">
        No data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <AreaChart data={chartData}>
        <defs>
          <linearGradient id="stepsGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
            <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#333" vertical={false} />
        <XAxis
          dataKey="date"
          stroke="#666"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="#666"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          tickFormatter={(value) => `${(value / 1000).toFixed(0)}k`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a2e',
            border: '1px solid #333',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#888' }}
          formatter={(value: number) => [formatNumber(value), 'Steps']}
        />
        <Area
          type="monotone"
          dataKey="steps"
          stroke="#6366f1"
          strokeWidth={2}
          fill="url(#stepsGradient)"
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
