"""Main Streamlit application for Trading Analytics System.

This is the entry point for the Streamlit UI.
Run with: streamlit run src/interface/app.py
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.config import config
from src.database.session import get_session
from src.database.operations import get_trade_count, get_all_trades

# Streamlit page config
st.set_page_config(
    page_title="Trading Analytics Terminal",
    page_icon="▓",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

    /* Main Background */
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

    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-weight: bold;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    h1 { border-bottom: 2px solid var(--matrix-green); padding-bottom: 0.5rem; }
    h2 { border-bottom: 1px solid var(--terminal-gray); padding-bottom: 0.3rem; }

    /* Metrics */
    [data-testid="stMetricValue"] {
        color: var(--matrix-green);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-size: 1.8rem;
        font-weight: bold;
    }

    [data-testid="stMetricLabel"] {
        color: var(--text-secondary);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
        font-size: 0.8rem;
        letter-spacing: 1px;
    }

    [data-testid="stMetricDelta"] {
        font-family: 'Courier New', Consolas, Monaco, monospace;
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
        transition: all 0.2s;
    }

    .stButton > button:hover {
        background-color: var(--matrix-green);
        color: var(--terminal-bg);
        border-color: var(--matrix-green);
    }

    .stButton > button[kind="primary"] {
        background-color: var(--terminal-blue);
        border-color: var(--terminal-blue);
        color: var(--terminal-bg);
    }

    .stButton > button[kind="primary"]:hover {
        background-color: var(--matrix-green);
        border-color: var(--matrix-green);
    }

    /* Input Fields */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > select,
    .stTextArea > div > div > textarea {
        background-color: var(--terminal-bg-light);
        color: var(--text-primary);
        border: 1px solid var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--matrix-green);
        box-shadow: 0 0 5px var(--matrix-green);
    }

    /* DataFrames/Tables */
    .dataframe {
        background-color: var(--terminal-bg-light);
        color: var(--text-primary);
        border: 1px solid var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    .dataframe th {
        background-color: var(--terminal-gray);
        color: var(--matrix-green);
        font-weight: bold;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 1px;
    }

    .dataframe td {
        background-color: var(--terminal-bg-light);
        color: var(--text-primary);
    }

    .dataframe tr:hover {
        background-color: var(--terminal-gray);
    }

    /* Info/Success/Warning/Error Messages */
    .stAlert {
        background-color: var(--terminal-bg-light);
        border: 1px solid var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        border-left-width: 4px;
    }

    [data-baseweb="notification"] {
        background-color: var(--terminal-bg-light);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    .stSuccess {
        border-left-color: var(--matrix-green);
        color: var(--matrix-green);
    }

    .stInfo {
        border-left-color: var(--terminal-blue);
        color: var(--terminal-blue);
    }

    .stWarning {
        border-left-color: #ffaa00;
        color: #ffaa00;
    }

    .stError {
        border-left-color: #ff4444;
        color: #ff4444;
    }

    /* Dividers */
    hr {
        border-color: var(--terminal-gray);
        border-style: solid;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background-color: var(--terminal-bg-light);
        border-bottom: 2px solid var(--terminal-gray);
    }

    .stTabs [data-baseweb="tab"] {
        color: var(--text-secondary);
        background-color: transparent;
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stTabs [aria-selected="true"] {
        color: var(--matrix-green);
        border-bottom-color: var(--matrix-green);
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: var(--terminal-bg-light);
        color: var(--matrix-green);
        border: 1px solid var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-transform: uppercase;
    }

    .streamlit-expanderContent {
        background-color: var(--terminal-bg-light);
        border: 1px solid var(--terminal-gray);
        border-top: none;
    }

    /* File Uploader */
    [data-testid="stFileUploader"] {
        background-color: var(--terminal-bg-light);
        border: 2px dashed var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    /* Checkbox */
    .stCheckbox {
        font-family: 'Courier New', Consolas, Monaco, monospace;
        color: var(--text-primary);
    }

    /* Spinner */
    .stSpinner > div {
        border-top-color: var(--matrix-green);
    }

    /* Captions */
    .caption, .stCaption {
        color: var(--text-secondary);
        font-family: 'Courier New', Consolas, Monaco, monospace;
        font-size: 0.85rem;
    }

    /* Main Content Padding */
    .main {
        padding: 0rem 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("## ╔═══════════════════════════╗")
st.sidebar.markdown("## ║  TRADING ANALYTICS  ║")
st.sidebar.markdown("## ╚═══════════════════════════╝")
st.sidebar.markdown("---")
st.sidebar.info(
    "**[>>>] NAVIGATION**\n\n"
    "• **Dashboard**: View, filter, and manage trades\n"
    "• **Add Trade**: Manual entry or CSV import\n"
    "• **Analytics**: PnL calendar, strategy analysis, drawdown metrics"
)

# Main page: Welcome and quick stats
st.markdown("# >>> TRADING ANALYTICS TERMINAL")

st.markdown("""
```
╔════════════════════════════════════════════════════════════════╗
║  SYSTEM OVERVIEW                                               ║
╠════════════════════════════════════════════════════════════════╣
║  • Track all trades with detailed entry/exit data              ║
║  • Analyze drawdown patterns across multiple timeframes        ║
║  • Identify which strategies and entries work best             ║
║  • Optimize hold times based on historical performance         ║
╚════════════════════════════════════════════════════════════════╝
```
""")

st.divider()

# Quick stats
st.markdown("## [SYSTEM STATUS]")

try:
    with get_session() as session:
        total_trades = get_trade_count(session)

        if total_trades > 0:
            # Get all trades for statistics
            all_trades = get_all_trades(session)

            # Calculate stats
            total_pnl = sum(t.net_pnl for t in all_trades)
            winning_trades = sum(1 for t in all_trades if t.net_pnl > 0)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # Strategy breakdown
            strategy_counts = {}
            for trade in all_trades:
                strategy_counts[trade.strategy_type] = strategy_counts.get(trade.strategy_type, 0) + 1
            most_traded_strategy = max(strategy_counts.items(), key=lambda x: x[1])[0] if strategy_counts else "N/A"

            # Display metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Total Trades", total_trades)

            with col2:
                st.metric(
                    "Total P&L",
                    f"${total_pnl:,.2f}",
                    delta=f"{total_pnl:,.2f}",
                    delta_color="normal"
                )

            with col3:
                st.metric(
                    "Win Rate",
                    f"{win_rate:.1f}%",
                    delta=f"{winning_trades}/{total_trades}"
                )

            with col4:
                st.metric("Most Traded Strategy", most_traded_strategy)

            # Recent trades preview
            st.divider()
            st.markdown("## [RECENT ACTIVITY] - Last 5 Trades")

            import pandas as pd
            recent_trades = all_trades[:5]
            df = pd.DataFrame([{
                'ID': t.trade_id,
                'Symbol': t.symbol,
                'Strategy': t.strategy_type,
                'Entry': t.entry_timestamp[:16],
                'Exit': t.exit_timestamp[:16],
                'P&L': f"${t.net_pnl:.2f}",
                'Size': t.max_size
            } for t in recent_trades])

            st.dataframe(df, use_container_width=True, hide_index=True)

        else:
            st.info("[INFO] No trades detected in database. Initialize system with trade data.")

            # Show getting started guide
            st.markdown("""
```
╔════════════════════════════════════════════════════════════════╗
║  GETTING STARTED                                               ║
╠════════════════════════════════════════════════════════════════╣
║  [1] ADD YOUR FIRST TRADE                                      ║
║      • Navigate to "Add Trade" page                            ║
║      • Use manual form or CSV bulk import                      ║
║                                                                 ║
║  [2] RUN ANALYSIS                                              ║
║      • Execute drawdown analysis after import                  ║
║      • View metrics in Analytics section                       ║
║                                                                 ║
║  [3] REVIEW PERFORMANCE                                        ║
║      • Use Dashboard for filtering and review                  ║
║      • Export data for external analysis                       ║
╚════════════════════════════════════════════════════════════════╝
```
            """)

except Exception as e:
    st.error(f"[ERROR] Failed to load system stats: {str(e)}")
    st.exception(e)

# Footer
st.divider()
st.caption("[SYSTEM] Trading Analytics Terminal v1.0 | Phase 4: Data Entry Interface")
