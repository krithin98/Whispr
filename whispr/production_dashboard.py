#!/usr/bin/env python3
"""
Production SPX ATR Level Dashboard
Shows real-time accurate levels using production calculator.
"""

import streamlit as st
import sys
import os
import time
from datetime import datetime

# Add backend path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

try:
    from production_atr_calculator import ProductionATRCalculator
    from data_collector import get_data_collector
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

st.set_page_config(
    page_title="🎯 SPX ATR Production Monitor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_atr_levels(timeframe):
    """Get production ATR levels with caching."""
    try:
        calc = ProductionATRCalculator()
        levels = calc.calculate_production_atr_levels(timeframe)
        return levels
    except Exception as e:
        st.error(f"ATR calculation error: {e}")
        return None

def get_live_price():
    """Get current SPX price."""
    try:
        from data_collector import SchwabDataCollector
        from schwab_config import get_oauth_manager
        collector = SchwabDataCollector(get_oauth_manager())
        tick = collector.get_current_price("SPX")
        return tick.price
    except Exception as e:
        print(f"Live price error: {e}")
        return None

    """Get current SPX price."""
    try:
        from data_collector import SchwabDataCollector
        tick = collector.get_current_price("SPX")
        return tick.price
    except Exception as e:
        st.error(f"Live price error: {e}")
        return None

def main():
    st.title("🎯 SPX ATR Production Monitor")
    st.markdown("**Live Accurate ATR Levels - Ready for Market Open**")
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Controls")
        timeframe = st.selectbox(
            "Timeframe", 
            ["day", "multiday"],
            help="Day: 14-period (100% accurate) | Multiday: 20-period (99.2% accurate)"
        )
        
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_seconds = st.slider("Refresh Rate (seconds)", 5, 60, 10)
        
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
    
    # Get data
    levels = get_atr_levels(timeframe)
    current_price = get_live_price()
    
    if not levels:
        st.error("❌ Failed to get ATR levels")
        return
    
    # Current price display
    if current_price:
        price_color = "🟢" if current_price > levels.previous_close else "🔴"
        change = current_price - levels.previous_close
        change_pct = (change / levels.previous_close) * 100
        
        st.metric(
            f"📈 Current SPX Price {price_color}",
            f"${current_price:.2f}",
            f"{change:+.2f} ({change_pct:+.2f}%)"
        )
    else:
        st.warning("⚠️ Live price unavailable (after hours)")
    
    # ATR Information
    st.subheader(f"📊 {timeframe.title()} ATR Levels")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("ATR Value", f"${levels.atr:.2f}")
        st.caption(f"Period: {levels.period_used}")
    
    with col2:
        st.metric("Previous Close", f"${levels.previous_close:.2f}")
        st.caption(f"Bars Used: {levels.historical_bars_used}")
    
    with col3:
        st.metric("Put Trigger", f"${levels.put_trigger:.2f}")
        st.caption("Entry below this")
    
    with col4:
        st.metric("Call Trigger", f"${levels.call_trigger:.2f}")
        st.caption("Entry above this")
    
    # Key Levels Table
    st.subheader("🎯 Key Trading Levels")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔴 Support Levels**")
        support_data = {
            "Level": ["Put Trigger", "38.2% Fib", "61.8% Fib", "-1 ATR", "-2 ATR"],
            "Price": [
                f"${levels.put_trigger:.2f}",
                f"${levels.lower_0382:.2f}",
                f"${levels.lower_0618:.2f}",
                f"${levels.minus_1_atr:.2f}",
                f"${levels.minus_2_atr:.2f}"
            ]
        }
        st.table(support_data)
    
    with col2:
        st.markdown("**🟢 Resistance Levels**")
        resistance_data = {
            "Level": ["Call Trigger", "38.2% Fib", "61.8% Fib", "+1 ATR", "+2 ATR"],
            "Price": [
                f"${levels.call_trigger:.2f}",
                f"${levels.upper_0382:.2f}",
                f"${levels.upper_0618:.2f}",
                f"${levels.plus_1_atr:.2f}",
                f"${levels.plus_2_atr:.2f}"
            ]
        }
        st.table(resistance_data)
    
    # Current Position Analysis
    if current_price:
        st.subheader("🎯 Current Market Position")
        
        if current_price < levels.put_trigger:
            st.success("🟢 **PUT TRIGGER ACTIVATED** - Consider put entries")
        elif current_price > levels.call_trigger:
            st.success("🟢 **CALL TRIGGER ACTIVATED** - Consider call entries")
        else:
            st.info("⚪ **NEUTRAL ZONE** - Between triggers")
        
        # Distance analysis
        put_distance = abs(current_price - levels.put_trigger)
        call_distance = abs(current_price - levels.call_trigger)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Distance to Put Trigger", f"${put_distance:.2f}")
        with col2:
            st.metric("Distance to Call Trigger", f"${call_distance:.2f}")
    
    # Metadata
    with st.expander("🔍 Calculation Details"):
        st.write(f"**Timeframe:** {levels.timeframe}")
        st.write(f"**Period Used:** {levels.period_used}")
        st.write(f"**Historical Bars:** {levels.historical_bars_used}")
        st.write(f"**Accuracy:** {levels.accuracy_note}")
        st.write(f"**Last Updated:** {levels.calculation_timestamp}")
    
    # Auto refresh
    if auto_refresh:
        time.sleep(refresh_seconds)
        st.rerun()

if __name__ == "__main__":
    main()
