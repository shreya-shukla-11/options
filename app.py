import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import datetime
import os
import json
from plotly.subplots import make_subplots

# Page config
st.set_page_config(
    page_title="Options Strategy Analysis",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .plot-container {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

def load_trade_data():
    """Load the most recent trade data from logs directory"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        st.error("Logs directory not found!")
        return None
    
    # Find the most recent trade data file
    trade_files = [f for f in os.listdir(log_dir) if f.startswith("trade_data_")]
    if not trade_files:
        st.error("No trade data files found!")
        return None
    
    latest_file = max(trade_files)
    with open(os.path.join(log_dir, latest_file), 'r') as f:
        return json.load(f)

def load_equity_data():
    """Load equity data from parquet files"""
    data_dir = "SPY"  # SPY directory in current folder
    if not os.path.exists(data_dir):
        st.error(f"Data directory not found: {data_dir}")
        return None
    
    # Load parquet files for March, April, May
    files = []
    for month in [3, 4, 5]:
        file_path = os.path.join(data_dir, f"2025-{month:02d}.parquet")
        if os.path.exists(file_path):
            files.append(pd.read_parquet(file_path))
    
    if not files:
        st.error("No equity data files found!")
        return None
    
    # Combine all data
    df = pd.concat(files, ignore_index=True)
    df['ts'] = pd.to_datetime(df['ts'], unit='ms')
    return df

def plot_trade_analysis(trade_data):
    """Create trade analysis plots"""
    # Convert trade data to DataFrame
    trades_df = pd.DataFrame(trade_data)
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    trades_df['cumulative_pnl'] = trades_df['total_pnl'].cumsum()
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Cumulative P&L', 'P&L Distribution', 
                       'Win Rate by Month', 'Average P&L by Month'),
        specs=[[{"type": "scatter"}, {"type": "histogram"}],
               [{"type": "bar"}, {"type": "bar"}]]
    )
    
    # Cumulative P&L
    fig.add_trace(
        go.Scatter(x=trades_df['date'], y=trades_df['cumulative_pnl'],
                  mode='lines+markers', name='Cumulative P&L'),
        row=1, col=1
    )
    
    # P&L Distribution
    fig.add_trace(
        go.Histogram(x=trades_df['total_pnl'], nbinsx=20, name='P&L Distribution'),
        row=1, col=2
    )
    
    # Monthly Analysis
    trades_df['month'] = trades_df['date'].dt.strftime('%Y-%m')
    monthly_stats = trades_df.groupby('month').agg({
        'total_pnl': ['count', 'mean', lambda x: (x > 0).mean()]
    }).reset_index()
    
    # Win Rate by Month
    fig.add_trace(
        go.Bar(x=monthly_stats['month'], 
               y=monthly_stats[('total_pnl', '<lambda_0>')] * 100,
               name='Win Rate'),
        row=2, col=1
    )
    
    # Average P&L by Month
    fig.add_trace(
        go.Bar(x=monthly_stats['month'], 
               y=monthly_stats[('total_pnl', 'mean')],
               name='Avg P&L'),
        row=2, col=2
    )
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=False,
        title_text="Trade Analysis Dashboard",
        title_x=0.5
    )
    
    # Update axes labels
    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1)
    fig.update_xaxes(title_text="P&L ($)", row=1, col=2)
    fig.update_yaxes(title_text="Frequency", row=1, col=2)
    fig.update_xaxes(title_text="Month", row=2, col=1)
    fig.update_yaxes(title_text="Win Rate (%)", row=2, col=1)
    fig.update_xaxes(title_text="Month", row=2, col=2)
    fig.update_yaxes(title_text="Average P&L ($)", row=2, col=2)
    
    return fig

def plot_trade_details(trade_data, equity_data):
    """Create detailed trade visualization"""
    # Check if data is empty or None
    if trade_data is None or equity_data is None:
        return None
    
    # Convert trade data to DataFrame if it's not already
    if isinstance(trade_data, list):
        trades_df = pd.DataFrame(trade_data)
    else:
        trades_df = trade_data
        
    if trades_df.empty or equity_data.empty:
        return None
    
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    
    # Create figure
    fig = go.Figure()
    
    # Add SPY price
    fig.add_trace(go.Scatter(
        x=equity_data['ts'],
        y=equity_data['c'],
        mode='lines',
        name='SPY Price',
        line=dict(color='blue', width=1)
    ))
    
    # Add entry and exit points
    for _, trade in trades_df.iterrows():
        # Find the closest price point for entry and exit times
        entry_price = equity_data[equity_data['ts'] == trade['entry_time']]['c']
        exit_price = equity_data[equity_data['ts'] == trade['exit_time']]['c']
        
        if not entry_price.empty and not exit_price.empty:
            # Entry point
            fig.add_trace(go.Scatter(
                x=[trade['entry_time']],
                y=[entry_price.iloc[0]],
                mode='markers',
                marker=dict(symbol='triangle-up', size=10, color='green'),
                name=f"Entry {trade['date'].date()}",
                showlegend=False
            ))
            
            # Exit point
            fig.add_trace(go.Scatter(
                x=[trade['exit_time']],
                y=[exit_price.iloc[0]],
                mode='markers',
                marker=dict(symbol='triangle-down', size=10, color='red'),
                name=f"Exit {trade['date'].date()}",
                showlegend=False
            ))
            
            # Add strike lines
            fig.add_trace(go.Scatter(
                x=[trade['entry_time'], trade['exit_time']],
                y=[trade['sell_strike'], trade['sell_strike']],
                mode='lines',
                line=dict(color='orange', width=1, dash='dash'),
                name=f"Sell Strike {trade['date'].date()}",
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=[trade['entry_time'], trade['exit_time']],
                y=[trade['buy_strike'], trade['buy_strike']],
                mode='lines',
                line=dict(color='purple', width=1, dash='dash'),
                name=f"Buy Strike {trade['date'].date()}",
                showlegend=False
            ))
    
    # Update layout
    fig.update_layout(
        title="Trade Details with SPY Price",
        xaxis_title="Time",
        yaxis_title="Price",
        height=600,
        showlegend=True
    )
    
    return fig

def main():
    st.title("Options Strategy Analysis")
    
    # Load data
    trade_data = load_trade_data()
    equity_data = load_equity_data()
    
    if trade_data is None or equity_data is None:
        st.error("Failed to load required data!")
        return
    
    # Convert trade data to DataFrame for metrics
    trades_df = pd.DataFrame(trade_data)
    trades_df['date'] = pd.to_datetime(trades_df['date'])
    
    # Calculate metrics
    total_trades = len(trades_df)
    total_pnl = trades_df['total_pnl'].sum()
    win_rate = (trades_df['total_pnl'] > 0).mean() * 100
    avg_pnl = trades_df['total_pnl'].mean()
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Trades", total_trades)
    with col2:
        st.metric("Total P&L", f"${total_pnl:.2f}")
    with col3:
        st.metric("Win Rate", f"{win_rate:.1f}%")
    with col4:
        st.metric("Average P&L", f"${avg_pnl:.2f}")
    
    # Trade Analysis Plots
    st.markdown("### Trade Analysis")
    trade_analysis_fig = plot_trade_analysis(trade_data)
    st.plotly_chart(trade_analysis_fig, use_container_width=True)
    
    # Trade Details Plot
    st.markdown("### Trade Details")
    trade_details_fig = plot_trade_details(trade_data, equity_data)
    if trade_details_fig:
        st.plotly_chart(trade_details_fig, use_container_width=True)
    
    # Trade History Table
    st.markdown("### Trade History")
    trades_df['date'] = trades_df['date'].dt.date
    trades_df['entry_time'] = pd.to_datetime(trades_df['entry_time']).dt.time
    trades_df['exit_time'] = pd.to_datetime(trades_df['exit_time']).dt.time
    
    # Format columns
    display_df = trades_df[[
        'date', 'entry_time', 'exit_time', 'sell_strike', 'buy_strike',
        'credit', 'total_pnl', 'iv', 'sell_delta'
    ]].copy()
    
    display_df.columns = [
        'Date', 'Entry Time', 'Exit Time', 'Sell Strike', 'Buy Strike',
        'Credit', 'P&L', 'IV', 'Sell Delta'
    ]
    
    # Format numeric columns with proper handling of None values
    def format_currency(x):
        return f"${x:.2f}" if pd.notnull(x) else "N/A"
    
    def format_percentage(x):
        return f"{x:.2%}" if pd.notnull(x) else "N/A"
    
    # Apply formatting
    display_df['Sell Strike'] = display_df['Sell Strike'].apply(format_currency)
    display_df['Buy Strike'] = display_df['Buy Strike'].apply(format_currency)
    display_df['Credit'] = display_df['Credit'].apply(format_currency)
    display_df['P&L'] = display_df['P&L'].apply(format_currency)
    display_df['IV'] = display_df['IV'].apply(format_percentage)
    display_df['Sell Delta'] = display_df['Sell Delta'].apply(format_percentage)
    
    st.dataframe(display_df, use_container_width=True)

if __name__ == "__main__":
    main() 