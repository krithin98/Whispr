#!/usr/bin/env python3
"""
Comprehensive Analytics Dashboard
Single source of truth for all ATR level and movement analytics
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import sqlite3
import asyncio
import aiosqlite
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
import json
import sys
import time

# Add backend to path
sys.path.append('backend')

from backend.comprehensive_level_detector import ComprehensiveLevelCalculator
from backend.realtime_level_detector import RealtimeLevelHitDetector
from backend.movement_tracker import MovementTracker

# Page config
st.set_page_config(
    page_title="SPX ATR Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for professional look
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        background-color: #1e1e1e;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 10px;
        color: white;
    }
    .alert-box {
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .bullish { background-color: #10b981; color: white; }
    .bearish { background-color: #ef4444; color: white; }
    .neutral { background-color: #6b7280; color: white; }
</style>
""", unsafe_allow_html=True)

DB_PATH = Path("data/whispr.db")

class ComprehensiveAnalyticsDashboard:
    """Main dashboard class"""

    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.calculator = ComprehensiveLevelCalculator()
        self.session_date = date.today().isoformat()
        self.initialize_session_state()

    def initialize_session_state(self):
        """Initialize session state variables"""
        if 'refresh_interval' not in st.session_state:
            st.session_state.refresh_interval = 5
        if 'selected_timeframe' not in st.session_state:
            st.session_state.selected_timeframe = '5m'
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True

    def get_current_price(self):
        """Get current SPX price"""
        df = pd.read_sql_query("""
            SELECT price, high, low, volume, timestamp
            FROM spx_price_ticks
            ORDER BY timestamp DESC
            LIMIT 1
        """, self.conn)

        if df.empty:
            return 6664.36, None

        return df.iloc[0]['price'], df.iloc[0]['timestamp']

    def get_atr_levels(self, timeframe):
        """Get ATR levels for timeframe"""
        df = pd.read_sql_query("""
            SELECT * FROM atr_levels
            WHERE timeframe = ? AND session_date = ?
        """, self.conn, params=(timeframe, self.session_date))

        if df.empty:
            return None

        return df.iloc[0]

    def create_level_chart(self, timeframe, current_price):
        """Create interactive level chart"""
        atr_data = self.get_atr_levels(timeframe)
        if atr_data is None:
            return None

        # Calculate all 28 levels
        levels = self.calculator.calculate_all_levels(
            pdc=atr_data['previous_close'],
            atr_value=atr_data['atr_value'],
            timeframe=timeframe
        )

        fig = go.Figure()

        # Add horizontal lines for each level
        colors = {
            'upper': '#10b981',  # Green
            'lower': '#ef4444',  # Red
            'neutral': '#6366f1'  # Blue
        }

        for level_name, level in levels.items():
            if 'beyond' in level_name:
                continue

            color = colors.get(level.direction, '#6b7280')
            width = 3 if level_name == 'PDC' else 2 if '1000' in level_name else 1

            fig.add_hline(
                y=level.value,
                line_color=color,
                line_width=width,
                line_dash="solid" if level_name == 'PDC' else "dash",
                annotation_text=f"{level_name} ({level.fib_ratio:+.1%})",
                annotation_position="right"
            )

        # Add current price marker
        fig.add_scatter(
            x=[datetime.now()],
            y=[current_price],
            mode='markers',
            marker=dict(size=15, color='#fbbf24', symbol='diamond'),
            name='Current Price'
        )

        # Add price line
        price_history = pd.read_sql_query("""
            SELECT timestamp, price
            FROM spx_price_ticks
            WHERE DATE(timestamp) = DATE('now')
            ORDER BY timestamp
        """, self.conn)

        if not price_history.empty:
            fig.add_scatter(
                x=pd.to_datetime(price_history['timestamp']),
                y=price_history['price'],
                mode='lines',
                line=dict(color='#fbbf24', width=2),
                name='SPX Price'
            )

        fig.update_layout(
            title=f"SPX Levels - {timeframe}",
            xaxis_title="Time",
            yaxis_title="Price ($)",
            height=600,
            hovermode='x unified',
            template='plotly_dark'
        )

        return fig

    def get_level_hits(self, limit=20):
        """Get recent level hits"""
        df = pd.read_sql_query("""
            SELECT
                hit_time,
                timeframe,
                level_name,
                level_value,
                hit_price,
                direction,
                fib_ratio
            FROM level_hits
            WHERE session_date = ?
            ORDER BY hit_time DESC
            LIMIT ?
        """, self.conn, params=(self.session_date, limit))

        return df

    def get_movement_stats(self, timeframe=None):
        """Get movement statistics"""
        where_clause = "WHERE h1.session_date = ?"
        params = [self.session_date]

        if timeframe:
            where_clause += " AND h1.timeframe = ?"
            params.append(timeframe)

        df = pd.read_sql_query(f"""
            SELECT
                h1.level_name as from_level,
                h2.level_name as to_level,
                h1.timeframe,
                COUNT(*) as count,
                AVG(CAST((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400 AS REAL)) as avg_duration,
                MIN(CAST((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400 AS REAL)) as min_duration,
                MAX(CAST((julianday(h2.hit_time) - julianday(h1.hit_time)) * 86400 AS REAL)) as max_duration
            FROM level_hits h1
            JOIN level_hits h2 ON h1.next_level_hit_id = h2.id
            {where_clause}
            GROUP BY h1.level_name, h2.level_name, h1.timeframe
            ORDER BY count DESC
        """, self.conn, params=params)

        return df

    def get_pattern_detections(self):
        """Get detected patterns"""
        df = pd.read_sql_query("""
            SELECT
                detection_time,
                timeframe,
                pattern_type,
                from_level,
                to_level,
                duration_seconds,
                price_change
            FROM movement_patterns
            WHERE session_date = ?
            ORDER BY detection_time DESC
            LIMIT 50
        """, self.conn, params=(self.session_date,))

        return df

    def calculate_position_metrics(self, current_price, timeframe):
        """Calculate position metrics"""
        atr_data = self.get_atr_levels(timeframe)
        if atr_data is None:
            return None

        pdc = atr_data['previous_close']
        atr = atr_data['atr_value']

        distance = current_price - pdc
        atr_multiple = distance / atr if atr > 0 else 0
        percentage = (distance / pdc) * 100 if pdc > 0 else 0

        # Calculate nearest levels
        levels = self.calculator.calculate_all_levels(pdc, atr, timeframe)
        position = self.calculator.get_price_position(current_price, timeframe)

        return {
            'pdc': pdc,
            'atr': atr,
            'distance': distance,
            'atr_multiple': atr_multiple,
            'percentage': percentage,
            'position': position
        }

    def display_header_metrics(self):
        """Display header metrics"""
        current_price, timestamp = self.get_current_price()

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric(
                "SPX Price",
                f"${current_price:,.2f}",
                f"{current_price - 6664.36:+.2f}"
            )

        # Get 5m position for quick reference
        metrics_5m = self.calculate_position_metrics(current_price, '5m')

        with col2:
            if metrics_5m:
                st.metric(
                    "ATR Multiple (5m)",
                    f"{metrics_5m['atr_multiple']:+.3f}",
                    f"{metrics_5m['percentage']:+.2f}%"
                )

        with col3:
            # Count today's hits
            hit_count = pd.read_sql_query("""
                SELECT COUNT(*) as count
                FROM level_hits
                WHERE session_date = ?
            """, self.conn, params=(self.session_date,)).iloc[0]['count']

            st.metric("Level Hits Today", hit_count)

        with col4:
            # Count patterns detected
            pattern_count = pd.read_sql_query("""
                SELECT COUNT(*) as count
                FROM movement_patterns
                WHERE session_date = ?
            """, self.conn, params=(self.session_date,)).iloc[0]['count']

            st.metric("Patterns Detected", pattern_count)

        with col5:
            # System health
            last_tick_time = pd.to_datetime(timestamp) if timestamp else None
            if last_tick_time:
                age = (datetime.now(timezone.utc) - last_tick_time.replace(tzinfo=timezone.utc)).total_seconds()
                if age < 60:
                    st.metric("System Status", "✅ Live", f"{age:.0f}s ago")
                elif age < 300:
                    st.metric("System Status", "⚠️ Delayed", f"{age/60:.1f}m ago")
                else:
                    st.metric("System Status", "❌ Stale", f"{age/60:.0f}m ago")
            else:
                st.metric("System Status", "❌ No Data")

    def display_trading_insights(self, current_price):
        """Display trading insights panel"""
        st.subheader("🎯 Trading Insights")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Next Key Levels")

            for tf in ['5m', '15m', '30m', '1h']:
                metrics = self.calculate_position_metrics(current_price, tf)
                if metrics and metrics['position']:
                    pos = metrics['position']

                    if pos['nearest_above']:
                        next_up = pos['nearest_above'][0]
                        st.markdown(
                            f"**{tf}** ↑ {next_up['name']} @ "
                            f"${next_up['value']:.2f} (${next_up['distance']:.2f})"
                        )

        with col2:
            st.markdown("#### Active Patterns")

            # Get recent patterns
            patterns = self.get_pattern_detections()
            if not patterns.empty:
                for _, pattern in patterns.head(5).iterrows():
                    emoji = "🟢" if "bull" in pattern['pattern_type'].lower() else "🔴"
                    st.markdown(
                        f"{emoji} **{pattern['pattern_type']}** [{pattern['timeframe']}] "
                        f"{pattern['from_level']} → {pattern['to_level']}"
                    )
            else:
                st.info("No patterns detected yet today")

    def display_movement_analytics(self):
        """Display movement analytics"""
        st.subheader("📊 Movement Analytics")

        # Get movement statistics
        stats = self.get_movement_stats()

        if not stats.empty:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### Most Frequent Transitions")
                top_transitions = stats.head(10)[['from_level', 'to_level', 'count', 'avg_duration']]
                top_transitions['avg_duration'] = top_transitions['avg_duration'].apply(
                    lambda x: f"{x:.1f}s" if x < 60 else f"{x/60:.1f}m"
                )
                st.dataframe(top_transitions, hide_index=True)

            with col2:
                st.markdown("#### Transition Velocity")
                # Create velocity chart
                fig = px.bar(
                    stats.head(10),
                    x='count',
                    y=stats['from_level'] + ' → ' + stats['to_level'],
                    orientation='h',
                    title="Transition Frequency"
                )
                fig.update_layout(height=400, template='plotly_dark')
                st.plotly_chart(fig, use_container_width=True)

    def run(self):
        """Main dashboard loop"""
        st.title("🎯 SPX ATR Analytics Dashboard")

        # Header metrics
        self.display_header_metrics()

        # Create tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Live Levels",
            "🎯 Trading Insights",
            "📊 Movement Analytics",
            "📋 Level Hits",
            "⚙️ System"
        ])

        current_price, _ = self.get_current_price()

        with tab1:
            # Timeframe selector
            timeframes = ['5m', '15m', '30m', '1h', '2h', '4h', 'daily', 'weekly']
            selected_tf = st.selectbox("Select Timeframe", timeframes)

            # Level chart
            chart = self.create_level_chart(selected_tf, current_price)
            if chart:
                st.plotly_chart(chart, use_container_width=True)

            # Position details
            metrics = self.calculate_position_metrics(current_price, selected_tf)
            if metrics:
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("PDC", f"${metrics['pdc']:.2f}")
                with col2:
                    st.metric("ATR", f"${metrics['atr']:.2f}")
                with col3:
                    st.metric("Current Zone", metrics['position']['current_zone'] if metrics['position'] else "Unknown")

        with tab2:
            self.display_trading_insights(current_price)

            # High probability setups
            st.markdown("#### High Probability Setups")

            # Check for Golden Gate setups
            for tf in ['5m', '15m', '30m']:
                metrics = self.calculate_position_metrics(current_price, tf)
                if metrics and metrics['position']:
                    pos = metrics['position']

                    # Check if near 0.382 level
                    for level in pos['nearest_above'][:2] + pos['nearest_below'][:2]:
                        if '0382' in level['name'] and level['distance'] < metrics['atr'] * 0.1:
                            direction = "Bullish" if "upper" in level['name'] else "Bearish"
                            st.success(
                                f"🎯 **{direction} Golden Gate Setup** [{tf}] - "
                                f"Near {level['name']} @ ${level['value']:.2f}"
                            )

        with tab3:
            self.display_movement_analytics()

            # Pattern success rates
            st.markdown("#### Pattern Success Rates")
            patterns = pd.read_sql_query("""
                SELECT
                    pattern_type,
                    COUNT(*) as occurrences,
                    AVG(duration_seconds) as avg_duration,
                    AVG(ABS(price_change)) as avg_price_move
                FROM movement_patterns
                GROUP BY pattern_type
                ORDER BY occurrences DESC
            """, self.conn)

            if not patterns.empty:
                st.dataframe(patterns, hide_index=True)

        with tab4:
            st.subheader("Recent Level Hits")

            # Refresh button
            if st.button("🔄 Refresh"):
                st.rerun()

            # Get recent hits
            hits = self.get_level_hits(50)
            if not hits.empty:
                hits['hit_time'] = pd.to_datetime(hits['hit_time'])
                hits['hit_time'] = hits['hit_time'].dt.strftime('%H:%M:%S')

                # Color code by direction
                def color_direction(val):
                    if val == 'up':
                        return 'background-color: #10b981'
                    elif val == 'down':
                        return 'background-color: #ef4444'
                    return ''

                styled_hits = hits.style.applymap(color_direction, subset=['direction'])
                st.dataframe(styled_hits, hide_index=True)
            else:
                st.info("No level hits recorded today")

        with tab5:
            st.subheader("System Configuration")

            col1, col2 = st.columns(2)

            with col1:
                # Auto refresh toggle
                auto_refresh = st.checkbox("Auto Refresh", value=st.session_state.auto_refresh)
                st.session_state.auto_refresh = auto_refresh

                # Refresh interval
                interval = st.slider(
                    "Refresh Interval (seconds)",
                    min_value=1,
                    max_value=60,
                    value=st.session_state.refresh_interval
                )
                st.session_state.refresh_interval = interval

            with col2:
                # System stats
                st.markdown("#### Database Statistics")

                tick_count = pd.read_sql_query("""
                    SELECT COUNT(*) as count
                    FROM spx_price_ticks
                    WHERE DATE(timestamp) = DATE('now')
                """, self.conn).iloc[0]['count']

                st.metric("Price Ticks Today", tick_count)

                # Token status
                token_data = pd.read_sql_query("""
                    SELECT * FROM events
                    WHERE event_type = 'token_refresh'
                    ORDER BY ts DESC
                    LIMIT 1
                """, self.conn)

                if not token_data.empty:
                    st.info(f"Last Token Refresh: {token_data.iloc[0]['ts']}")

        # Auto refresh
        if st.session_state.auto_refresh:
            time.sleep(st.session_state.refresh_interval)
            st.rerun()


def main():
    dashboard = ComprehensiveAnalyticsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()