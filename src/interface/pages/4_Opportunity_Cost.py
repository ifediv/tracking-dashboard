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
from src.database.operations import get_all_trades
from src.analysis.opportunity_cost import OpportunityCostCalculator
from src.interface.components.charts import create_opportunity_cost_chart
from src.interface.components.buying_power_manager import render_buying_power_manager
from src.utils.config import config

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

        # Strategy Filter Section
        st.markdown("## [FILTER OPTIONS]")

        # Get all available strategies
        all_trades = get_all_trades(session)
        available_strategies = list(set(t.strategy_type for t in all_trades if t.strategy_type))

        col_filter1, col_filter2 = st.columns([2, 1])

        with col_filter1:
            selected_strategies = st.multiselect(
                "Filter by Strategy (leave empty for all)",
                options=available_strategies,
                default=[],
                key="opp_cost_strategy_filter",
                help="Compare specific strategies vs SPY. Leave empty to include all strategies."
            )

        with col_filter2:
            # Show filter status
            if selected_strategies:
                filter_text = ", ".join(selected_strategies)
                st.markdown(f"""
                <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1.5rem;">
                    <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem;">ACTIVE FILTER</div>
                    <div style="color: #00ff41; font-size: 1.2rem; font-weight: bold;">{filter_text}</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1.5rem;">
                    <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem;">FILTER STATUS</div>
                    <div style="color: #1e90ff; font-size: 1.2rem; font-weight: bold;">[ALL STRATEGIES]</div>
                </div>
                """, unsafe_allow_html=True)

        # Apply strategy filter
        strategy_filter = selected_strategies if selected_strategies else None

        st.divider()

        # Opportunity Cost Analysis Section
        st.markdown("## [PERFORMANCE COMPARISON]")

        # Initialize calculator with strategy filter
        calc = OpportunityCostCalculator(session, strategy_filter=strategy_filter)

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

        # What-If Scenarios Section
        st.markdown("### [WHAT-IF SCENARIOS] Optimal Hold Time Simulations")

        # Check if we have analyzed trades
        from src.database.operations import get_analysis_for_trade

        trades_with_analysis = []
        for trade in all_trades:
            if not strategy_filter or trade.strategy_type in strategy_filter:
                analysis = get_analysis_for_trade(session, trade.trade_id)
                if analysis:
                    trades_with_analysis.append(trade)

        if len(trades_with_analysis) > 0:
            st.info("[INFO] Compare actual results vs optimal hold time scenarios. Shows how returns would compare to SPY if trades were held to optimal timeframes.")

            try:
                from src.analysis.optimal_hold_analyzer import OptimalHoldAnalyzer

                analyzer = OptimalHoldAnalyzer(session)

                # Get optimal hold times for filtered strategies
                optimal_times = analyzer.get_optimal_hold_times()
                if strategy_filter:
                    optimal_times = [o for o in optimal_times if o.strategy_type in strategy_filter]

                # Get all simulations
                strategy_for_sim = strategy_filter[0] if strategy_filter and len(strategy_filter) == 1 else None
                simulations = analyzer.get_all_simulations(strategy_for_sim)

                if simulations and optimal_times:
                    # Find the best simulation
                    best_sim = max(simulations, key=lambda s: s.total_pnl)

                    # Create comparison
                    col_sim1, col_sim2, col_sim3 = st.columns(3)

                    with col_sim1:
                        actual_pnl_color = "#00ff41" if metrics.trader_total_return_dollars > 0 else "#ff4444"
                        st.markdown(f"""
                        <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                            <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">ACTUAL TRADING</div>
                            <div style="color: {actual_pnl_color}; font-size: 1.8rem; font-weight: bold;">${metrics.trader_total_return_dollars:,.0f}</div>
                            <div style="color: #a0a0a0; font-size: 0.9rem;">As traded</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_sim2:
                        best_pnl_color = "#00ff41" if best_sim.total_pnl > 0 else "#ff4444"
                        st.markdown(f"""
                        <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                            <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">OPTIMAL SCENARIO</div>
                            <div style="color: {best_pnl_color}; font-size: 1.8rem; font-weight: bold;">${best_sim.total_pnl:,.0f}</div>
                            <div style="color: #a0a0a0; font-size: 0.9rem;">At {best_sim.timeframe_minutes}min exit</div>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_sim3:
                        improvement = best_sim.total_pnl - metrics.trader_total_return_dollars
                        improvement_color = "#00ff41" if improvement > 0 else "#ff4444"
                        improvement_pct = (improvement / abs(metrics.trader_total_return_dollars) * 100) if metrics.trader_total_return_dollars != 0 else 0
                        st.markdown(f"""
                        <div style="font-family: 'Courier New', Consolas, Monaco, monospace;">
                            <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">POTENTIAL GAIN</div>
                            <div style="color: {improvement_color}; font-size: 1.8rem; font-weight: bold;">${improvement:+,.0f}</div>
                            <div style="color: {improvement_color}; font-size: 0.9rem;">{improvement_pct:+.1f}% better</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown("")  # Spacing

                    # Timeframe selector for simulation
                    timeframes = config.get_timeframes()
                    col_tf1, col_tf2 = st.columns([2, 2])

                    with col_tf1:
                        selected_tf = st.selectbox(
                            "Select Timeframe for Detailed Comparison",
                            options=timeframes,
                            format_func=lambda x: f"{x} minutes",
                            index=timeframes.index(best_sim.timeframe_minutes) if best_sim.timeframe_minutes in timeframes else 0,
                            key="whatif_timeframe"
                        )

                    # Get simulation for selected timeframe
                    selected_sim = next((s for s in simulations if s.timeframe_minutes == selected_tf), None)

                    if selected_sim:
                        with col_tf2:
                            # Calculate what SPY would need to return to match this
                            required_spy_return = (selected_sim.total_pnl / metrics.spy_total_return_dollars * 100) if metrics.spy_total_return_dollars != 0 else 0
                            st.markdown(f"""
                            <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1.5rem;">
                                <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem;">SPY EQUIVALENT</div>
                                <div style="color: #1e90ff; font-size: 1.2rem; font-weight: bold;">Would need {required_spy_return:.1f}% return</div>
                            </div>
                            """, unsafe_allow_html=True)

                        # Comparison table
                        st.markdown(f"""
                        <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-top: 1rem;">
                            <table style="width: 100%; color: #e0e0e0; border-collapse: collapse;">
                                <tr style="border-bottom: 1px solid #2a3f38;">
                                    <th style="text-align: left; color: #00ff41; padding: 0.5rem;">Scenario</th>
                                    <th style="text-align: right; color: #00ff41; padding: 0.5rem;">Total P&L</th>
                                    <th style="text-align: right; color: #00ff41; padding: 0.5rem;">vs SPY</th>
                                    <th style="text-align: right; color: #00ff41; padding: 0.5rem;">Outperformance</th>
                                </tr>
                                <tr style="border-bottom: 1px solid #2a3f38;">
                                    <td style="padding: 0.5rem;">Actual Trading</td>
                                    <td style="text-align: right; padding: 0.5rem;">${metrics.trader_total_return_dollars:,.2f}</td>
                                    <td style="text-align: right; padding: 0.5rem;">${metrics.spy_total_return_dollars:,.2f}</td>
                                    <td style="text-align: right; padding: 0.5rem; color: {'#00ff41' if metrics.outperformance_dollars > 0 else '#ff4444'};">${metrics.outperformance_dollars:+,.2f}</td>
                                </tr>
                                <tr style="border-bottom: 1px solid #2a3f38;">
                                    <td style="padding: 0.5rem;">If held to {selected_tf}min</td>
                                    <td style="text-align: right; padding: 0.5rem;">${selected_sim.total_pnl:,.2f}</td>
                                    <td style="text-align: right; padding: 0.5rem;">${metrics.spy_total_return_dollars:,.2f}</td>
                                    <td style="text-align: right; padding: 0.5rem; color: {'#00ff41' if (selected_sim.total_pnl - metrics.spy_total_return_dollars) > 0 else '#ff4444'};">${(selected_sim.total_pnl - metrics.spy_total_return_dollars):+,.2f}</td>
                                </tr>
                            </table>
                        </div>
                        """, unsafe_allow_html=True)

                    # Show strategy breakdown if multiple strategies
                    if not strategy_filter or len(strategy_filter) > 1:
                        st.markdown("")
                        with st.expander("📊 View Strategy-by-Strategy Breakdown", expanded=False):
                            for opt in optimal_times:
                                st.markdown(f"**{opt.strategy_type.upper()}**")
                                st.markdown(f"- Optimal exit: {opt.optimal_timeframe_minutes} minutes")
                                st.markdown(f"- Improvement potential: ${opt.improvement_potential_dollars:.2f}")
                                st.markdown("")

                else:
                    st.warning("[WARN] No simulation data available. Ensure trades are analyzed.")

            except ImportError:
                st.warning("[WARN] Optimal hold analysis module not available.")
            except Exception as e:
                st.error(f"[ERROR] Failed to load what-if scenarios: {str(e)}")
        else:
            st.warning("[WARN] What-if scenarios require analyzed trades. Go to Dashboard and click 'Analyze All' or 'Analyze Selected'.")

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
