"""Analytics dashboard for trading performance visualization."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

# Set page config FIRST
st.set_page_config(
    page_title="Analytics - Trading Analytics",
    page_icon="▓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.operations import get_all_trades, get_analysis_for_trade
from src.database.models import DrawdownAnalysis
from src.utils.config import config

# Apply terminal-style theme (same as other pages)
st.markdown("""
    <style>
    /* Terminal Color Palette */
    :root {
        --terminal-bg: #0a1612;
        --terminal-bg-light: #0d1f1a;
        --matrix-green: #00ff41;
        --matrix-green-dim: #00b82e;
        --terminal-blue: #1e90ff;
        --terminal-gray: #2a3f38;
        --text-primary: #e0e0e0;
        --text-secondary: #a0a0a0;
    }

    .stApp {
        background-color: var(--terminal-bg) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Header Area */
    header[data-testid="stHeader"] {
        background-color: var(--terminal-bg) !important;
    }

    /* Sidebar Styling - Force dark background */
    [data-testid="stSidebar"] {
        background-color: var(--terminal-bg-light) !important;
        border-right: 2px solid var(--terminal-gray) !important;
    }

    [data-testid="stSidebar"] > div:first-child {
        background-color: var(--terminal-bg-light) !important;
    }

    [data-testid="stSidebar"] * {
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: var(--terminal-bg-light) !important;
    }

    /* Sidebar Navigation Links */
    [data-testid="stSidebarNav"] {
        background-color: var(--terminal-bg-light) !important;
        padding-top: 1rem;
    }

    [data-testid="stSidebarNav"] ul {
        padding: 0.5rem;
    }

    [data-testid="stSidebarNav"] li {
        background-color: var(--terminal-bg) !important;
        border: 1px solid var(--terminal-gray) !important;
        border-radius: 4px;
        margin-bottom: 0.5rem;
        transition: all 0.2s;
    }

    [data-testid="stSidebarNav"] li:hover {
        border-color: var(--matrix-green) !important;
        background-color: var(--terminal-bg-light) !important;
        box-shadow: 0 0 8px rgba(0, 255, 65, 0.3);
    }

    [data-testid="stSidebarNav"] li a {
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.9rem;
        padding: 0.5rem 0.75rem;
    }

    [data-testid="stSidebarNav"] li[aria-selected="true"] {
        background-color: var(--terminal-gray) !important;
        border-color: var(--matrix-green) !important;
        border-left-width: 4px;
    }

    [data-testid="stSidebarNav"] li[aria-selected="true"] a {
        color: var(--matrix-green) !important;
        font-weight: bold;
    }

    [data-testid="stSidebarNav"] li span {
        color: var(--text-primary) !important;
    }

    h1, h2, h3 {
        color: var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

    /* Buttons */
    .stButton > button {
        background-color: var(--terminal-bg-light);
        color: var(--matrix-green);
        border: 2px solid var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton > button:hover {
        background-color: var(--matrix-green);
        color: var(--terminal-bg);
        border-color: var(--matrix-green);
    }

    /* Selectbox styling */
    [data-baseweb="select"] {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    [data-baseweb="select"] > div {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Plotly chart background */
    .js-plotly-plot {
        background-color: var(--terminal-bg-light) !important;
    }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-weight: bold;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--terminal-bg-light);
        border-bottom: 2px solid var(--terminal-gray);
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-weight: bold;
        text-transform: uppercase;
    }

    .stTabs [aria-selected="true"] {
        color: var(--matrix-green);
        border-bottom-color: var(--matrix-green);
    }

    /* MultiSelect Styling */
    [data-baseweb="tag"] {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        border: 1px solid var(--matrix-green) !important;
    }

    .stMultiSelect > div > div {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Date Input Styling */
    .stDateInput > div > div > input {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Calendar popup */
    [data-baseweb="calendar"] {
        background-color: var(--terminal-bg-light) !important;
        border: 2px solid var(--matrix-green) !important;
    }

    [data-baseweb="calendar"] * {
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# >>> ANALYTICS DASHBOARD")
st.markdown("Advanced performance analysis and optimization insights")

st.divider()

# Load data
try:
    with get_session() as session:
        all_trades = get_all_trades(session)

        if not all_trades:
            st.warning("[WARN] No trades found. Import trades to view analytics.")
            st.stop()

        # Get trades with analysis
        trades_with_analysis = []
        for trade in all_trades:
            analysis = get_analysis_for_trade(session, trade.trade_id)
            if analysis:
                trades_with_analysis.append(trade)

        total_trades = len(all_trades)
        analyzed_trades = len(trades_with_analysis)

        # Calculate metrics (works with or without analysis)
        total_pnl = sum(t.net_pnl for t in all_trades)
        winning_trades = sum(1 for t in all_trades if t.net_pnl > 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

        # Strategy performance
        strategy_pnl = {}
        strategy_counts = {}
        for trade in all_trades:
            strat = trade.strategy_type
            strategy_pnl[strat] = strategy_pnl.get(strat, 0) + trade.net_pnl
            strategy_counts[strat] = strategy_counts.get(strat, 0) + 1

        best_strategy = max(strategy_pnl.items(), key=lambda x: x[1])[0] if strategy_pnl else "N/A"
        worst_strategy = min(strategy_pnl.items(), key=lambda x: x[1])[0] if strategy_pnl else "N/A"

        # Sharpe ratio (proper calculation)
        # Sharpe = (Mean Return - Risk Free Rate) / Std Dev
        # Using risk-free rate of 0 for simplicity (can adjust to current T-bill rate ~4-5%)
        if total_trades > 1:
            pnl_list = [t.net_pnl for t in all_trades]
            avg = sum(pnl_list) / len(pnl_list)

            # Use sample standard deviation (n-1 denominator) for better estimate
            variance = sum((x - avg) ** 2 for x in pnl_list) / (len(pnl_list) - 1)
            std_dev = variance ** 0.5

            # Sharpe ratio: (mean - risk_free_rate) / std_dev
            # Assuming risk-free rate = 0 for per-trade Sharpe
            sharpe = (avg / std_dev) if std_dev > 0 else 0

            # Note: This is per-trade Sharpe, not annualized
            # To annualize: multiply by sqrt(trading_days_per_year)
        else:
            sharpe = 0

except Exception as e:
    st.error(f"[ERROR] Failed to load data: {str(e)}")
    st.stop()

# Summary Metrics
st.markdown("## [SYSTEM STATUS]")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">TOTAL TRADES</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{total_trades}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1rem;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">WIN RATE</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{win_rate:.1f}%</div>
        <div style="color: #a0a0a0; font-size: 0.9rem; margin-top: 0.2rem;">{winning_trades}/{total_trades}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    # Color-code P&L metrics - red for negative, green for positive
    pnl_color = "#ff4444" if total_pnl < 0 else "#00ff41"
    avg_pnl_color = "#ff4444" if avg_pnl < 0 else "#00ff41"

    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">TOTAL P&L</div>
        <div style="color: {pnl_color}; font-size: 1.8rem; font-weight: bold;">${total_pnl:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1rem;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">AVG P&L</div>
        <div style="color: {avg_pnl_color}; font-size: 1.8rem; font-weight: bold;">${avg_pnl:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">BEST STRATEGY</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{best_strategy}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1rem;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">WORST STRATEGY</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{worst_strategy}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">SHARPE RATIO</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{sharpe:.2f}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1rem;">
        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">ANALYZED</div>
        <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{analyzed_trades}/{total_trades}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# PnL Calendar - always visible under System Status
st.markdown("### [PNL CALENDAR] - Click any day to filter Dashboard")

# Month selector
import calendar as cal
from datetime import datetime

current_date = datetime.now()
col_month, col_year = st.columns(2)

with col_month:
    selected_month = st.selectbox(
        "Month",
        range(1, 13),
        index=current_date.month - 1,
        format_func=lambda x: cal.month_name[x]
    )

with col_year:
    selected_year = st.selectbox(
        "Year",
        range(2020, current_date.year + 1),
        index=current_date.year - 2020
    )

# Import chart function
from src.interface.components.charts import create_pnl_calendar
from streamlit_plotly_events import plotly_events

with get_session() as session:
    calendar_fig = create_pnl_calendar(session, selected_year, selected_month)

    # Use plotly_events to capture clicks
    selected_data = plotly_events(
        calendar_fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=400,
        override_width="100%",
        key="calendar_click"
    )

    # Handle click event
    if selected_data:
        try:
            # Get clicked point data
            point = selected_data[0]
            x_idx = point.get('x')  # Day of week (Mon, Tue, etc.)
            y_idx = point.get('pointIndex', [None, None])[0]  # Week number

            # Get customdata from the figure
            if y_idx is not None and x_idx is not None:
                # Map day name to index
                day_map = {'Mon': 0, 'Tue': 1, 'Wed': 2, 'Thu': 3, 'Fri': 4, 'Sat': 5, 'Sun': 6}
                x_index = day_map.get(x_idx, 0)

                # Get the date from customdata
                customdata = calendar_fig.data[0].customdata
                if customdata and y_idx < len(customdata) and x_index < len(customdata[y_idx]):
                    clicked_date = customdata[y_idx][x_index]

                    if clicked_date:  # Not empty
                        # Store selected date in session state
                        st.session_state['selected_date'] = clicked_date
                        # Redirect to Dashboard page
                        st.switch_page("pages/1_Dashboard.py")
        except Exception as e:
            st.error(f"[ERROR] Failed to process click: {str(e)}")

st.divider()

# Tabs for different analyses
st.markdown("## [ANALYSIS MODULES]")

# Show warning if no analyzed trades
if analyzed_trades == 0:
    st.warning("[WARN] Advanced analytics require analyzed trades. Go to Dashboard → Select trades → Click 'Analyze Selected'")
    st.info("The tabs below will show placeholder messages until trades are analyzed.")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "[STRATEGY HEATMAP]",
    "[STRATEGY COMPARISON]",
    "[ENTRY QUALITY]",
    "[HOLD TIME ANALYSIS]",
    "[OPTIMAL HOLD TIME]"
])

with tab1:
    st.markdown("### Strategy Performance Heatmap")
    st.info("[INFO] Heatmap shows average max drawdown by strategy × timeframe. Red = high drawdown (bad), Green = low drawdown (good)")

    from src.interface.components.charts import create_strategy_heatmap

    with get_session() as session:
        heatmap_fig = create_strategy_heatmap(session)
        st.plotly_chart(heatmap_fig, use_container_width=True)

with tab2:
    st.markdown("### Strategy Comparison")
    st.info("[INFO] Compare P&L performance across different strategies")

    # Create bar chart of strategy performance
    strategy_df = pd.DataFrame([
        {'Strategy': strat, 'Total P&L': pnl, 'Trades': strategy_counts[strat]}
        for strat, pnl in strategy_pnl.items()
    ])

    import plotly.graph_objects as go
    from src.interface.components.charts import COLORS, get_plotly_layout

    fig = go.Figure()
    colors = [COLORS['profit'] if pnl > 0 else COLORS['loss'] for pnl in strategy_df['Total P&L']]

    fig.add_trace(go.Bar(
        x=strategy_df['Strategy'],
        y=strategy_df['Total P&L'],
        marker_color=colors,
        text=strategy_df['Total P&L'].apply(lambda x: f'${x:.0f}'),
        textposition='outside',
        hovertemplate='<b>%{x}</b><br>P&L: $%{y:.2f}<br>Trades: %{customdata}<extra></extra>',
        customdata=strategy_df['Trades']
    ))

    fig.update_layout(**get_plotly_layout(
        title="[STRATEGY COMPARISON] Total P&L by Strategy",
        xaxis_title="Strategy",
        yaxis_title="Total P&L ($)",
        height=500
    ))

    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### Entry Quality Analysis")
    st.info("[INFO] Correlation between early drawdown (5min) and final P&L. Shows if early price action predicts outcome.")

    from src.interface.components.charts import create_entry_quality_scatter

    # Strategy filter
    selected_strategy_eq = st.selectbox(
        "Filter by Strategy (Entry Quality)",
        options=["All"] + list(strategy_pnl.keys()),
        key="eq_strategy"
    )

    with get_session() as session:
        eq_fig = create_entry_quality_scatter(
            session,
            strategy_type=None if selected_strategy_eq == "All" else selected_strategy_eq
        )
        st.plotly_chart(eq_fig, use_container_width=True)

with tab4:
    st.markdown("### Optimal Hold Time Analysis")
    st.info("[INFO] Shows how P&L evolves over time. Identifies when to exit for maximum profit.")

    # Strategy selector
    selected_strategy_ht = st.selectbox(
        "Select Strategy (Hold Time)",
        options=list(strategy_pnl.keys()),
        key="ht_strategy"
    )

    from src.interface.components.charts import create_hold_time_curve

    with get_session() as session:
        ht_fig = create_hold_time_curve(session, selected_strategy_ht)
        st.plotly_chart(ht_fig, use_container_width=True)

with tab5:
    st.markdown("### Optimal Hold Time - Advanced Analysis")
    st.info("[INFO] Comprehensive optimal hold time analysis using Polygon API data. Compare strategies, simulate outcomes, and identify execution gaps.")

    if analyzed_trades == 0:
        st.warning("[WARN] This analysis requires trades to be analyzed first. Go to Dashboard and click 'Analyze All' or 'Analyze Selected'.")
    else:
        try:
            from src.analysis.optimal_hold_analyzer import OptimalHoldAnalyzer
            from src.interface.components.charts import (
                create_optimal_hold_matrix_chart,
                create_strategy_hold_curves_chart,
                create_cumulative_pnl_simulation_chart,
                create_drawdown_by_timeframe_chart
            )

            with get_session() as session:
                analyzer = OptimalHoldAnalyzer(session)

                # Filters
                st.markdown("#### [FILTER OPTIONS]")
                col_filter1, col_filter2, col_filter3 = st.columns(3)

                with col_filter1:
                    available_strategies = list(strategy_pnl.keys())
                    selected_strategy_opt = st.selectbox(
                        "Strategy Filter",
                        options=["All Strategies"] + available_strategies,
                        key="opt_strategy_filter"
                    )
                    strategy_filter = None if selected_strategy_opt == "All Strategies" else selected_strategy_opt

                with col_filter2:
                    # Get all unique tickers from trades
                    available_tickers = sorted(list(set(t.symbol for t in all_trades if t.symbol)))
                    selected_ticker_opt = st.selectbox(
                        "Ticker Filter",
                        options=["All Tickers"] + available_tickers,
                        key="opt_ticker_filter"
                    )
                    ticker_filter = None if selected_ticker_opt == "All Tickers" else selected_ticker_opt

                with col_filter3:
                    # Show current filter status
                    filter_parts = []
                    if strategy_filter:
                        filter_parts.append(strategy_filter)
                    if ticker_filter:
                        filter_parts.append(ticker_filter)

                    filter_status = " + ".join(filter_parts) if filter_parts else "[ALL DATA]"
                    st.markdown(f"""
                    <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1.5rem;">
                        <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem;">ACTIVE FILTERS</div>
                        <div style="color: #00ff41; font-size: 1.2rem; font-weight: bold;">{filter_status}</div>
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                # Optimal Hold Times Summary
                st.markdown("#### [OPTIMAL HOLD TIMES] Strategy Summary")
                optimal_times = analyzer.get_optimal_hold_times(ticker_filter)

                if optimal_times:
                    # Create summary dataframe
                    summary_data = []
                    for opt in optimal_times:
                        summary_data.append({
                            'Strategy': opt.strategy_type.upper(),
                            'Optimal Time (min)': f"{opt.optimal_timeframe_minutes}",
                            'Avg Actual Hold (min)': f"{opt.actual_avg_hold_minutes:.1f}",
                            'Execution Gap (min)': f"{opt.execution_gap_minutes:+.1f}",
                            'Optimal Avg P&L': f"${opt.optimal_avg_pnl:.2f}",
                            'Improvement Potential': f"${opt.improvement_potential_dollars:.2f}"
                        })

                    summary_df = pd.DataFrame(summary_data)

                    # Style the dataframe with terminal theme
                    st.markdown("""
                    <style>
                    .dataframe {
                        font-family: 'Courier New', Consolas, Monaco, monospace !important;
                        background-color: #0d1f1a !important;
                        color: #e0e0e0 !important;
                    }
                    .dataframe th {
                        background-color: #0a1612 !important;
                        color: #00ff41 !important;
                        text-transform: uppercase;
                        font-weight: bold;
                        border: 1px solid #2a3f38 !important;
                    }
                    .dataframe td {
                        border: 1px solid #2a3f38 !important;
                        color: #e0e0e0 !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    st.dataframe(summary_df, use_container_width=True, hide_index=True)
                else:
                    st.warning("[WARN] No optimal hold time data available. Ensure trades are analyzed.")

                st.divider()

                # Optimal Hold Matrix
                st.markdown("#### [MATRIX VIEW] Strategy × Timeframe P&L Heatmap")
                matrix_data = analyzer.get_strategy_timeframe_matrix(strategy_filter, ticker_filter)

                if matrix_data:
                    matrix_fig = create_optimal_hold_matrix_chart(matrix_data)
                    st.plotly_chart(matrix_fig, use_container_width=True)
                else:
                    st.info("[INFO] No data available for matrix view.")

                st.divider()

                # Strategy Hold Curves
                st.markdown("#### [HOLD CURVES] P&L Evolution by Strategy")

                # Multi-select for strategies to compare
                if strategy_filter:
                    strategies_to_show = [strategy_filter]
                    st.info(f"[INFO] Showing hold curve for: {strategy_filter}")
                else:
                    strategies_to_show = st.multiselect(
                        "Select Strategies to Compare (max 4 recommended)",
                        options=available_strategies,
                        default=available_strategies[:2] if len(available_strategies) >= 2 else available_strategies,
                        key="hold_curves_strategies"
                    )

                if strategies_to_show:
                    curves_fig = create_strategy_hold_curves_chart(matrix_data, strategies_to_show)
                    st.plotly_chart(curves_fig, use_container_width=True)
                else:
                    st.info("[INFO] Select at least one strategy to view hold curves.")

                st.divider()

                # Cumulative PnL Simulation
                st.markdown("#### [WHAT-IF SIMULATOR] Cumulative P&L at Different Hold Times")
                st.info("[INFO] Shows total P&L if ALL trades were held to each timeframe. Compare vs actual results.")

                simulations = analyzer.get_all_simulations(strategy_filter, ticker_filter)

                if simulations:
                    # Calculate actual total PnL for comparison
                    filtered_trades = all_trades
                    if strategy_filter:
                        filtered_trades = [t for t in filtered_trades if t.strategy_type == strategy_filter]
                    if ticker_filter:
                        filtered_trades = [t for t in filtered_trades if t.symbol == ticker_filter]
                    actual_pnl = sum(t.net_pnl for t in filtered_trades)

                    sim_fig = create_cumulative_pnl_simulation_chart(simulations, actual_pnl)
                    st.plotly_chart(sim_fig, use_container_width=True)

                    # Show best simulation
                    best_sim = max(simulations, key=lambda s: s.total_pnl)
                    st.success(f"[BEST SCENARIO] Holding all trades to {best_sim.timeframe_minutes}min → ${best_sim.total_pnl:,.2f} (vs actual: ${actual_pnl:,.2f})")
                else:
                    st.info("[INFO] No simulation data available.")

                st.divider()

                # Drawdown by Timeframe
                st.markdown("#### [DRAWDOWN ANALYSIS] Risk by Hold Time")
                st.info("[INFO] Maximum drawdown at each timeframe. Higher = more risk at that hold time.")

                dd_stats = analyzer.get_drawdown_by_timeframe(strategy_filter, ticker_filter)

                if dd_stats:
                    dd_fig = create_drawdown_by_timeframe_chart(dd_stats)
                    st.plotly_chart(dd_fig, use_container_width=True)
                else:
                    st.info("[INFO] No drawdown data available.")

        except ImportError as e:
            st.error(f"[ERROR] Failed to import optimal hold analyzer: {str(e)}")
        except Exception as e:
            st.error(f"[ERROR] Failed to load optimal hold analysis: {str(e)}")

st.divider()
st.caption("[SYSTEM] Analytics Dashboard v1.0 | Phase 5: Analytics & Visualization")
