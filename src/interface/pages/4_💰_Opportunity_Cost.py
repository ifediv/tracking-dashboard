"""Opportunity Cost Dashboard - Compare active trading vs passive SPY investment."""

import streamlit as st
import sys
from pathlib import Path

# Set page config FIRST
st.set_page_config(
    page_title="Opportunity Cost - Trading Analytics",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.analysis.opportunity_cost import OpportunityCostCalculator
from src.interface.components.charts import create_opportunity_cost_chart
from src.interface.components.buying_power_manager import render_buying_power_manager

# Apply terminal-style theme
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

    header[data-testid="stHeader"] {
        background-color: var(--terminal-bg) !important;
    }

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

    h1, h2, h3 {
        color: var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
        letter-spacing: 2px;
    }

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

    [data-baseweb="select"] {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .stExpander {
        border: 1px solid var(--terminal-gray) !important;
        background-color: var(--terminal-bg-light) !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# >>> OPPORTUNITY COST ANALYSIS")
st.markdown("Compare active trading performance against passive SPY investment")

st.divider()

# Main content
try:
    with get_session() as session:
        # Buying Power Management Section
        render_buying_power_manager(session)

        st.divider()

        # Opportunity Cost Analysis Section
        st.markdown("## [PERFORMANCE COMPARISON]")

        # Initialize calculator
        calc = OpportunityCostCalculator(session)

        # Check if we have data
        try:
            start_date, end_date = calc.get_date_range()
        except ValueError as e:
            st.warning(f"[WARN] {str(e)}")
            st.info("[INFO] Import trades and configure buying power to view opportunity cost analysis.")
            st.stop()

        # Calculate equity curves
        try:
            with st.spinner("[...] Calculating equity curves and fetching SPY data..."):
                daily_data = calc.build_daily_timeline()
                metrics = calc.calculate_performance_metrics(daily_data)
                bp_changes = calc.get_buying_power_changes()

        except ValueError as e:
            st.error(f"[ERROR] {str(e)}")
            st.info("[INFO] Make sure buying power is configured for your trading period.")
            st.stop()
        except Exception as e:
            st.error(f"[ERROR] Failed to calculate opportunity cost: {str(e)}")
            st.stop()

        # Display key metrics
        st.markdown("### [SUMMARY METRICS]")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            trader_color = "#00ff41" if metrics.trader_total_return_dollars > 0 else "#ff4444"
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">TRADER RETURN</div>
                <div style="color: {trader_color}; font-size: 1.8rem; font-weight: bold;">${metrics.trader_total_return_dollars:,.0f}</div>
                <div style="color: {trader_color}; font-size: 1.2rem;">{metrics.trader_total_return_pct:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            spy_color = "#00ff41" if metrics.spy_total_return_dollars > 0 else "#ff4444"
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">SPY RETURN</div>
                <div style="color: {spy_color}; font-size: 1.8rem; font-weight: bold;">${metrics.spy_total_return_dollars:,.0f}</div>
                <div style="color: {spy_color}; font-size: 1.2rem;">{metrics.spy_total_return_pct:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            outperf_color = "#00ff41" if metrics.outperformance_dollars > 0 else "#ff4444"
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">OUTPERFORMANCE</div>
                <div style="color: {outperf_color}; font-size: 1.8rem; font-weight: bold;">${metrics.outperformance_dollars:,.0f}</div>
                <div style="color: {outperf_color}; font-size: 1.2rem;">{metrics.outperformance_pct:+.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">TRADING DAYS</div>
                <div style="color: #00ff41; font-size: 1.8rem; font-weight: bold;">{metrics.trading_days}</div>
                <div style="color: #a0a0a0; font-size: 1rem;">of {metrics.total_days} total</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Equity curve chart
        st.markdown("### [EQUITY CURVES]")
        fig = create_opportunity_cost_chart(daily_data, bp_changes)
        st.plotly_chart(fig, use_container_width=True)

        st.divider()

        # Detailed metrics comparison
        st.markdown("### [DETAILED COMPARISON]")

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("#### [ACTIVE TRADING]")
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <table style="width: 100%; color: #e0e0e0;">
                    <tr>
                        <td style="color: #a0a0a0;">Total Return:</td>
                        <td style="text-align: right; color: #00ff41;"><b>${metrics.trader_total_return_dollars:,.2f}</b></td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Return %:</td>
                        <td style="text-align: right; color: #00ff41;"><b>{metrics.trader_total_return_pct:.2f}%</b></td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Avg Daily P&L:</td>
                        <td style="text-align: right;">${metrics.trader_avg_daily_pnl:.2f}</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Best Day:</td>
                        <td style="text-align: right; color: #00ff41;">${metrics.trader_best_day:.2f}</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Worst Day:</td>
                        <td style="text-align: right; color: #ff4444;">${metrics.trader_worst_day:.2f}</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Win Rate:</td>
                        <td style="text-align: right;">{metrics.trader_win_rate:.1f}%</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Trading Days:</td>
                        <td style="text-align: right;">{metrics.trading_days}</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

        with col_right:
            st.markdown("#### [PASSIVE SPY]")
            st.markdown(f"""
            <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                <table style="width: 100%; color: #e0e0e0;">
                    <tr>
                        <td style="color: #a0a0a0;">Total Return:</td>
                        <td style="text-align: right; color: #1e90ff;"><b>${metrics.spy_total_return_dollars:,.2f}</b></td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Return %:</td>
                        <td style="text-align: right; color: #1e90ff;"><b>{metrics.spy_total_return_pct:.2f}%</b></td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Avg Daily Return:</td>
                        <td style="text-align: right;">{metrics.spy_avg_daily_return:.2f}%</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Best Day:</td>
                        <td style="text-align: right; color: #00ff41;">{metrics.spy_best_day:.2f}%</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Worst Day:</td>
                        <td style="text-align: right; color: #ff4444;">{metrics.spy_worst_day:.2f}%</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Market Days:</td>
                        <td style="text-align: right;">{metrics.total_days}</td>
                    </tr>
                    <tr>
                        <td style="color: #a0a0a0;">Strategy:</td>
                        <td style="text-align: right;">Buy & Hold</td>
                    </tr>
                </table>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # Analysis notes
        st.markdown("### [ANALYSIS NOTES]")
        st.info(f"""
        [INFO] Analysis Period: {start_date} to {end_date}

        **Methodology:**
        - **Trader**: Static book accounting (losses don't reduce available capital)
        - **SPY**: Compounding returns (buy & hold strategy)
        - **Buying Power Changes**: Automatically reflected in both curves
        - **Data Source**: Yahoo Finance (yfinance) for SPY prices
        """)

        if metrics.outperformance_dollars > 0:
            st.success(f"[OK] Active trading outperformed SPY by ${metrics.outperformance_dollars:,.2f} ({metrics.outperformance_pct:+.2f}%)")
        else:
            st.warning(f"[WARN] SPY outperformed active trading by ${abs(metrics.outperformance_dollars):,.2f} ({abs(metrics.outperformance_pct):.2f}%)")

except Exception as e:
    st.error(f"[ERROR] Failed to load opportunity cost analysis: {str(e)}")
    import traceback
    st.code(traceback.format_exc())

st.divider()
st.caption("[SYSTEM] Opportunity Cost Dashboard v1.0 | Phase 6: Benchmark Comparison")
