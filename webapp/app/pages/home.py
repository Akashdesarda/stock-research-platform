"""
Home Page - StockSense Stock Research Platform
"""

import streamlit as st



st.title("🏠 Welcome to StockSense")
st.markdown("---")

st.markdown("""
## Your Stock Research Platform

Welcome to **StockSense** - a simple platform for stock research and analysis.

### 🚀 Features:

- **📊 Data Analysis**: View stock data
- **🎯 Strategy Development**: Build trading strategies  
- **💬 AI Chat**: Investment assistant
- **🔍 Research**: Market research tools
""")

# Quick navigation
st.subheader("🧭 Navigation")

col1, col2 = st.columns(2)

with col1:
    st.info("📊 **Data Detail View** - Explore stock data")
    st.info("💬 **Chat** - AI assistant")

with col2:
    st.info("🎯 **Strategy** - Trading strategies")
    st.info("🔍 **Research** - Market research")

st.success("Use the navigation menu on the left to explore different sections!")
