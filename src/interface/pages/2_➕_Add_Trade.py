"""Trade entry page with manual form and CSV import."""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, time

# Set page config FIRST - must be before any other Streamlit commands
st.set_page_config(
    page_title="Add Trade - Trading Analytics",
    page_icon="▓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import get_session
from src.database.operations import create_trade
from src.utils.config import config
from src.utils.validation import validate_trade_data
from src.utils.csv_processor import import_trades_from_csv

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
    .stTextArea > div > div > textarea,
    .stDateInput > div > div > input,
    .stTimeInput > div > div > input {
        background-color: var(--terminal-bg-light);
        color: var(--text-primary);
        border: 1px solid var(--terminal-gray);
        font-family: 'Courier New', Consolas, Monaco, monospace;
    }

    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextArea > div > div > textarea:focus,
    .stDateInput > div > div > input:focus,
    .stTimeInput > div > div > input:focus {
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

    /* Selectbox Styling - Force dark background */
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

    /* Calendar popup */
    [data-baseweb="calendar"] {
        background-color: var(--terminal-bg-light) !important;
        border: 2px solid var(--matrix-green) !important;
    }

    [data-baseweb="calendar"] * {
        color: var(--text-primary) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    /* Time Input Styling */
    .stTimeInput > div > div {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
    }

    .stTimeInput input {
        color: var(--text-primary) !important;
        background-color: var(--terminal-bg-light) !important;
    }

    /* Expander Styling - Update to match Dashboard */
    [data-testid="stExpander"] summary {
        background-color: var(--terminal-bg-light) !important;
        color: var(--matrix-green) !important;
        border: 1px solid var(--terminal-gray) !important;
        font-family: 'Courier New', Consolas, Monaco, monospace !important;
        font-weight: bold !important;
        text-transform: uppercase !important;
        padding: 1rem !important;
    }

    [data-testid="stExpander"] > div:last-child {
        background-color: var(--terminal-bg-light) !important;
        border: 1px solid var(--terminal-gray) !important;
        border-top: none !important;
        padding: 1rem !important;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("# >>> ADD NEW TRADE")
st.markdown("Enter trades manually or import from CSV")

# Tabs for manual entry vs CSV import
tab1, tab2 = st.tabs(["[MANUAL ENTRY]", "[CSV IMPORT]"])

# ============================================================================
# TAB 1: MANUAL ENTRY
# ============================================================================

with tab1:
    st.subheader("Trade Entry Form")

    # Sub-tabs for organized form
    form_tab1, form_tab2, form_tab3 = st.tabs(["Basic Info", "Prices & P&L", "Context (Optional)"])

    with form_tab1:
        st.markdown("### Basic Trade Information")

        col1, col2 = st.columns(2)

        with col1:
            symbol = st.text_input(
                "Symbol *",
                placeholder="AAPL",
                help="Stock ticker symbol (uppercase)"
            ).upper()

            strategy_type = st.selectbox(
                "Strategy Type *",
                options=config.strategy_types,
                help="Trading strategy used for this trade"
            )

        with col2:
            entry_date = st.date_input(
                "Entry Date *",
                value=datetime.now().date(),
                help="Date when you entered the trade"
            )

            entry_time = st.time_input(
                "Entry Time *",
                value=time(9, 30),
                help="Time when you entered the trade (Eastern Time)"
            )

        col3, col4 = st.columns(2)

        with col3:
            exit_date = st.date_input(
                "Exit Date *",
                value=datetime.now().date(),
                help="Date when you exited the trade"
            )

            exit_time = st.time_input(
                "Exit Time *",
                value=time(10, 0),
                help="Time when you exited the trade (Eastern Time)"
            )

        with col4:
            position_established_date = st.date_input(
                "Position Fully Established Date",
                value=None,
                help="Leave empty if entered full size immediately"
            )

            position_established_time = st.time_input(
                "Position Fully Established Time",
                value=time(9, 30),
                help="Time when position reached max size"
            )

    with form_tab2:
        st.markdown("### Prices & P&L")

        col5, col6 = st.columns(2)

        with col5:
            entry_price = st.number_input(
                "Entry Price *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Price at initial entry"
            )

            exit_price = st.number_input(
                "Exit Price *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Final exit price"
            )

            max_size = st.number_input(
                "Max Size (shares) *",
                min_value=1,
                step=1,
                help="Maximum number of shares held"
            )

        with col6:
            price_at_max_size = st.number_input(
                "Price at Max Size *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Stock price when max position was established"
            )

            avg_price_at_max = st.number_input(
                "Avg Price at Max *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Average price paid for shares at max position"
            )

            bp_used_at_max = st.number_input(
                "BP Used at Max *",
                min_value=0.01,
                step=0.01,
                format="%.2f",
                help="Buying power used at max position"
            )

        col7, col8 = st.columns(2)

        with col7:
            net_pnl = st.number_input(
                "Net P&L *",
                step=0.01,
                format="%.2f",
                help="Net profit/loss after fees"
            )

            gross_pnl = st.number_input(
                "Gross P&L *",
                step=0.01,
                format="%.2f",
                help="Gross profit/loss before fees"
            )

        with col8:
            pnl_at_open = st.number_input(
                "P&L at Open",
                value=0.0,
                step=0.01,
                format="%.2f",
                help="P&L at market open (optional)"
            )

            pnl_at_close = st.number_input(
                "P&L at Close",
                value=0.0,
                step=0.01,
                format="%.2f",
                help="P&L at market close (optional)"
            )

    with form_tab3:
        st.markdown("### News & Context (Optional)")

        headline_title = st.text_input(
            "Headline Title",
            placeholder="e.g., Apple Announces New iPhone",
            help="News headline that influenced this trade (optional)"
        )

        headline_content = st.text_area(
            "Headline Content",
            placeholder="Full news article or summary...",
            help="Full news content (optional)",
            height=100
        )

        col9, col10 = st.columns(2)

        with col9:
            headline_score = st.number_input(
                "Headline Materiality Score",
                min_value=0.0,
                max_value=10.0,
                value=0.0,
                step=0.1,
                help="How impactful was this news? (0-10)"
            )

        with col10:
            # Placeholder for symmetry
            st.write("")

        notes = st.text_area(
            "Trade Notes",
            placeholder="Any observations, lessons learned, or context about this trade...",
            help="Free-form notes (optional)",
            height=100
        )

    # Submit button
    st.divider()

    col_submit1, col_submit2, col_submit3 = st.columns([2, 1, 1])

    with col_submit1:
        submit_button = st.button("[>>>] Add Trade", type="primary", use_container_width=True)

    with col_submit2:
        analyze_after = st.checkbox("Run analysis after adding", value=True)

    with col_submit3:
        clear_form = st.button("[CLEAR] Form", use_container_width=True)

    if clear_form:
        st.rerun()

    if submit_button:
        # Combine date and time into timestamp
        entry_timestamp = datetime.combine(entry_date, entry_time).isoformat()
        exit_timestamp = datetime.combine(exit_date, exit_time).isoformat()

        position_established_timestamp = None
        if position_established_date:
            position_established_timestamp = datetime.combine(
                position_established_date,
                position_established_time
            ).isoformat()

        # Collect all data
        trade_data = {
            'symbol': symbol,
            'strategy_type': strategy_type,
            'entry_timestamp': entry_timestamp,
            'position_fully_established_timestamp': position_established_timestamp,
            'exit_timestamp': exit_timestamp,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'price_at_max_size': price_at_max_size,
            'avg_price_at_max': avg_price_at_max,
            'max_size': max_size,
            'bp_used_at_max': bp_used_at_max,
            'net_pnl': net_pnl,
            'gross_pnl': gross_pnl,
            'pnl_at_open': pnl_at_open if pnl_at_open != 0.0 else None,
            'pnl_at_close': pnl_at_close if pnl_at_close != 0.0 else None,
            'headline_title': headline_title if headline_title else None,
            'headline_content': headline_content if headline_content else None,
            'headline_score': headline_score if headline_score != 0.0 else None,
            'notes': notes if notes else None
        }

        # Validate
        validation_errors = validate_trade_data(trade_data)

        if validation_errors:
            st.error("[ERROR] Validation failed:")
            for error in validation_errors:
                st.error(f"  - {error}")
        else:
            # Insert into database
            try:
                with get_session() as session:
                    trade = create_trade(session, trade_data)
                    session.commit()

                    st.success(f"[OK] Trade added successfully. Trade ID: {trade.trade_id}")

                    # Run analysis if requested
                    if analyze_after:
                        with st.spinner("Running drawdown analysis..."):
                            from src.analysis.processor import TradeAnalyzer

                            analyzer = TradeAnalyzer(session)
                            result = analyzer.analyze_trade(trade.trade_id)

                            if result['success']:
                                st.success(
                                    f"[OK] Analysis complete: {result['timeframes_completed']} timeframes analyzed"
                                )
                            else:
                                st.warning(f"[WARN] Analysis failed: {result['error']}")

                    # Show summary
                    with st.expander("View Trade Summary"):
                        st.json(trade.to_dict())

                    # Option to add another
                    if st.button("[>>>] Add Another Trade"):
                        st.rerun()

            except Exception as e:
                st.error(f"[ERROR] Failed to add trade: {str(e)}")
                st.exception(e)

# ============================================================================
# TAB 2: CSV IMPORT
# ============================================================================

with tab2:
    st.subheader("Bulk Import from CSV")

    st.markdown("""
    Upload a CSV file with your trade data. The file should have the following columns:

    **Required columns:**
    - Symbol, Start, End, Net P&L, Gross P&L, Max Size
    - Price at Max Size, Avg Price at Max, BP Used at Max

    **Optional columns:**
    - P&L at Open, P&L at Close, Notes

    The system expects the same format as your trading platform export.
    """)

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose CSV file",
        type=['csv'],
        help="Upload a CSV file with trade data"
    )

    if uploaded_file:
        try:
            # Try to auto-detect delimiter
            # Read first line to check delimiter
            uploaded_file.seek(0)
            first_line = uploaded_file.readline().decode('utf-8')
            uploaded_file.seek(0)

            # Count delimiters in first line
            pipe_count = first_line.count('|')
            comma_count = first_line.count(',')
            tab_count = first_line.count('\t')

            # Choose most common delimiter
            if pipe_count > comma_count and pipe_count > tab_count:
                delimiter = '|'
            elif tab_count > comma_count:
                delimiter = '\t'
            else:
                delimiter = ','

            # Read CSV with detected delimiter
            df = pd.read_csv(uploaded_file, delimiter=delimiter)

            # Show preview
            st.success(f"[OK] File loaded: {len(df)} rows (delimiter: '{delimiter}')")

            st.markdown("## [DATA PREVIEW] - First 10 Rows")
            st.dataframe(df.head(10), use_container_width=True)

            # Show column mapping
            st.divider()
            st.markdown("## [COLUMN MAPPING]")

            detected_cols = df.columns.tolist()

            # Check for expected columns
            expected_cols = ['Symbol', 'Start', 'End', 'Net P&L', 'Gross P&L', 'Max Size',
                           'Price at Max Size', 'Avg Price at Max', 'BP Used at Max']
            missing_cols = [col for col in expected_cols if col not in detected_cols]

            if missing_cols:
                st.warning(f"[WARN] Missing expected columns: {', '.join(missing_cols)}")
                st.info("""
                **Expected CSV format:**
                - Symbol | Start | End | Net P&L | Gross P&L | Max Size | Price at Max Size | Avg Price at Max | BP Used at Max | P&L at Open | P&L at Close

                Your CSV columns: {', '.join(detected_cols)}
                """)
            else:
                st.success("[OK] All expected columns detected")

            st.write("**Detected columns:**", ", ".join(detected_cols))

            # Import settings
            st.divider()
            st.markdown("## [IMPORT SETTINGS]")

            st.info("""
            [INFO] Imported trades will use default strategy types from CSV.
            You can assign specific strategies after import using the Dashboard.
            """)

            col1, col2 = st.columns(2)

            with col1:
                dry_run = st.checkbox(
                    "Dry Run (Preview Only)",
                    value=True,
                    help="Test import without actually adding to database"
                )

            with col2:
                # Placeholder for future options
                st.write("")

            # Import button
            if st.button("[>>>] Import Trades", type="primary", use_container_width=True):
                with st.spinner("Importing trades..."):
                    try:
                        # Save uploaded file temporarily
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.csv', mode='wb') as tmp_file:
                            tmp_file.write(uploaded_file.getvalue())
                            tmp_path = Path(tmp_file.name)

                        # Import from temporary file with detected delimiter
                        result = import_trades_from_csv(
                            tmp_path,
                            skip_header=True,
                            dry_run=dry_run,
                            delimiter=delimiter
                        )

                        # Clean up temp file
                        tmp_path.unlink()

                        # Display results
                        if result.success_count > 0:
                            st.success(
                                f"[OK] Successfully imported {result.success_count} trades"
                            )

                        if result.skipped_count > 0:
                            st.info(
                                f"[SKIP] {result.skipped_count} duplicate trades (already in database)"
                            )

                            with st.expander("View Skipped Duplicates"):
                                for row_num, reason in result.skipped[:20]:  # Show first 20
                                    st.info(f"Row {row_num}: {reason}")
                                if len(result.skipped) > 20:
                                    st.info(f"... and {len(result.skipped) - 20} more duplicates")

                        if result.failure_count > 0:
                            st.warning(
                                f"[WARN] Failed to import {result.failure_count} trades"
                            )

                            with st.expander("View Errors"):
                                for row_num, error in result.failed[:20]:  # Show first 20
                                    st.error(f"[FAIL] Row {row_num}: {error}")
                                if len(result.failed) > 20:
                                    st.info(f"... and {len(result.failed) - 20} more errors")

                        if dry_run:
                            st.info(
                                "[INFO] This was a dry run. Uncheck 'Dry Run' to actually import the trades."
                            )
                        else:
                            # Ask about analysis
                            st.divider()
                            st.markdown("## [RUN ANALYSIS?]")

                            if st.button("[>>>] Analyze Imported Trades"):
                                with st.spinner("Running analysis on all trades..."):
                                    from src.analysis.processor import TradeAnalyzer
                                    from src.database.session import get_session

                                    with get_session() as session:
                                        analyzer = TradeAnalyzer(session)
                                        analyze_result = analyzer.analyze_all_unprocessed()

                                        st.success(
                                            f"[OK] Analyzed {analyze_result['successful']} trades"
                                        )

                    except Exception as e:
                        st.error(f"[ERROR] Import failed: {str(e)}")
                        st.exception(e)

        except Exception as e:
            st.error(f"[ERROR] Failed to read CSV file: {str(e)}")
            st.exception(e)

    else:
        # Show sample CSV format
        st.divider()
        st.markdown("## [SAMPLE CSV FORMAT]")

        sample_df = pd.DataFrame([
            {
                'Symbol': 'AAPL',
                'Start': '2024-01-15 09:31:00',
                'End': '2024-01-15 10:15:00',
                'Net P&L': '215.00',
                'Gross P&L': '225.00',
                'Max Size': '100',
                'Price at Max Size': '150.50',
                'Avg Price at Max': '150.40',
                'BP Used at Max': '15040.00',
                'P&L at Open': '50.00',
                'P&L at Close': '215.00'
            }
        ])

        st.dataframe(sample_df, use_container_width=True)

        # Download sample CSV
        csv_data = sample_df.to_csv(sep='|', index=False)
        st.download_button(
            label="[>>>] Download Sample CSV",
            data=csv_data,
            file_name="sample_trades.csv",
            mime="text/csv"
        )

# Footer
st.divider()
st.caption("[TIP] Use CSV import for bulk data, manual entry for single trades")
