import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import os
import json

st.set_page_config(page_title="Call Credit Spread Strategy", layout="wide")

st.title("Call Credit Spread Strategy Analysis")

# Load trade data
@st.cache_data
def load_trade_data():
    log_dir = "logs"
    trade_data = None
    
    try:
        # Find the most recent trade data file
        trade_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
        if trade_files:
            latest_file = max(trade_files, key=lambda x: os.path.getctime(os.path.join(log_dir, x)))
            with open(os.path.join(log_dir, latest_file), 'r') as f:
                trade_data = json.load(f)
                st.sidebar.success(f"Loaded trade data from {latest_file}")
        else:
            st.sidebar.warning("No trade data files found in logs directory")
    except Exception as e:
        st.sidebar.error(f"Error loading trade data: {str(e)}")
    
    return trade_data

# Load equity data
@st.cache_data
def load_equity_data():
    try:
        eq_dir = f"SPY"
        
        # Check if directory exists
        if not os.path.exists(eq_dir):
            st.sidebar.error(f"Equity data directory not found: {eq_dir}")
            return None
            
        # Get list of available files
        available_files = []
        for month in [3, 4, 5]:  # Only look for March, April, May
            file_path = os.path.join(eq_dir, f"2025-{month:02d}.parquet")
            if os.path.exists(file_path):
                available_files.append(file_path)
        
        if not available_files:
            st.sidebar.error("No equity data files found in the specified months (March-May)")
            return None
            
        # Read and concatenate available files
        equity_data = pd.concat([pd.read_parquet(f) for f in available_files], ignore_index=True)
        equity_data['ts'] = pd.to_datetime(equity_data['ts'], unit='ms')
        st.sidebar.success(f"Loaded equity data from {len(available_files)} files")
        return equity_data
    except Exception as e:
        st.sidebar.error(f"Error loading equity data: {str(e)}")
        return None

# Load data
equity_data = load_equity_data()
trade_data = load_trade_data()

if equity_data is None or trade_data is None:
    st.error("Unable to load required data. Please ensure data files are available.")
    st.stop()

# Create the main plot
fig = go.Figure()

# Add SPY price line
fig.add_trace(go.Scatter(
    x=equity_data['ts'],
    y=equity_data['c'],
    mode='lines',
    name='SPY Price',
    line=dict(color='blue')
))

# Add entry points
if trade_data['entry_times']:
    entry_times = [datetime.fromisoformat(ts) for ts in trade_data['entry_times']]
    entry_prices = [equity_data[equity_data['ts'] == ts]['c'].values[0] for ts in entry_times]
    fig.add_trace(go.Scatter(
        x=entry_times,
        y=entry_prices,
        mode='markers',
        name='Entry',
        marker=dict(color='green', size=10)
    ))

# Add exit points
if trade_data['exit_times']:
    exit_times = [datetime.fromisoformat(ts) for ts in trade_data['exit_times']]
    exit_prices = [equity_data[equity_data['ts'] == ts]['c'].values[0] for ts in exit_times]
    fig.add_trace(go.Scatter(
        x=exit_times,
        y=exit_prices,
        mode='markers',
        name='Exit',
        marker=dict(color='red', size=10)
    ))

# Add strike lines for the most recent trade
if trade_data['sell_strikes'] and trade_data['buy_strikes']:
    fig.add_hline(
        y=trade_data['sell_strikes'][-1],
        line_dash="dash",
        line_color="orange",
        annotation_text="Sell Strike",
        annotation_position="top left"
    )
    fig.add_hline(
        y=trade_data['buy_strikes'][-1],
        line_dash="dash",
        line_color="purple",
        annotation_text="Buy Strike",
        annotation_position="bottom left"
    )

# Update layout
fig.update_layout(
    title="SPY Call Credit Spread Strategy Simulation",
    xaxis_title="Date",
    yaxis_title="Price",
    legend_title="Legend",
    hovermode="x",
    template="plotly_white",
    height=600
)

# Display the plot
st.plotly_chart(fig, use_container_width=True)

# Display trade statistics
st.subheader("Trade Statistics")
trades_df = pd.DataFrame(trade_data['trades'])

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Trades", len(trades_df))
with col2:
    total_pnl = trades_df['total_pnl'].sum()
    st.metric("Total P&L", f"${total_pnl:.2f}")
with col3:
    win_rate = len(trades_df[trades_df['total_pnl'] > 0]) / len(trades_df) * 100
    st.metric("Win Rate", f"{win_rate:.1f}%")

# Display trade history
st.subheader("Trade History")
st.dataframe(
    trades_df.style.format({
        'credit': '${:.2f}',
        'exit_pnl': '${:.2f}',
        'total_pnl': '${:.2f}',
        'sell_strike': '${:.2f}',
        'buy_strike': '${:.2f}'
    }),
    use_container_width=True
) 