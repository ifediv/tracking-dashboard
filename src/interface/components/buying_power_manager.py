"""Buying Power Manager UI Component for Streamlit.

Provides interface for:
- Viewing current buying power
- Adding new buying power changes
- Editing existing entries
- Viewing history of changes
"""

import streamlit as st
from datetime import datetime
from sqlalchemy.orm import Session

from src.database.operations import (
    create_buying_power_entry,
    get_all_buying_power_entries,
    update_buying_power_entry,
    delete_buying_power_entry,
    get_buying_power_for_date
)


def render_buying_power_manager(session: Session):
    """Render the buying power management interface.

    Args:
        session: Active database session

    Example:
        >>> with get_session() as session:
        ...     render_buying_power_manager(session)
    """
    st.markdown("### [BUYING POWER MANAGEMENT]")

    # Get current buying power
    today = datetime.now().strftime('%Y-%m-%d')
    current_bp = get_buying_power_for_date(session, today)

    # Display current BP
    if current_bp > 0:
        st.markdown(f"""
        <div style="font-family: 'Courier New', Consolas, Monaco, monospace; margin-bottom: 1rem;">
            <div style="color: #a0a0a0; text-transform: uppercase; font-size: 0.8rem; letter-spacing: 1px;">CURRENT BUYING POWER</div>
            <div style="color: #00ff41; font-size: 2rem; font-weight: bold;">${current_bp:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("[WARN] No buying power configured. Please add an entry below.")

    st.divider()

    # Add new entry form
    with st.expander("[ADD NEW BUYING POWER ENTRY]", expanded=(current_bp == 0)):
        with st.form("add_bp_entry"):
            col1, col2 = st.columns(2)

            with col1:
                effective_date = st.date_input(
                    "Effective Date",
                    help="Date when this buying power amount takes effect"
                )

            with col2:
                bp_amount = st.number_input(
                    "Buying Power Amount ($)",
                    min_value=0.0,
                    step=10000.0,
                    format="%.2f",
                    help="Total buying power in dollars"
                )

            notes = st.text_area(
                "Notes (Optional)",
                help="E.g., 'Initial funding', 'Account size increased', etc."
            )

            submitted = st.form_submit_button("[SUBMIT]", use_container_width=True)

            if submitted:
                try:
                    if bp_amount <= 0:
                        st.error("[ERROR] Buying power must be greater than zero")
                    else:
                        date_str = effective_date.strftime('%Y-%m-%d')
                        entry = create_buying_power_entry(
                            session,
                            effective_date=date_str,
                            buying_power_amount=bp_amount,
                            notes=notes if notes else None
                        )
                        session.commit()
                        st.success(f"[OK] Created buying power entry for {date_str}")
                        st.rerun()
                except ValueError as e:
                    st.error(f"[ERROR] {str(e)}")

    st.divider()

    # Show existing entries
    st.markdown("### [BUYING POWER HISTORY]")

    entries = get_all_buying_power_entries(session)

    if not entries:
        st.info("[INFO] No buying power history. Add an entry above to get started.")
    else:
        # Display as table
        st.markdown(f"**Total Entries:** {len(entries)}")

        for i, entry in enumerate(entries):
            with st.expander(f"**{entry.effective_date}** - ${entry.buying_power_amount:,.0f}"):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    st.markdown(f"""
                    **Date:** {entry.effective_date}
                    **Amount:** ${entry.buying_power_amount:,.0f}
                    """)

                with col2:
                    st.markdown(f"""
                    **Notes:** {entry.notes or 'None'}
                    **Created:** {entry.created_at[:10]}
                    """)

                with col3:
                    # Delete button
                    if st.button("[DELETE]", key=f"delete_{entry.bp_id}"):
                        if delete_buying_power_entry(session, entry.bp_id):
                            session.commit()
                            st.success(f"[OK] Deleted entry for {entry.effective_date}")
                            st.rerun()
                        else:
                            st.error("[ERROR] Failed to delete entry")

                # Edit form
                with st.form(f"edit_{entry.bp_id}"):
                    st.markdown("**Edit Entry:**")

                    edit_col1, edit_col2 = st.columns(2)

                    with edit_col1:
                        new_date = st.date_input(
                            "Date",
                            value=datetime.strptime(entry.effective_date, '%Y-%m-%d'),
                            key=f"date_{entry.bp_id}"
                        )

                    with edit_col2:
                        new_amount = st.number_input(
                            "Amount ($)",
                            value=float(entry.buying_power_amount),
                            min_value=0.0,
                            step=10000.0,
                            format="%.2f",
                            key=f"amount_{entry.bp_id}"
                        )

                    new_notes = st.text_area(
                        "Notes",
                        value=entry.notes or "",
                        key=f"notes_{entry.bp_id}"
                    )

                    if st.form_submit_button("[UPDATE]", use_container_width=True):
                        try:
                            updates = {
                                'effective_date': new_date.strftime('%Y-%m-%d'),
                                'buying_power_amount': new_amount,
                                'notes': new_notes if new_notes else None
                            }
                            update_buying_power_entry(session, entry.bp_id, updates)
                            session.commit()
                            st.success(f"[OK] Updated entry")
                            st.rerun()
                        except Exception as e:
                            st.error(f"[ERROR] {str(e)}")

    st.divider()
    st.caption("[INFO] Buying power changes are used to calculate opportunity cost vs SPY")
