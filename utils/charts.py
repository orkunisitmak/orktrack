"""Chart building utilities using Plotly."""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from config import CHART_COLORS, HR_ZONES, SLEEP_STAGES


class ChartBuilder:
    """Utility class for building Plotly charts with consistent styling."""
    
    # Dark theme template
    TEMPLATE = "plotly_dark"
    
    # Chart defaults
    DEFAULT_HEIGHT = 400
    DEFAULT_MARGIN = dict(l=40, r=40, t=60, b=40)
    
    @classmethod
    def _apply_theme(cls, fig: go.Figure, title: str = "") -> go.Figure:
        """Apply consistent dark theme to figure."""
        fig.update_layout(
            template=cls.TEMPLATE,
            title=dict(
                text=title,
                font=dict(size=18, color="#f8fafc"),
                x=0,
                xanchor="left"
            ),
            paper_bgcolor="rgba(26, 26, 46, 0.8)",
            plot_bgcolor="rgba(26, 26, 46, 0.5)",
            margin=cls.DEFAULT_MARGIN,
            font=dict(family="Outfit, sans-serif", color="#94a3b8"),
            legend=dict(
                bgcolor="rgba(26, 26, 46, 0.8)",
                bordercolor="rgba(51, 65, 85, 0.5)",
                borderwidth=1
            ),
            xaxis=dict(
                gridcolor="rgba(51, 65, 85, 0.3)",
                zerolinecolor="rgba(51, 65, 85, 0.5)"
            ),
            yaxis=dict(
                gridcolor="rgba(51, 65, 85, 0.3)",
                zerolinecolor="rgba(51, 65, 85, 0.5)"
            )
        )
        return fig
    
    @classmethod
    def activity_summary_chart(
        cls,
        data: pd.DataFrame,
        metric: str = "steps",
        title: str = "Activity Summary"
    ) -> go.Figure:
        """Create a bar chart for daily activity metrics."""
        fig = go.Figure()
        
        color_map = {
            "steps": CHART_COLORS["primary"],
            "calories": CHART_COLORS["accent"],
            "distance": CHART_COLORS["secondary"],
            "active_minutes": CHART_COLORS["info"],
        }
        
        fig.add_trace(go.Bar(
            x=data["date"],
            y=data[metric],
            marker_color=color_map.get(metric, CHART_COLORS["primary"]),
            marker_line_width=0,
            hovertemplate=f"<b>%{{x}}</b><br>{metric.replace('_', ' ').title()}: %{{y:,.0f}}<extra></extra>"
        ))
        
        # Add trend line
        if len(data) > 2:
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data[metric].rolling(7, min_periods=1).mean(),
                mode="lines",
                name="7-day avg",
                line=dict(color="#f8fafc", width=2, dash="dash"),
                hovertemplate="7-day avg: %{y:,.0f}<extra></extra>"
            ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=cls.DEFAULT_HEIGHT,
            showlegend=True,
            legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99)
        )
        
        return fig
    
    @classmethod
    def heart_rate_chart(
        cls,
        data: pd.DataFrame,
        title: str = "Heart Rate Trends"
    ) -> go.Figure:
        """Create a heart rate chart with zones."""
        fig = go.Figure()
        
        # Resting HR line
        if "resting_hr" in data.columns:
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data["resting_hr"],
                mode="lines+markers",
                name="Resting HR",
                line=dict(color=CHART_COLORS["info"], width=3),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>Resting HR: %{y} bpm<extra></extra>"
            ))
        
        # Max HR line
        if "max_hr" in data.columns:
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data["max_hr"],
                mode="lines+markers",
                name="Max HR",
                line=dict(color=CHART_COLORS["danger"], width=2),
                marker=dict(size=4),
                hovertemplate="<b>%{x}</b><br>Max HR: %{y} bpm<extra></extra>"
            ))
        
        # Average HR area
        if "avg_hr" in data.columns:
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data["avg_hr"],
                mode="lines",
                name="Avg HR",
                fill="tozeroy",
                line=dict(color=CHART_COLORS["primary"], width=2),
                fillcolor="rgba(99, 102, 241, 0.2)",
                hovertemplate="<b>%{x}</b><br>Avg HR: %{y} bpm<extra></extra>"
            ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=cls.DEFAULT_HEIGHT,
            yaxis_title="Heart Rate (bpm)",
            hovermode="x unified"
        )
        
        return fig
    
    @classmethod
    def hr_zones_donut(cls, zone_minutes: Dict[str, float], title: str = "HR Zones") -> go.Figure:
        """Create a donut chart for heart rate zone distribution."""
        labels = [HR_ZONES[zone]["name"] for zone in zone_minutes.keys()]
        values = list(zone_minutes.values())
        colors = [HR_ZONES[zone]["color"] for zone in zone_minutes.keys()]
        
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker_colors=colors,
            textinfo="percent",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>%{value:.0f} min (%{percent})<extra></extra>"
        )])
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=350,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        
        return fig
    
    @classmethod
    def sleep_chart(cls, data: pd.DataFrame, title: str = "Sleep Analysis") -> go.Figure:
        """Create a stacked bar chart for sleep stages."""
        fig = go.Figure()
        
        stages = ["deep", "light", "rem", "awake"]
        
        for stage in stages:
            if stage in data.columns:
                fig.add_trace(go.Bar(
                    x=data["date"],
                    y=data[stage],
                    name=SLEEP_STAGES[stage]["name"],
                    marker_color=SLEEP_STAGES[stage]["color"],
                    hovertemplate=f"<b>%{{x}}</b><br>{SLEEP_STAGES[stage]['name']}: %{{y:.1f}} hrs<extra></extra>"
                ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=cls.DEFAULT_HEIGHT,
            barmode="stack",
            yaxis_title="Hours",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        
        return fig
    
    @classmethod
    def sleep_score_gauge(cls, score: float, title: str = "Sleep Score") -> go.Figure:
        """Create a gauge chart for sleep score."""
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=score,
            domain=dict(x=[0, 1], y=[0, 1]),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor="#94a3b8"),
                bar=dict(color=CHART_COLORS["primary"]),
                bgcolor="rgba(26, 26, 46, 0.5)",
                borderwidth=0,
                steps=[
                    dict(range=[0, 40], color="rgba(239, 68, 68, 0.3)"),
                    dict(range=[40, 70], color="rgba(245, 158, 11, 0.3)"),
                    dict(range=[70, 100], color="rgba(34, 197, 94, 0.3)")
                ],
                threshold=dict(
                    line=dict(color="#f8fafc", width=2),
                    thickness=0.75,
                    value=score
                )
            ),
            number=dict(font=dict(size=40, color="#f8fafc"))
        ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(height=250)
        
        return fig
    
    @classmethod
    def stress_chart(cls, data: pd.DataFrame, title: str = "Stress Levels") -> go.Figure:
        """Create an area chart for stress levels."""
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=data["date"],
            y=data["stress"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=CHART_COLORS["accent"], width=2),
            fillcolor="rgba(245, 158, 11, 0.2)",
            hovertemplate="<b>%{x}</b><br>Stress: %{y}<extra></extra>"
        ))
        
        # Add threshold lines
        fig.add_hline(y=25, line_dash="dash", line_color="rgba(34, 197, 94, 0.5)",
                      annotation_text="Low", annotation_position="right")
        fig.add_hline(y=50, line_dash="dash", line_color="rgba(245, 158, 11, 0.5)",
                      annotation_text="Medium", annotation_position="right")
        fig.add_hline(y=75, line_dash="dash", line_color="rgba(239, 68, 68, 0.5)",
                      annotation_text="High", annotation_position="right")
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=cls.DEFAULT_HEIGHT,
            yaxis=dict(range=[0, 100], title="Stress Level"),
        )
        
        return fig
    
    @classmethod
    def activity_breakdown_pie(
        cls,
        activities: Dict[str, int],
        title: str = "Activity Types"
    ) -> go.Figure:
        """Create a pie chart for activity type breakdown."""
        fig = go.Figure(data=[go.Pie(
            labels=list(activities.keys()),
            values=list(activities.values()),
            hole=0.4,
            marker_colors=px.colors.qualitative.Set2,
            textinfo="label+percent",
            textposition="outside",
            hovertemplate="<b>%{label}</b><br>%{value} activities (%{percent})<extra></extra>"
        )])
        
        cls._apply_theme(fig, title)
        fig.update_layout(height=350)
        
        return fig
    
    @classmethod
    def weekly_comparison(
        cls,
        current_week: Dict[str, float],
        previous_week: Dict[str, float],
        title: str = "Week-over-Week Comparison"
    ) -> go.Figure:
        """Create a grouped bar chart comparing two weeks."""
        metrics = list(current_week.keys())
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            name="This Week",
            x=metrics,
            y=list(current_week.values()),
            marker_color=CHART_COLORS["primary"]
        ))
        
        fig.add_trace(go.Bar(
            name="Last Week",
            x=metrics,
            y=list(previous_week.values()),
            marker_color=CHART_COLORS["muted"]
        ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=cls.DEFAULT_HEIGHT,
            barmode="group",
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        
        return fig
    
    @classmethod
    def training_load_chart(
        cls,
        data: pd.DataFrame,
        title: str = "Training Load"
    ) -> go.Figure:
        """Create a combined chart showing training load and recovery."""
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.6, 0.4],
            subplot_titles=("Training Load", "Recovery Score")
        )
        
        # Training load bars
        fig.add_trace(go.Bar(
            x=data["date"],
            y=data.get("training_load", data.get("calories", [])),
            marker_color=CHART_COLORS["primary"],
            name="Training Load",
            hovertemplate="<b>%{x}</b><br>Load: %{y}<extra></extra>"
        ), row=1, col=1)
        
        # Recovery line
        if "recovery" in data.columns:
            fig.add_trace(go.Scatter(
                x=data["date"],
                y=data["recovery"],
                mode="lines+markers",
                name="Recovery",
                line=dict(color=CHART_COLORS["secondary"], width=2),
                marker=dict(size=6),
                hovertemplate="<b>%{x}</b><br>Recovery: %{y}%<extra></extra>"
            ), row=2, col=1)
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=500,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.05)
        )
        
        return fig
    
    @classmethod
    def calendar_heatmap(
        cls,
        data: pd.DataFrame,
        metric: str = "steps",
        title: str = "Activity Calendar"
    ) -> go.Figure:
        """Create a calendar heatmap for activity data."""
        # Prepare data
        df = data.copy()
        df["date"] = pd.to_datetime(df["date"])
        df["week"] = df["date"].dt.isocalendar().week
        df["day"] = df["date"].dt.dayofweek
        df["day_name"] = df["date"].dt.day_name()
        
        # Create pivot table
        pivot = df.pivot_table(index="day", columns="week", values=metric, aggfunc="mean")
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
            colorscale=[
                [0, "rgba(26, 26, 46, 0.5)"],
                [0.5, "rgba(99, 102, 241, 0.5)"],
                [1, "rgba(99, 102, 241, 1)"]
            ],
            hovertemplate="Week %{x}<br>%{y}<br>%{z:,.0f}<extra></extra>"
        ))
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=250,
            xaxis_title="Week",
            yaxis=dict(autorange="reversed")
        )
        
        return fig
    
    @classmethod
    def goal_progress_chart(
        cls,
        goals: List[Dict[str, Any]],
        title: str = "Goal Progress"
    ) -> go.Figure:
        """Create a horizontal bar chart for goal progress."""
        fig = go.Figure()
        
        names = [g["name"] for g in goals]
        progress = [min(g["current"] / g["target"] * 100, 100) for g in goals]
        colors = [
            CHART_COLORS["success"] if p >= 100 
            else CHART_COLORS["primary"] if p >= 50 
            else CHART_COLORS["warning"] 
            for p in progress
        ]
        
        fig.add_trace(go.Bar(
            y=names,
            x=progress,
            orientation="h",
            marker_color=colors,
            text=[f"{p:.0f}%" for p in progress],
            textposition="auto",
            hovertemplate="<b>%{y}</b><br>Progress: %{x:.1f}%<extra></extra>"
        ))
        
        # Add target line
        fig.add_vline(x=100, line_dash="dash", line_color="#f8fafc", line_width=2)
        
        cls._apply_theme(fig, title)
        fig.update_layout(
            height=max(200, len(goals) * 50),
            xaxis=dict(range=[0, 110], title="Progress (%)"),
        )
        
        return fig
