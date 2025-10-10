"""Terminal-styled modal components for Streamlit dashboard.

Provides reusable modal dialog components with terminal aesthetic
for displaying detailed data without cluttering the main dashboard.
"""

import streamlit as st
from typing import Optional, Callable


def render_terminal_modal(
    button_label: str,
    modal_title: str,
    content_callback: Callable,
    button_key: str,
    modal_key: str,
    help_text: Optional[str] = None
) -> None:
    """Render a terminal-styled expandable modal dialog.

    Creates a button that, when clicked, opens an expander containing
    the modal content. Styled with terminal colors and monospace fonts.

    Args:
        button_label: Text to display on the trigger button
        modal_title: Title shown at top of modal
        content_callback: Function that renders the modal content
        button_key: Unique key for the button (required by Streamlit)
        modal_key: Unique key for the expander (required by Streamlit)
        help_text: Optional tooltip text for the button

    Example:
        >>> def render_details():
        ...     st.write("Detailed information here")
        ...     st.dataframe(data)
        >>>
        >>> render_terminal_modal(
        ...     button_label="[VIEW DETAILS]",
        ...     modal_title="Detailed Analysis",
        ...     content_callback=render_details,
        ...     button_key="details_btn",
        ...     modal_key="details_modal"
        ... )
    """
    # Render trigger button
    if st.button(
        button_label,
        key=button_key,
        help=help_text,
        use_container_width=False
    ):
        # Toggle modal state
        if modal_key not in st.session_state:
            st.session_state[modal_key] = False
        st.session_state[modal_key] = not st.session_state[modal_key]

    # Render modal if open
    if st.session_state.get(modal_key, False):
        with st.expander(f">>> {modal_title}", expanded=True):
            # Render content using callback
            content_callback()

            # Close button at bottom
            if st.button(
                "[CLOSE]",
                key=f"{modal_key}_close",
                use_container_width=False
            ):
                st.session_state[modal_key] = False
                st.rerun()


def render_terminal_expander(
    title: str,
    content_callback: Callable,
    expanded: bool = False,
    key: Optional[str] = None
) -> None:
    """Render a terminal-styled expander (simpler than modal).

    Similar to render_terminal_modal but uses only an expander without
    a separate trigger button. Good for sections that don't need to be
    hidden behind a button click.

    Args:
        title: Title shown on the expander
        content_callback: Function that renders the expander content
        expanded: Whether expander starts open (default: False)
        key: Optional unique key for the expander

    Example:
        >>> def render_matrix():
        ...     st.plotly_chart(fig, use_container_width=True)
        >>>
        >>> render_terminal_expander(
        ...     title="Strategy × Timeframe Matrix",
        ...     content_callback=render_matrix,
        ...     expanded=True,
        ...     key="matrix_expander"
        ... )
    """
    with st.expander(f">>> {title}", expanded=expanded):
        content_callback()


def render_terminal_tabs(
    tabs: list[tuple[str, Callable]],
    key_prefix: str
) -> None:
    """Render terminal-styled tabs for organizing content.

    Creates Streamlit tabs with terminal-styled labels and content.
    Each tab renders its content using a callback function.

    Args:
        tabs: List of (tab_label, content_callback) tuples
        key_prefix: Prefix for generating unique tab keys

    Example:
        >>> def render_overview():
        ...     st.metric("Total Trades", 100)
        >>>
        >>> def render_details():
        ...     st.dataframe(df)
        >>>
        >>> render_terminal_tabs(
        ...     tabs=[
        ...         ("OVERVIEW", render_overview),
        ...         ("DETAILS", render_details)
        ...     ],
        ...     key_prefix="analysis"
        ... )
    """
    # Format tab labels with brackets
    tab_labels = [f"[{label}]" for label, _ in tabs]

    # Create tabs
    tab_objects = st.tabs(tab_labels)

    # Render content in each tab
    for tab_obj, (_, content_callback) in zip(tab_objects, tabs):
        with tab_obj:
            content_callback()


