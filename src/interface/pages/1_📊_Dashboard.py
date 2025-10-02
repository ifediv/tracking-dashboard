"""Dashboard page for viewing and managing trades."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime

# Set page config FIRST - must be before any other Streamlit commands
st.set_page_config(
    page_title="Dashboard - Trading Analytics",
    page_icon="▓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.operations import (
    get_all_trades,
    delete_trade,
    get_unique_symbols,
    update_trade
)
from src.utils.config import config
from src.utils.csv_processor import export_trades_to_csv
import time

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

    /* Sidebar content background */
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
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--matrix-green) !important;
        box-shadow: 0 0 5px var(--matrix-green) !important;
    }

    /* Selectbox (Dropdown) Styling */
    [data-baseweb="select"] {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    [data-baseweb="select"] > div {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border-color: var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    [data-baseweb="select"]:hover > div {
        border-color: var(--matrix-green) !important;
    }

    /* Dropdown menu */
    [data-baseweb="popover"] {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--matrix-green) !important;
    }

    [role="listbox"] {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--matrix-green) !important;
    }

    [role="option"] {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    [role="option"]:hover {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    [aria-selected="true"] {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    /* Checkboxes - Terminal Theme */
    [data-testid="stCheckbox"] {
        color: var(--text-primary);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    [data-testid="stCheckbox"] > label > div {
        background-color: var(--terminal-bg-light) !important;
        border: 2px solid var(--terminal-gray) !important;
    }

    [data-testid="stCheckbox"] > label > div[data-checked="true"] {
        background-color: var(--matrix-green) !important;
        border-color: var(--matrix-green) !important;
    }

    input[type="checkbox"] {
        accent-color: var(--matrix-green) !important;
    }

    /* Modal Dialogs */
    [data-testid="stModal"] {
        background-color: var(--terminal-bg) !important;
    }

    [data-testid="stModal"] > div {
        background-color: var(--terminal-bg) !important;
        border: 3px solid var(--matrix-green) !important;
        box-shadow: 0 0 20px var(--matrix-green) !important;
    }

    /* Warning/Error Messages */
    .stAlert {
        background-color: var(--terminal-bg-light) !important;
        border-left: 4px solid var(--matrix-green) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    [data-baseweb="notification"] {
        background-color: var(--terminal-bg-light) !important;
        border: 2px solid var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* DataFrames/Tables */
    .dataframe {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border: 2px solid var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        font-size: 0.9rem !important;
    }

    .dataframe th {
        background-color: var(--terminal-bg) !important;
        color: var(--matrix-green) !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        font-size: 0.75rem !important;
        letter-spacing: 2px !important;
        border-bottom: 2px solid var(--matrix-green) !important;
        padding: 10px 8px !important;
    }

    .dataframe td {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border-bottom: 1px solid var(--terminal-gray) !important;
        padding: 8px !important;
    }

    .dataframe tr:hover {
        background-color: var(--terminal-gray) !important;
    }

    .dataframe tr:hover td {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    /* Streamlit Dataframe Widget */
    [data-testid="stDataFrame"] {
        background-color: var(--terminal-bg) !important;
        border: 2px solid var(--matrix-green) !important;
        border-radius: 0 !important;
    }

    [data-testid="stDataFrame"] > div {
        background-color: var(--terminal-bg) !important;
    }

    /* Dataframe header */
    [data-testid="stDataFrame"] thead tr th {
        background-color: var(--terminal-bg) !important;
        color: var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        text-transform: uppercase !important;
        font-weight: bold !important;
        letter-spacing: 2px !important;
        border-bottom: 2px solid var(--matrix-green) !important;
    }

    /* Dataframe cells */
    [data-testid="stDataFrame"] tbody tr td {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        border-bottom: 1px solid var(--terminal-gray) !important;
    }

    [data-testid="stDataFrame"] tbody tr:hover td {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    /* Target the actual table element inside the dataframe widget */
    [data-testid="stDataFrame"] table {
        background-color: var(--terminal-bg) !important;
        border: 2px solid var(--matrix-green) !important;
    }

    [data-testid="stDataFrame"] table thead {
        background-color: var(--terminal-bg) !important;
    }

    [data-testid="stDataFrame"] table thead th {
        background-color: var(--terminal-bg) !important;
        color: var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        border-bottom: 2px solid var(--matrix-green) !important;
        font-weight: bold !important;
    }

    [data-testid="stDataFrame"] table tbody {
        background-color: var(--terminal-bg-light) !important;
    }

    [data-testid="stDataFrame"] table tbody tr {
        background-color: var(--terminal-bg-light) !important;
    }

    [data-testid="stDataFrame"] table tbody tr:hover {
        background-color: var(--terminal-gray) !important;
    }

    [data-testid="stDataFrame"] table tbody td {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        border-bottom: 1px solid var(--terminal-gray) !important;
    }

    [data-testid="stDataFrame"] table tbody tr:hover td {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    /* Override any white backgrounds in the dataframe container */
    [data-testid="stDataFrame"] div[data-testid="stDataFrameResizable"] {
        background-color: var(--terminal-bg) !important;
    }

    /* Target the canvas/grid if using AgGrid */
    .ag-theme-streamlit {
        --ag-background-color: var(--terminal-bg-light) !important;
        --ag-foreground-color: var(--text-primary) !important;
        --ag-header-background-color: var(--terminal-bg) !important;
        --ag-header-foreground-color: var(--matrix-green) !important;
        --ag-odd-row-background-color: var(--terminal-bg-light) !important;
        --ag-row-hover-color: var(--terminal-gray) !important;
        --ag-border-color: var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .ag-header-cell-text {
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        color: var(--matrix-green) !important;
        font-weight: bold !important;
    }

    .ag-cell {
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .ag-row-hover {
        background-color: var(--terminal-gray) !important;
    }

    .ag-row-hover .ag-cell {
        color: var(--matrix-green) !important;
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

    [data-baseweb="tag"] > span {
        color: var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Remove X button styling for multiselect tags */
    [data-baseweb="tag"] svg {
        fill: var(--matrix-green) !important;
    }

    /* Date Input Styling - Force all child elements */
    .stDateInput > div > div > input {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .stDateInput > div > div > input:focus {
        border-color: var(--matrix-green) !important;
        box-shadow: 0 0 5px var(--matrix-green) !important;
    }

    /* Date input container - fix white pills */
    .stDateInput > div {
        background-color: var(--terminal-bg-light) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .stDateInput * {
        background-color: var(--terminal-bg-light) !important;
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        border-color: var(--terminal-gray) !important;
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

    [data-baseweb="calendar"] [aria-label*="Choose"] {
        background-color: var(--terminal-gray) !important;
        color: var(--matrix-green) !important;
    }

    /* Expander Styling - Clean header-style */
    [data-testid="stExpander"] {
        border: none !important;
        background-color: transparent !important;
    }

    [data-testid="stExpander"] summary {
        background-color: transparent !important;
        color: var(--matrix-green) !important;
        border: none !important;
        border-bottom: 2px solid var(--matrix-green) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        padding: 0.5rem 0 !important;
        font-size: 1.2rem !important;
    }

    [data-testid="stExpander"] summary:hover {
        border-bottom-color: var(--terminal-blue) !important;
        cursor: pointer !important;
    }

    /* Hide the default arrow icon */
    [data-testid="stExpander"] summary svg {
        display: none !important;
    }

    /* Add custom arrow with pseudo-element */
    [data-testid="stExpander"] summary::before {
        content: '▼ ';
        color: var(--matrix-green);
        font-size: 0.8rem;
        margin-right: 0.5rem;
    }

    [data-testid="stExpander"][open] summary::before {
        content: '▲ ';
    }

    [data-testid="stExpander"] > div:last-child {
        background-color: transparent !important;
        border: none !important;
        padding: 1rem 0 !important;
    }

    /* Main Content Padding */
    .main {
        padding: 0rem 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# >>> TRADE DASHBOARD")
st.markdown("View, filter, and manage your trading history")

# Session state for selections
if 'selected_trade_ids' not in st.session_state:
    st.session_state.selected_trade_ids = []

st.divider()

# Load all trades first (needed for both chart and filtering)
with get_session() as session:
    all_trades_initial = get_all_trades(session)
    # Get filter options
    all_symbols = sorted(get_unique_symbols(session))

if not all_trades_initial:
    st.info("[INFO] No trades found. Add your first trade to get started.")
    st.stop()

# Daily PnL Chart Section - BEFORE filters, shows all trades by default
st.markdown("## [DAILY PNL PERFORMANCE]")
st.info("[INFO] Each trading day starts at $0. Chart shows cumulative P&L as trades execute throughout the day.")

# Strategy filter for PnL chart
chart_strategy_filter = st.selectbox(
    "Filter by Strategy",
    options=["All Strategies"] + config.strategy_types,
    key="pnl_chart_strategy",
    help="Filter the daily P&L chart by specific strategy"
)

# Display chart with all trades (will be updated after filters are applied)
from src.interface.components.charts import create_daily_pnl_chart
pnl_chart_placeholder = st.empty()  # We'll update this after filters

st.divider()

# Filters section - collapsible
with st.expander("[FILTERS]", expanded=True):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        filter_symbols = st.multiselect(
            "Symbols",
            options=all_symbols if all_symbols else [],
            help="Filter by stock symbol"
        )

    with col2:
        filter_strategies = st.multiselect(
            "Strategies",
            options=config.strategy_types,
            help="Filter by strategy type"
        )

    with col3:
        # Check if a date was selected from the calendar
        default_from_date = None
        if 'selected_date' in st.session_state and st.session_state['selected_date']:
            try:
                from datetime import datetime as dt
                default_from_date = dt.strptime(st.session_state['selected_date'], '%Y-%m-%d').date()
            except:
                pass

        filter_date_from = st.date_input(
            "From Date",
            value=default_from_date,
            help="Start date for filtering"
        )

    with col4:
        # Set the same date for "To Date" if coming from calendar click
        default_to_date = default_from_date if default_from_date else None

        filter_date_to = st.date_input(
            "To Date",
            value=default_to_date,
            help="End date for filtering"
        )

    # Clear the selected_date from session state after using it
    if 'selected_date' in st.session_state:
        st.info(f"[CALENDAR] Filtering trades for date: {st.session_state['selected_date']}")
        del st.session_state['selected_date']

    # Additional filters
    col5, col6 = st.columns(2)

    with col5:
        filter_pnl = st.selectbox(
            "P&L Filter",
            options=["All", "Winners Only", "Losers Only"],
            help="Filter by trade outcome"
        )

    with col6:
        sort_by = st.selectbox(
            "Sort By",
            options=["Entry Time (Newest)", "Entry Time (Oldest)", "P&L (Highest)", "P&L (Lowest)", "Symbol"],
            help="Sort order for trades"
        )

st.divider()

# Load and filter trades
try:
    with get_session() as session:
        # Get all trades
        all_trades = get_all_trades(session)

        if not all_trades:
            st.info("[INFO] No trades found. Add your first trade to get started.")
            st.stop()

        # Apply filters
        filtered_trades = all_trades

        # Symbol filter
        if filter_symbols:
            filtered_trades = [t for t in filtered_trades if t.symbol in filter_symbols]

        # Strategy filter
        if filter_strategies:
            filtered_trades = [t for t in filtered_trades if t.strategy_type in filter_strategies]

        # Date filters - use full day range (00:00:00 to 23:59:59)
        if filter_date_from:
            # Start of day (00:00:00) - use T separator for ISO format
            date_from_str = f"{filter_date_from.isoformat()}T00:00:00"
            filtered_trades = [t for t in filtered_trades if t.entry_timestamp >= date_from_str]

        if filter_date_to:
            # End of day (23:59:59) - use T separator for ISO format
            date_to_str = f"{filter_date_to.isoformat()}T23:59:59"
            filtered_trades = [t for t in filtered_trades if t.entry_timestamp <= date_to_str]

        # P&L filter
        if filter_pnl == "Winners Only":
            filtered_trades = [t for t in filtered_trades if t.net_pnl > 0]
        elif filter_pnl == "Losers Only":
            filtered_trades = [t for t in filtered_trades if t.net_pnl < 0]

        # Sort
        if sort_by == "Entry Time (Newest)":
            filtered_trades = sorted(filtered_trades, key=lambda t: t.entry_timestamp, reverse=True)
        elif sort_by == "Entry Time (Oldest)":
            filtered_trades = sorted(filtered_trades, key=lambda t: t.entry_timestamp)
        elif sort_by == "P&L (Highest)":
            filtered_trades = sorted(filtered_trades, key=lambda t: t.net_pnl, reverse=True)
        elif sort_by == "P&L (Lowest)":
            filtered_trades = sorted(filtered_trades, key=lambda t: t.net_pnl)
        elif sort_by == "Symbol":
            filtered_trades = sorted(filtered_trades, key=lambda t: t.symbol)

        # Update PnL chart with filtered trades
        with pnl_chart_placeholder.container():
            pnl_chart = create_daily_pnl_chart(filtered_trades, chart_strategy_filter)
            st.plotly_chart(pnl_chart, use_container_width=True)

        if not filtered_trades:
            st.warning("[WARN] No trades match your filters.")
            st.stop()

        # Trade History section - collapsible
        with st.expander(f"[TRADE HISTORY] - {len(filtered_trades)} Records", expanded=True):
            # Convert to DataFrame for display
            df_data = []
            for t in filtered_trades:
                pnl_pct = ((t.exit_price - t.entry_price) / t.entry_price * 100) if t.entry_price else 0
                df_data.append({
                    'Select': False,  # Checkbox placeholder
                    'ID': t.trade_id,
                    'Symbol': t.symbol,
                    'Strategy': t.strategy_type,
                    'Entry Date': t.entry_timestamp[:10],
                    'Entry Time': t.entry_timestamp[11:16],
                    'Exit Date': t.exit_timestamp[:10],
                    'Exit Time': t.exit_timestamp[11:16],
                    'Entry Price': f"${t.entry_price:.2f}",
                    'Exit Price': f"${t.exit_price:.2f}",
                    'Size': t.max_size,
                    'Net P&L': f"${t.net_pnl:.2f}",
                    'P&L %': f"{pnl_pct:.2f}%",
                    'Gross P&L': f"${t.gross_pnl:.2f}"
                })

            df = pd.DataFrame(df_data)

            # Initialize session state for strategy edits and original strategies
            if 'strategy_edits' not in st.session_state:
                st.session_state.strategy_edits = {}

            if 'original_strategies' not in st.session_state:
                st.session_state.original_strategies = {t.trade_id: t.strategy_type for t in filtered_trades}
            else:
                # Update with current data
                st.session_state.original_strategies = {t.trade_id: t.strategy_type for t in filtered_trades}

            # Add expandable view option
            col_expand1, col_expand2 = st.columns([6, 1])
            with col_expand2:
                if 'table_expanded' not in st.session_state:
                    st.session_state.table_expanded = False

            if st.button("[EXPAND]" if not st.session_state.table_expanded else "[COLLAPSE]", use_container_width=True):
                st.session_state.table_expanded = not st.session_state.table_expanded
                st.rerun()

            # Determine table height based on expanded state
            table_height = 600 if st.session_state.table_expanded else 400

            # Create table with editable strategy column
            st.markdown("""
            <style>
            .trade-table-header {
                color: #00ff41;
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 2px;
                font-weight: bold;
                padding: 8px 4px;
                font-family: 'Courier New', Consolas, Monaco, monospace;
            }
            .trade-table-cell {
                color: #e0e0e0;
                font-size: 0.85rem;
                padding: 4px;
                font-family: 'Courier New', Consolas, Monaco, monospace;
            }
            </style>
            """, unsafe_allow_html=True)

            # Wrap table in container with fixed width
            # Create a grid layout for the table
            # Header row - using explicit gap parameter (added DELETE column)
            cols = st.columns([0.4, 0.5, 0.8, 1.2, 1.0, 0.8, 1.0, 0.8, 1.0, 1.0, 0.8, 1.0, 0.8, 1.0], gap="small")
            headers = ['DEL', 'ID', 'SYMBOL', 'STRATEGY', 'ENTRY-DATE', 'ENTRY-TIME', 'EXIT-DATE', 'EXIT-TIME',
                       'ENTRY-PRICE', 'EXIT-PRICE', 'SIZE', 'NET-P&L', 'P&L-%', 'GROSS-P&L']
            for col, header in zip(cols, headers):
                col.markdown(f'<p class="trade-table-header">{header}</p>', unsafe_allow_html=True)

            st.divider()

            # Data rows with editable strategy dropdown
            for idx, row in df.iterrows():
                cols = st.columns([0.4, 0.5, 0.8, 1.2, 1.0, 0.8, 1.0, 0.8, 1.0, 1.0, 0.8, 1.0, 0.8, 1.0], gap="small")

                trade_id = row['ID']

                # Column 0: DELETE checkbox
                delete_key = f"delete_{trade_id}"
                if delete_key not in st.session_state:
                    st.session_state[delete_key] = False

                cols[0].checkbox(
                    label="",
                    key=delete_key,
                    label_visibility="collapsed"
                )

                # Column 1: ID
                cols[1].markdown(f'<p class="trade-table-cell">{row["ID"]}</p>', unsafe_allow_html=True)

                # Column 2: Symbol
                cols[2].markdown(f'<p class="trade-table-cell">{row["Symbol"]}</p>', unsafe_allow_html=True)

                # Column 3: EDITABLE Strategy dropdown
                original_strategy = st.session_state.original_strategies.get(trade_id, row['Strategy'])

                selected_strategy = cols[3].selectbox(
                    label=f"strategy_{trade_id}",
                    options=config.strategy_types,
                    index=config.strategy_types.index(original_strategy) if original_strategy in config.strategy_types else 0,
                    key=f"strategy_select_{trade_id}",
                    label_visibility="collapsed"
                )

                # Track changes compared to original
                if selected_strategy != original_strategy:
                    st.session_state.strategy_edits[trade_id] = selected_strategy
                elif trade_id in st.session_state.strategy_edits:
                    # Changed back to original, remove from edits
                    del st.session_state.strategy_edits[trade_id]

                # Remaining columns (shifted by 1 due to delete column)
                cols[4].markdown(f'<p class="trade-table-cell">{row["Entry Date"]}</p>', unsafe_allow_html=True)
                cols[5].markdown(f'<p class="trade-table-cell">{row["Entry Time"]}</p>', unsafe_allow_html=True)
                cols[6].markdown(f'<p class="trade-table-cell">{row["Exit Date"]}</p>', unsafe_allow_html=True)
                cols[7].markdown(f'<p class="trade-table-cell">{row["Exit Time"]}</p>', unsafe_allow_html=True)
                cols[8].markdown(f'<p class="trade-table-cell">{row["Entry Price"]}</p>', unsafe_allow_html=True)
                cols[9].markdown(f'<p class="trade-table-cell">{row["Exit Price"]}</p>', unsafe_allow_html=True)
                cols[10].markdown(f'<p class="trade-table-cell">{row["Size"]}</p>', unsafe_allow_html=True)
                cols[11].markdown(f'<p class="trade-table-cell">{row["Net P&L"]}</p>', unsafe_allow_html=True)
                cols[12].markdown(f'<p class="trade-table-cell">{row["P&L %"]}</p>', unsafe_allow_html=True)
                cols[13].markdown(f'<p class="trade-table-cell">{row["Gross P&L"]}</p>', unsafe_allow_html=True)

            # Save Changes and Delete buttons - always display below table
            st.divider()

            # Check which trades are marked for deletion
            trades_to_delete = [
                int(key.replace("delete_", ""))
                for key in st.session_state.keys()
                if key.startswith("delete_") and st.session_state[key]
            ]

            # Show delete section if any trades selected
            if trades_to_delete:
                st.warning(f"**[⚠️ DELETE WARNING]** - {len(trades_to_delete)} trade(s) marked for deletion")

                # Show which trades will be deleted
                delete_info_df = df[df['ID'].isin(trades_to_delete)][['ID', 'Symbol', 'Entry Date', 'Net P&L']]
                st.dataframe(delete_info_df, use_container_width=True, hide_index=True)

                col_del1, col_del2, col_del3 = st.columns([1, 2, 1])
                with col_del2:
                    # Use modal dialog for confirmation
                    @st.dialog("⚠️ CONFIRM DELETION")
                    def confirm_delete():
                        st.error(f"""
                        **PERMANENT ACTION - CANNOT BE UNDONE**

                        You are about to **permanently delete {len(trades_to_delete)} trade(s)** from the database.

                        This will remove:
                        - Trade records
                        - All associated analysis data
                        - All drawdown analysis results

                        **This action is irreversible.**
                        """)

                        st.divider()

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("❌ CANCEL", use_container_width=True):
                                st.rerun()

                        with col2:
                            if st.button("🗑️ DELETE PERMANENTLY", type="primary", use_container_width=True):
                                try:
                                    with get_session() as session:
                                        deleted_count = 0
                                        for trade_id in trades_to_delete:
                                            if delete_trade(session, trade_id):
                                                deleted_count += 1
                                                # Clear checkbox state
                                                if f"delete_{trade_id}" in st.session_state:
                                                    del st.session_state[f"delete_{trade_id}"]

                                    st.success(f"[SUCCESS] Deleted {deleted_count} trade(s) from database")
                                    time.sleep(1)
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"[ERROR] Failed to delete trades: {str(e)}")

                    if st.button("[🗑️ DELETE SELECTED TRADES]", type="secondary", use_container_width=True):
                        confirm_delete()

            st.divider()

            if st.session_state.strategy_edits:
                # Show pending changes
                st.markdown(f"**[PENDING CHANGES]** - {len(st.session_state.strategy_edits)} trade(s) modified:")
                changes_df = pd.DataFrame([
                    {
                        'Trade ID': tid,
                        'Original Strategy': st.session_state.original_strategies.get(tid, 'N/A'),
                        'New Strategy': new_strat
                    }
                    for tid, new_strat in st.session_state.strategy_edits.items()
                ])
                st.dataframe(changes_df, use_container_width=True, hide_index=True)

                col_save1, col_save2, col_save3 = st.columns([1, 2, 1])
                with col_save2:
                    if st.button("[>>> SAVE CHANGES]", type="primary", use_container_width=True):
                        try:
                            updated_count = 0
                            with get_session() as session:
                                for trade_id, new_strategy in st.session_state.strategy_edits.items():
                                    original = st.session_state.original_strategies.get(trade_id)
                                    update_trade(session, trade_id, {'strategy_type': new_strategy})
                                    updated_count += 1
                                session.commit()

                            st.success(f"[OK] Successfully updated {updated_count} trade(s) in database")

                            # Clear edits
                            st.session_state.strategy_edits = {}
                            st.session_state.original_strategies = {}
                            time.sleep(1.5)
                            st.rerun()
                        except Exception as e:
                            st.error(f"[ERROR] Failed to update trades: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
            else:
                st.info("[INFO] No changes detected. Modify strategy dropdowns above to enable saving.")

        # Action buttons
        st.divider()
        with st.expander("[ACTIONS]", expanded=True):
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("[>>>] Analyze All", use_container_width=True):
                    with st.spinner("Running analysis on filtered trades..."):
                        from src.analysis.processor import TradeAnalyzer

                        analyzer = TradeAnalyzer(session)
                        trade_ids = [t.trade_id for t in filtered_trades]

                        result = analyzer.analyze_batch(trade_ids)

                        st.success(f"[OK] Analyzed {result['successful']}/{result['total_trades']} trades")
                        st.info(f"[INFO] Total timeframes: {result['total_timeframes']}")

                        if result['failures']:
                            with st.expander("View Failures"):
                                for failure in result['failures']:
                                    st.error(f"[FAIL] Trade {failure['trade_id']}: {failure['error']}")

            with col2:
                if st.button("[>>>] Export to CSV", use_container_width=True):
                    try:
                        # Export filtered trades
                        export_path = Path(f"data/exports/trades_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                        export_path.parent.mkdir(parents=True, exist_ok=True)

                        result = export_trades_to_csv(session, str(export_path), filtered_trades)

                        if result['success']:
                            st.success(f"[OK] Exported {result['count']} trades to {export_path}")

                            # Provide download button
                            with open(export_path, 'r') as f:
                                st.download_button(
                                    label="[>>>] Download CSV",
                                    data=f.read(),
                                    file_name=export_path.name,
                                    mime="text/csv"
                                )
                        else:
                            st.error(f"[FAIL] Export failed: {result.get('error')}")

                    except Exception as e:
                        st.error(f"[ERROR] Export failed: {str(e)}")

            with col3:
                # Trade selection input
                selected_ids_input = st.text_input(
                    "Trade IDs to delete",
                    placeholder="e.g., 1,2,3",
                    help="Enter comma-separated trade IDs"
                )

            with col4:
                if st.button("[X] Delete Selected", type="secondary", use_container_width=True):
                    if selected_ids_input:
                        try:
                            # Parse IDs
                            ids_to_delete = [int(id.strip()) for id in selected_ids_input.split(',')]

                            # Confirm deletion
                            if st.session_state.get('confirm_delete') != ids_to_delete:
                                st.session_state.confirm_delete = ids_to_delete
                                st.warning(f"[WARN] Click again to confirm deletion of {len(ids_to_delete)} trades")
                            else:
                                # Delete trades
                                deleted_count = 0
                                for trade_id in ids_to_delete:
                                    if delete_trade(session, trade_id):
                                        deleted_count += 1

                                session.commit()
                                st.success(f"[OK] Deleted {deleted_count} trades")
                                st.session_state.confirm_delete = None
                                st.rerun()

                        except ValueError:
                            st.error("[ERROR] Invalid trade IDs. Use comma-separated numbers (e.g., 1,2,3)")
                    else:
                        st.warning("[WARN] Enter trade IDs to delete")

            # Trade detail view
            st.divider()
            st.markdown("## [TRADE DETAILS]")

            trade_id_to_view = st.number_input(
                "Enter Trade ID to view details",
                min_value=1,
                step=1,
                value=filtered_trades[0].trade_id if filtered_trades else 1
            )

            if st.button("View Details"):
                trade = next((t for t in filtered_trades if t.trade_id == trade_id_to_view), None)

                if trade:
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown("**Trade Information**")
                        st.write(f"**ID:** {trade.trade_id}")
                        st.write(f"**Symbol:** {trade.symbol}")
                        st.write(f"**Strategy:** {trade.strategy_type}")
                        st.write(f"**Entry:** {trade.entry_timestamp}")
                        st.write(f"**Exit:** {trade.exit_timestamp}")

                    with col2:
                        st.markdown("**Price & P&L**")
                        st.write(f"**Entry Price:** ${trade.entry_price:.2f}")
                        st.write(f"**Exit Price:** ${trade.exit_price:.2f}")
                        st.write(f"**Max Size:** {trade.max_size}")
                        st.write(f"**Net P&L:** ${trade.net_pnl:.2f}")
                        st.write(f"**Gross P&L:** ${trade.gross_pnl:.2f}")

                    if trade.notes:
                        st.markdown("**Notes**")
                        st.info(trade.notes)

                    if trade.headline_title:
                        st.markdown("**News Context**")
                        st.write(f"**Title:** {trade.headline_title}")
                        if trade.headline_content:
                            with st.expander("View Full Headline"):
                                st.write(trade.headline_content)
                        if trade.headline_score:
                            st.write(f"**Score:** {trade.headline_score}/10")

                else:
                    st.warning(f"[WARN] Trade #{trade_id_to_view} not found in filtered results")

except Exception as e:
    st.error(f"[ERROR] Failed to load trades: {str(e)}")
    st.exception(e)
