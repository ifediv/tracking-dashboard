"""Chart generation module for analytics dashboard.

Creates terminal-themed Plotly visualizations inspired by Dune.xyz aesthetics.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.models import Trade, DrawdownAnalysis

# Terminal color scheme
COLORS = {
    'bg': '#0a1612',
    'bg_light': '#0d1f1a',
    'matrix_green': '#00ff41',
    'matrix_green_dim': '#00b82e',
    'terminal_blue': '#1e90ff',
    'terminal_gray': '#2a3f38',
    'text_primary': '#e0e0e0',
    'text_secondary': '#a0a0a0',
    'profit': '#00ff41',
    'loss': '#ff4444',
    'warning': '#ffaa00',
}

def get_plotly_layout(**kwargs) -> dict:
    """Get standard terminal-themed layout for Plotly charts."""
    default_layout = {
        'plot_bgcolor': COLORS['bg_light'],
        'paper_bgcolor': COLORS['bg'],
        'font': {
            'family': 'Courier New, monospace',
            'color': COLORS['text_primary'],
            'size': 12
        },
        'title': {
            'font': {
                'family': 'Courier New, monospace',
                'color': COLORS['matrix_green'],
                'size': 16
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        'xaxis': {
            'gridcolor': COLORS['terminal_gray'],
            'linecolor': COLORS['matrix_green'],
            'tickfont': {'color': COLORS['text_secondary']},
            'title': {'font': {'color': COLORS['matrix_green']}}
        },
        'yaxis': {
            'gridcolor': COLORS['terminal_gray'],
            'linecolor': COLORS['matrix_green'],
            'tickfont': {'color': COLORS['text_secondary']},
            'title': {'font': {'color': COLORS['matrix_green']}}
        },
        'hoverlabel': {
            'bgcolor': COLORS['bg_light'],
            'font': {'family': 'Courier New, monospace', 'color': COLORS['text_primary']},
            'bordercolor': COLORS['matrix_green']
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
    }
    default_layout.update(kwargs)
    return default_layout


def create_strategy_heatmap(session: Session) -> go.Figure:
    """Create heatmap showing average drawdown by strategy and timeframe.

    Args:
        session: Database session

    Returns:
        Plotly figure with heatmap
    """
    # Query data: strategy x timeframe → avg drawdown
    query = session.query(
        Trade.strategy_type,
        DrawdownAnalysis.timeframe_minutes,
        func.avg(DrawdownAnalysis.max_drawdown_pct).label('avg_drawdown'),
        func.count(DrawdownAnalysis.analysis_id).label('trade_count')
    ).join(
        DrawdownAnalysis, Trade.trade_id == DrawdownAnalysis.trade_id
    ).group_by(
        Trade.strategy_type,
        DrawdownAnalysis.timeframe_minutes
    ).all()

    if not query:
        # Return empty heatmap
        fig = go.Figure()
        fig.update_layout(**get_plotly_layout(title="[NO DATA] Strategy Heatmap"))
        return fig

    # Create pivot table
    df = pd.DataFrame(query, columns=['strategy', 'timeframe', 'avg_drawdown', 'count'])
    pivot = df.pivot(index='strategy', columns='timeframe', values='avg_drawdown')
    count_pivot = df.pivot(index='strategy', columns='timeframe', values='count')

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"{int(t)}min" for t in pivot.columns],
        y=pivot.index,
        colorscale=[
            [0, COLORS['loss']],      # Red for bad (high drawdown)
            [0.5, COLORS['warning']],  # Yellow for medium
            [1, COLORS['profit']]      # Green for good (low drawdown)
        ],
        text=count_pivot.values,
        texttemplate='%{z:.1f}%<br>n=%{text}',
        textfont={'size': 10, 'color': COLORS['text_primary']},
        colorbar={
            'title': {
                'text': 'Avg DD%',
                'font': {'color': COLORS['matrix_green']}
            },
            'tickfont': {'color': COLORS['text_secondary']}
        },
        hovertemplate='<b>%{y}</b><br>Timeframe: %{x}<br>Avg Drawdown: %{z:.2f}%<br>Trades: %{text}<extra></extra>'
    ))

    fig.update_layout(**get_plotly_layout(
        title="[STRATEGY HEATMAP] Average Max Drawdown by Timeframe",
        xaxis_title="Timeframe",
        yaxis_title="Strategy",
        height=max(400, len(pivot.index) * 50)
    ))

    return fig


def create_pnl_calendar(session: Session, year: int, month: int) -> go.Figure:
    """Create interactive calendar heatmap showing daily P&L.

    Args:
        session: Database session
        year: Year to display
        month: Month to display (1-12)

    Returns:
        Plotly figure with calendar heatmap
    """
    # Get all trades for the month
    from sqlalchemy import func, extract
    import calendar as cal

    trades = session.query(
        func.date(Trade.entry_timestamp).label('date'),
        func.sum(Trade.net_pnl).label('daily_pnl'),
        func.count(Trade.trade_id).label('trade_count')
    ).filter(
        extract('year', Trade.entry_timestamp) == year,
        extract('month', Trade.entry_timestamp) == month
    ).group_by(
        func.date(Trade.entry_timestamp)
    ).all()

    # Create DataFrame
    df = pd.DataFrame(trades, columns=['date', 'pnl', 'count']) if trades else pd.DataFrame(columns=['date', 'pnl', 'count'])
    if len(df) > 0:
        df['date'] = pd.to_datetime(df['date'])

    # Create calendar grid (7 columns for weekdays)
    month_cal = cal.monthcalendar(year, month)

    # Get current date for comparison
    from datetime import date as dt_date
    today = dt_date.today()

    # Prepare data for heatmap
    z_data = []
    text_data = []
    hover_data = []
    customdata = []  # For day numbers

    for week in month_cal:
        week_pnl = []
        week_text = []
        week_hover = []
        week_custom = []

        for day_idx, day in enumerate(week):
            if day == 0:
                # Empty cell for days outside the month
                week_pnl.append(None)
                week_text.append("")
                week_hover.append("")
                week_custom.append("")
            else:
                date_obj = datetime(year, month, day)
                day_data = df[df['date'] == date_obj] if len(df) > 0 else pd.DataFrame()

                # Check if this is a weekend (Saturday=5, Sunday=6)
                is_weekend = day_idx >= 5

                # Check if date is in the future
                is_future = date_obj.date() > today

                if len(day_data) > 0:
                    # Has trading data
                    pnl = day_data['pnl'].iloc[0]
                    count = day_data['count'].iloc[0]
                    week_pnl.append(pnl)
                    week_text.append(f"{day}<br>${pnl:.0f}")
                    week_hover.append(f"Date: {date_obj.strftime('%Y-%m-%d')}<br>P&L: ${pnl:.2f}<br>Trades: {count}")
                elif is_future:
                    # Future date - use None to not show color
                    week_pnl.append(None)
                    week_text.append(f"{day}")
                    week_hover.append(f"Date: {date_obj.strftime('%Y-%m-%d')}<br>Future date")
                elif is_weekend:
                    # Weekend with no trades - grey
                    week_pnl.append(0)
                    week_text.append(f"{day}")
                    week_hover.append(f"Date: {date_obj.strftime('%Y-%m-%d')}<br>Weekend - No trades")
                else:
                    # Weekday with no trades
                    week_pnl.append(0)
                    week_text.append(f"{day}")
                    week_hover.append(f"Date: {date_obj.strftime('%Y-%m-%d')}<br>No trades")

                week_custom.append(f"{year}-{month:02d}-{day:02d}")

        z_data.append(week_pnl)
        text_data.append(week_text)
        hover_data.append(week_hover)
        customdata.append(week_custom)

    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        text=text_data,
        hovertext=hover_data,
        customdata=customdata,
        hovertemplate='%{hovertext}<extra></extra>',
        x=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        y=[f"Week {i+1}" for i in range(len(z_data))],
        colorscale=[
            [0, COLORS['loss']],
            [0.5, COLORS['terminal_gray']],
            [1, COLORS['profit']]
        ],
        texttemplate='%{text}',
        textfont={'size': 10, 'color': COLORS['text_primary']},
        colorbar={
            'title': {
                'text': 'Daily P&L',
                'font': {'color': COLORS['matrix_green']}
            },
            'tickfont': {'color': COLORS['text_secondary']},
            'tickprefix': '$'
        },
        xgap=3,  # Gap between cells horizontally
        ygap=3   # Gap between cells vertically
    ))

    month_name = cal.month_name[month]
    fig.update_layout(**get_plotly_layout(
        title=f"[PNL CALENDAR] {month_name} {year}",
        xaxis={'side': 'top'},
        height=400,
        yaxis={'autorange': 'reversed'}  # Week 1 at top
    ))

    return fig


def create_entry_quality_scatter(session: Session, strategy_type: Optional[str] = None) -> go.Figure:
    """Scatter plot: early drawdown vs final P&L.

    Args:
        session: Database session
        strategy_type: Optional strategy filter

    Returns:
        Plotly scatter plot
    """
    # Query: get 5min drawdown and final P&L for each trade
    query = session.query(
        Trade.trade_id,
        Trade.symbol,
        Trade.strategy_type,
        Trade.net_pnl,
        DrawdownAnalysis.max_drawdown_pct
    ).join(
        DrawdownAnalysis, Trade.trade_id == DrawdownAnalysis.trade_id
    ).filter(
        DrawdownAnalysis.timeframe_minutes == 5
    )

    if strategy_type:
        query = query.filter(Trade.strategy_type == strategy_type)

    results = query.all()

    if not results:
        fig = go.Figure()
        fig.update_layout(**get_plotly_layout(title="[NO DATA] Entry Quality Analysis"))
        return fig

    df = pd.DataFrame(results, columns=['trade_id', 'symbol', 'strategy', 'pnl', 'drawdown_5min'])

    # Color by win/loss
    df['color'] = df['pnl'].apply(lambda x: COLORS['profit'] if x > 0 else COLORS['loss'])
    df['result'] = df['pnl'].apply(lambda x: 'WIN' if x > 0 else 'LOSS')

    fig = go.Figure()

    for result, color in [('WIN', COLORS['profit']), ('LOSS', COLORS['loss'])]:
        subset = df[df['result'] == result]
        fig.add_trace(go.Scatter(
            x=subset['drawdown_5min'],
            y=subset['pnl'],
            mode='markers',
            name=result,
            marker={
                'color': color,
                'size': 8,
                'line': {'color': COLORS['matrix_green'], 'width': 1}
            },
            hovertemplate='<b>%{text}</b><br>5min DD: %{x:.2f}%<br>Final P&L: $%{y:.2f}<extra></extra>',
            text=subset['symbol']
        ))

    fig.update_layout(**get_plotly_layout(
        title="[ENTRY QUALITY] Early Drawdown vs Final P&L",
        xaxis_title="Max Drawdown at 5min (%)",
        yaxis_title="Final Net P&L ($)",
        showlegend=True,
        height=500
    ))

    return fig


def create_hold_time_curve(session: Session, strategy_type: str) -> go.Figure:
    """Line chart showing P&L evolution across timeframes.

    Args:
        session: Database session
        strategy_type: Strategy to analyze

    Returns:
        Plotly line chart
    """
    from sqlalchemy import func

    # Get average P&L at each timeframe for this strategy
    query = session.query(
        DrawdownAnalysis.timeframe_minutes,
        func.avg(DrawdownAnalysis.unrealized_pnl_at_timeframe).label('avg_pnl'),
        func.count(DrawdownAnalysis.analysis_id).label('count')
    ).join(
        Trade, DrawdownAnalysis.trade_id == Trade.trade_id
    ).filter(
        Trade.strategy_type == strategy_type
    ).group_by(
        DrawdownAnalysis.timeframe_minutes
    ).order_by(
        DrawdownAnalysis.timeframe_minutes
    ).all()

    if not query:
        fig = go.Figure()
        fig.update_layout(**get_plotly_layout(title=f"[NO DATA] {strategy_type}"))
        return fig

    df = pd.DataFrame(query, columns=['timeframe', 'avg_pnl', 'count'])

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['timeframe'],
        y=df['avg_pnl'],
        mode='lines+markers',
        name='Avg P&L',
        line={'color': COLORS['matrix_green'], 'width': 3},
        marker={'size': 10, 'color': COLORS['terminal_blue']},
        hovertemplate='<b>%{x}min</b><br>Avg P&L: $%{y:.2f}<extra></extra>'
    ))

    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color=COLORS['text_secondary'], opacity=0.5)

    # Find peak
    peak_idx = df['avg_pnl'].idxmax()
    peak_time = df.loc[peak_idx, 'timeframe']
    peak_pnl = df.loc[peak_idx, 'avg_pnl']

    fig.add_annotation(
        x=peak_time,
        y=peak_pnl,
        text=f"PEAK: {peak_time}min<br>${peak_pnl:.2f}",
        showarrow=True,
        arrowhead=2,
        arrowcolor=COLORS['warning'],
        font={'color': COLORS['warning']}
    )

    fig.update_layout(**get_plotly_layout(
        title=f"[HOLD TIME ANALYSIS] {strategy_type.upper()}",
        xaxis_title="Time Held (minutes)",
        yaxis_title="Average P&L ($)",
        height=500
    ))

    return fig


def create_daily_pnl_chart(trades: List[Trade], strategy_filter: Optional[str] = None) -> go.Figure:
    """Create cumulative P&L chart showing performance throughout the trading day.

    Each day starts at $0. Chart shows how P&L evolves over time as trades are executed.
    Designed for extensibility - can add multiple lines for comparisons in future.

    Args:
        trades: List of Trade objects (should already be filtered by date/symbol)
        strategy_filter: Optional strategy type to filter by (None = all strategies)

    Returns:
        Plotly line chart with cumulative P&L over time
    """
    from datetime import datetime

    # Filter by strategy if specified
    if strategy_filter and strategy_filter != "All Strategies":
        trades = [t for t in trades if t.strategy_type == strategy_filter]

    if not trades:
        # Return empty chart with message
        fig = go.Figure()
        fig.update_layout(**get_plotly_layout(
            title="[NO DATA] Daily P&L Performance",
            xaxis_title="Time of Day",
            yaxis_title="Cumulative P&L ($)"
        ))
        fig.add_annotation(
            text="No trades found for selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font={'size': 14, 'color': COLORS['text_secondary']}
        )
        return fig

    # Parse timestamps and sort by entry time
    trade_data = []
    for trade in trades:
        # Parse ISO timestamp: 2025-10-02T09:03:21
        dt = datetime.fromisoformat(trade.entry_timestamp)
        time_str = dt.strftime('%H:%M:%S')  # e.g., "09:03:21"
        trade_data.append({
            'time': dt.time(),
            'time_str': time_str,
            'datetime': dt,
            'pnl': trade.net_pnl,
            'symbol': trade.symbol,
            'strategy': trade.strategy_type
        })

    # Sort by time
    trade_data.sort(key=lambda x: x['datetime'])

    # Calculate cumulative P&L starting from 0
    cumulative_pnl = 0
    times = []
    pnl_values = []
    hover_texts = []
    trade_counts = []

    for i, td in enumerate(trade_data):
        cumulative_pnl += td['pnl']
        times.append(td['time_str'])
        pnl_values.append(cumulative_pnl)
        trade_counts.append(i + 1)

        # Hover text
        hover_texts.append(
            f"<b>{td['time_str']}</b><br>"
            f"Trade #{i+1}: {td['symbol']} ({td['strategy']})<br>"
            f"Trade P&L: ${td['pnl']:,.2f}<br>"
            f"<b>Cumulative: ${cumulative_pnl:,.2f}</b>"
        )

    # Create figure
    fig = go.Figure()

    # Determine line color based on final P&L
    final_pnl = pnl_values[-1] if pnl_values else 0
    line_color = COLORS['profit'] if final_pnl >= 0 else COLORS['loss']

    # Add cumulative P&L line
    fig.add_trace(go.Scatter(
        x=times,
        y=pnl_values,
        mode='lines+markers',
        name='Cumulative P&L',
        line={'color': line_color, 'width': 3},
        marker={'size': 8, 'color': COLORS['terminal_blue']},
        hovertext=hover_texts,
        hoverinfo='text'
    ))

    # Add zero reference line
    fig.add_hline(
        y=0,
        line_dash="dash",
        line_color=COLORS['text_secondary'],
        opacity=0.5,
        annotation_text="Breakeven",
        annotation_position="right",
        annotation_font={'color': COLORS['text_secondary'], 'size': 10}
    )

    # Add shaded regions for profit/loss zones
    if pnl_values:
        # Profit zone (green)
        fig.add_hrect(
            y0=0, y1=max(pnl_values) if max(pnl_values) > 0 else 100,
            fillcolor=COLORS['profit'],
            opacity=0.1,
            layer="below",
            line_width=0
        )

        # Loss zone (red)
        fig.add_hrect(
            y0=min(pnl_values) if min(pnl_values) < 0 else -100, y1=0,
            fillcolor=COLORS['loss'],
            opacity=0.1,
            layer="below",
            line_width=0
        )

    # Build title
    title_text = "[DAILY PNL] Cumulative Performance"
    if strategy_filter and strategy_filter != "All Strategies":
        title_text += f" - {strategy_filter.upper()}"

    # Final P&L annotation
    if pnl_values:
        annotation_color = COLORS['profit'] if final_pnl >= 0 else COLORS['loss']
        fig.add_annotation(
            x=times[-1],
            y=pnl_values[-1],
            text=f"Final: ${final_pnl:,.2f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=annotation_color,
            font={'color': annotation_color, 'size': 12, 'family': 'Courier New'}
        )

    fig.update_layout(**get_plotly_layout(
        title=title_text,
        xaxis_title="Time of Day",
        yaxis_title="Cumulative P&L ($)",
        height=450,
        showlegend=False
    ))

    # Format x-axis to show fewer labels for readability
    fig.update_xaxes(tickangle=-45)

    return fig


def create_opportunity_cost_chart(
    daily_data: List,
    bp_changes: List[Dict]
) -> go.Figure:
    """Create equity curve comparing Trader vs SPY performance.

    Args:
        daily_data: List of DailyPerformance objects from OpportunityCostCalculator
        bp_changes: List of dicts with buying power changes {'date', 'amount', 'notes'}

    Returns:
        Plotly figure with dual equity curves

    Example:
        >>> from src.analysis.opportunity_cost import OpportunityCostCalculator
        >>> calc = OpportunityCostCalculator(session)
        >>> daily_data = calc.build_daily_timeline()
        >>> bp_changes = calc.get_buying_power_changes()
        >>> fig = create_opportunity_cost_chart(daily_data, bp_changes)
    """
    if not daily_data:
        fig = go.Figure()
        fig.update_layout(**get_plotly_layout(title="[NO DATA] Opportunity Cost Analysis"))
        return fig

    # Extract data
    dates = [d.date for d in daily_data]
    trader_cumulative = [d.trader_cumulative_pnl for d in daily_data]
    spy_cumulative = [d.spy_cumulative_pnl for d in daily_data]

    fig = go.Figure()

    # Add Trader equity curve
    fig.add_trace(go.Scatter(
        x=dates,
        y=trader_cumulative,
        mode='lines',
        name='Active Trading',
        line={'color': COLORS['matrix_green'], 'width': 3},
        fill='tonexty',
        fillcolor=f"rgba(0, 255, 65, 0.1)",
        hovertemplate='<b>%{x}</b><br>Trader P&L: $%{y:,.2f}<extra></extra>'
    ))

    # Add SPY equity curve
    fig.add_trace(go.Scatter(
        x=dates,
        y=spy_cumulative,
        mode='lines',
        name='Passive SPY',
        line={'color': COLORS['terminal_blue'], 'width': 3, 'dash': 'dash'},
        hovertemplate='<b>%{x}</b><br>SPY P&L: $%{y:,.2f}<extra></extra>'
    ))

    # Add zero reference line
    fig.add_hline(
        y=0,
        line_dash="dot",
        line_color=COLORS['text_secondary'],
        opacity=0.5,
        annotation_text="Breakeven",
        annotation_position="right"
    )

    # Add vertical lines for buying power changes
    for bp_change in bp_changes:
        if bp_change['date'] in dates:
            fig.add_vline(
                x=bp_change['date'],
                line_dash="dash",
                line_color=COLORS['warning'],
                opacity=0.6,
                annotation_text=f"BP: ${bp_change['amount']/1000:.0f}K",
                annotation_position="top",
                annotation_font={'size': 9, 'color': COLORS['warning']}
            )

    # Final values annotation
    if daily_data:
        final_trader = trader_cumulative[-1]
        final_spy = spy_cumulative[-1]
        outperformance = final_trader - final_spy

        annotation_y = max(final_trader, final_spy)
        annotation_color = COLORS['profit'] if outperformance > 0 else COLORS['loss']

        fig.add_annotation(
            x=dates[-1],
            y=annotation_y,
            text=f"Outperformance: ${outperformance:,.0f}",
            showarrow=True,
            arrowhead=2,
            arrowcolor=annotation_color,
            font={'color': annotation_color, 'size': 12, 'family': 'Courier New'},
            yshift=20
        )

    fig.update_layout(**get_plotly_layout(
        title="[OPPORTUNITY COST] Active Trading vs Passive SPY Investment",
        xaxis_title="Date",
        yaxis_title="Cumulative P&L ($)",
        height=600,
        showlegend=True,
        legend={
            'bgcolor': COLORS['bg_light'],
            'bordercolor': COLORS['matrix_green'],
            'borderwidth': 1,
            'font': {'color': COLORS['text_primary']}
        },
        hovermode='x unified'
    ))

    # Format y-axis with dollar signs
    fig.update_yaxes(tickprefix='$', tickformat=',.0f')

    return fig