def render_terminal_info_box(
    title: str,
    items: dict[str, str],
    box_color: str = "matrix_green"
) -> None:
    """Render a terminal-styled information box.

    Displays key-value pairs in a bordered box with terminal styling.
    Useful for showing metrics, configuration, or status information.

    Args:
        title: Title shown at top of box
        items: Dictionary of label -> value pairs
        box_color: Color theme ('matrix_green', 'terminal_blue', 'warning')

    Example:
        >>> render_terminal_info_box(
        ...     title="System Status",
        ...     items={
        ...         "Database": "Connected",
        ...         "Trades Loaded": "150",
        ...         "Last Update": "2025-10-10 15:30:00"
        ...     }
        ... )
    """
    # Color mapping
    colors = {
        'matrix_green': '#00ff41',
        'terminal_blue': '#1e90ff',
        'warning': '#ffaa00',
        'loss': '#ff4444'
    }

    border_color = colors.get(box_color, colors['matrix_green'])

    # Build HTML table
    rows_html = ""
    for label, value in items.items():
        rows_html += f"""
            <tr>
                <td style="color: #a0a0a0; padding: 0.3rem 1rem;">{label}:</td>
                <td style="color: #e0e0e0; padding: 0.3rem 1rem; text-align: right;"><b>{value}</b></td>
            </tr>
        """

    html = f"""
    <div style="
        border: 2px solid {border_color};
        border-radius: 4px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #0d1f1a;
        font-family: 'Courier New', Consolas, Monaco, monospace;
    ">
        <div style="
            color: {border_color};
            font-size: 1.1rem;
            font-weight: bold;
            margin-bottom: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 2px;
        ">>>> {title}</div>
        <table style="width: 100%; color: #e0e0e0;">
            {rows_html}
        </table>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_terminal_metric_card(
    label: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "matrix_green"
) -> None:
    """Render a terminal-styled metric card.

    Displays a single metric with optional delta in terminal styling.
    Can be used in columns for dashboard-style layouts.

    Args:
        label: Metric label
        value: Main metric value (formatted string)
        delta: Optional delta/change indicator
        delta_color: Color for delta ('matrix_green', 'loss', 'warning')

    Example:
        >>> col1, col2, col3 = st.columns(3)
        >>> with col1:
        ...     render_terminal_metric_card(
        ...         label="Total P&L",
        ...         value="$12,450",
        ...         delta="+15.2%",
        ...         delta_color="matrix_green"
        ...     )
    """
    colors = {
        'matrix_green': '#00ff41',
        'loss': '#ff4444',
        'warning': '#ffaa00',
        'terminal_blue': '#1e90ff'
    }

    value_color = colors.get(delta_color, colors['matrix_green'])

    delta_html = ""
    if delta:
        delta_html = f"""
            <div style="
                color: {value_color};
                font-size: 1rem;
                margin-top: 0.3rem;
            ">{delta}</div>
        """

    html = f"""
    <div style="
        border: 1px solid #2a3f38;
        border-radius: 4px;
        padding: 1rem;
        background-color: #0d1f1a;
        font-family: 'Courier New', Consolas, Monaco, monospace;
        text-align: center;
    ">
        <div style="
            color: #a0a0a0;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 0.5rem;
        ">{label}</div>
        <div style="
            color: {value_color};
            font-size: 1.8rem;
            font-weight: bold;
        ">{value}</div>
        {delta_html}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def render_terminal_section_header(
    title: str,
    subtitle: Optional[str] = None,
    icon: str = ">>>"
) -> None:
    """Render a terminal-styled section header.

    Creates a visually distinct section header with optional subtitle.

    Args:
        title: Main section title
        subtitle: Optional subtitle text
        icon: Icon/prefix for title (default: ">>>")

    Example:
        >>> render_terminal_section_header(
        ...     title="Optimal Hold Time Analysis",
        ...     subtitle="Identify best exit windows for each strategy"
        ... )
    """
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
            <div style="
                color: #a0a0a0;
                font-size: 0.9rem;
                margin-top: 0.3rem;
                font-weight: normal;
            ">{subtitle}</div>
        """

    html = f"""
    <div style="
        font-family: 'Courier New', Consolas, Monaco, monospace;
        margin: 2rem 0 1rem 0;
    ">
        <div style="
            color: #00ff41;
            font-size: 1.4rem;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 2px;
        ">{icon} {title}</div>
        {subtitle_html}
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)
