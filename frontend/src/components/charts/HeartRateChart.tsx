import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'

interface HeartRateChartProps {
  data: Array<{
    date: string
    resting_hr: number | null
  }>
}

export default function HeartRateChart({ data }: HeartRateChartProps) {
  const chartData = data
    .filter((d) => d.resting_hr !== null)
    .slice()
    .reverse()
    .map((d) => ({
      date: new Date(d.date).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      }),
      hr: d.resting_hr,
    }))

  if (chartData.length === 0) {
    return (
      <div className="h-[250px] flex items-center justify-center text-muted-foreground">
        No heart rate data available
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={250}>
      <LineChart data={chartData}>
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
          domain={['dataMin - 5', 'dataMax + 5']}
          tickFormatter={(value) => `${value}`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1a1a2e',
            border: '1px solid #333',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#888' }}
          formatter={(value: number) => [`${value} bpm`, 'Resting HR']}
        />
        <Line
          type="monotone"
          dataKey="hr"
          stroke="#ef4444"
          strokeWidth={2}
          dot={{ fill: '#ef4444', strokeWidth: 0, r: 4 }}
          activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2, fill: '#fff' }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
