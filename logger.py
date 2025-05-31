import logging
from datetime import datetime
import os
from fpdf import FPDF
import pandas as pd
import json
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class StrategyLogger:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_dir = "logs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Set up logging
        self.logger = logging.getLogger("StrategyLogger")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(os.path.join(self.log_dir, f"strategy_{self.timestamp}.log"))
        fh.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        
        # Initialize trade data
        self.trades = []
        self.equity_data = None
        self.options_data = None
        
    def log_data_summary(self, equity_data, options_data):
        """Log summary of loaded data"""
        self.equity_data = equity_data
        self.options_data = options_data
        
        self.logger.info("=== Data Summary ===")
        self.logger.info(f"Equity Data Rows: {len(equity_data)}")
        self.logger.info(f"Options Data Rows: {len(options_data)}")
        
        if not equity_data.empty:
            date_range = f"{equity_data['ts'].min()} to {equity_data['ts'].max()}"
            self.logger.info(f"Date Range: {date_range}")
    
    def log_strategy_details(self, strategy_details=None):
        """Log strategy parameters and configuration"""
        self.logger.info("\n=== Strategy Details ===")
        
        if strategy_details:
            for key, value in strategy_details.items():
                if isinstance(value, list):
                    self.logger.info(f"{key}:")
                    for item in value:
                        self.logger.info(f"  - {item}")
                elif isinstance(value, dict):
                    self.logger.info(f"{key}:")
                    for k, v in value.items():
                        self.logger.info(f"  - {k}: {v}")
                else:
                    self.logger.info(f"{key}: {value}")
        else:
            self.logger.info("No strategy details provided")
    
    def log_trade(self, trading_day, entry_time, exit_time, sell_strike, buy_strike, 
                 credit, exit_pnl, total_pnl, atm_strike=None, iv=None, sell_delta=None):
        """Log individual trade details"""
        trade = {
            'date': trading_day,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'sell_strike': sell_strike,
            'buy_strike': buy_strike,
            'credit': credit,
            'exit_pnl': exit_pnl,
            'total_pnl': total_pnl,
            'atm_strike': atm_strike,
            'iv': iv,
            'sell_delta': sell_delta
        }
        self.trades.append(trade)
        
        self.logger.info(f"\n=== Trade Executed ===")
        self.logger.info(f"Date: {trading_day}")
        self.logger.info(f"Entry Time: {entry_time}")
        self.logger.info(f"Exit Time: {exit_time}")
        self.logger.info(f"Sell Strike: {sell_strike}")
        self.logger.info(f"Buy Strike: {buy_strike}")
        self.logger.info(f"Credit: ${credit:.2f}")
        self.logger.info(f"Exit P&L: ${exit_pnl:.2f}")
        self.logger.info(f"Total P&L: ${total_pnl:.2f}")
        if atm_strike:
            self.logger.info(f"ATM Strike: {atm_strike}")
        if iv:
            self.logger.info(f"IV: {iv:.4f}")
        if sell_delta:
            self.logger.info(f"Sell Delta: {sell_delta:.4f}")
    
    def get_trade_data(self):
        """Get all trade data for analysis"""
        return self.trades
    
    def generate_pdf_report(self):
        """Generate PDF report with trade analysis and charts"""
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, 'Options Strategy Report', 0, 1, 'C')
        pdf.ln(10)
        
        # Strategy Details
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Strategy Details', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        strategy_text = """
        Entry Conditions:
        - Entry Time: 9:15 AM US time
        - Sell leg delta < 0.03
        - Minimum credit between legs: $0.1
        - Buy leg: Nearest strike above sell leg
        
        Capital Requirements:
        - $500 per lot
        
        Profit Targets:
        - Gross: $10
        - Net: $7.5 (after 1.5% charges)
        
        Stop Loss:
        - Exit if spread value reaches $0.3
        - Exit at market close (4:00 PM)
        """
        pdf.multi_cell(0, 10, strategy_text)
        pdf.ln(10)
        
        # Strategy Summary
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Strategy Summary', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        trades_df = pd.DataFrame(self.trades)
        if not trades_df.empty:
            total_trades = len(trades_df)
            total_pnl = trades_df['total_pnl'].sum()
            avg_pnl = trades_df['total_pnl'].mean()
            win_rate = (trades_df['total_pnl'] > 0).mean() * 100
            
            # Calculate delta statistics
            avg_sell_delta = trades_df['sell_delta'].mean()
            min_sell_delta = trades_df['sell_delta'].min()
            max_sell_delta = trades_df['sell_delta'].max()
            
            # Calculate IV statistics
            avg_iv = trades_df['iv'].mean()
            min_iv = trades_df['iv'].min()
            max_iv = trades_df['iv'].max()
            
            # Calculate credit statistics
            avg_credit = trades_df['credit'].mean()
            min_credit = trades_df['credit'].min()
            max_credit = trades_df['credit'].max()
            
            pdf.multi_cell(0, 10, f'Total Trades: {total_trades}')
            pdf.multi_cell(0, 10, f'Total P&L: ${total_pnl:.2f}')
            pdf.multi_cell(0, 10, f'Average P&L per Trade: ${avg_pnl:.2f}')
            pdf.multi_cell(0, 10, f'Win Rate: {win_rate:.1f}%')
            pdf.ln(5)
            
            # Delta Analysis
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Delta Analysis', 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 10, f'Average Sell Delta: {avg_sell_delta:.4f}')
            pdf.multi_cell(0, 10, f'Min Sell Delta: {min_sell_delta:.4f}')
            pdf.multi_cell(0, 10, f'Max Sell Delta: {max_sell_delta:.4f}')
            pdf.ln(5)
            
            # IV Analysis
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'IV Analysis', 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 10, f'Average IV: {avg_iv:.4f}')
            pdf.multi_cell(0, 10, f'Min IV: {min_iv:.4f}')
            pdf.multi_cell(0, 10, f'Max IV: {max_iv:.4f}')
            pdf.ln(5)
            
            # Credit Analysis
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Credit Analysis', 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 10, f'Average Credit: ${avg_credit:.2f}')
            pdf.multi_cell(0, 10, f'Min Credit: ${min_credit:.2f}')
            pdf.multi_cell(0, 10, f'Max Credit: ${max_credit:.2f}')
        
        # Trade Details
        pdf.add_page()
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Trade Details', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        if not trades_df.empty:
            # Create table headers
            headers = ['Date', 'Entry', 'Exit', 'Sell Strike', 'Buy Strike', 'Credit', 'P&L', 'IV', 'Delta']
            col_widths = [20, 20, 20, 20, 20, 20, 20, 20, 20]
            
            # Add headers
            pdf.set_font('Arial', 'B', 8)
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1)
            pdf.ln()
            
            # Add data rows
            pdf.set_font('Arial', '', 8)
            for _, trade in trades_df.iterrows():
                # Format values with proper handling of None
                def format_value(value, format_str):
                    if pd.isna(value):
                        return "N/A"
                    return format_str.format(value)
                
                pdf.cell(col_widths[0], 10, str(trade['date']), 1)
                pdf.cell(col_widths[1], 10, str(trade['entry_time'].time()), 1)
                pdf.cell(col_widths[2], 10, str(trade['exit_time'].time()), 1)
                pdf.cell(col_widths[3], 10, format_value(trade['sell_strike'], "{:.1f}"), 1)
                pdf.cell(col_widths[4], 10, format_value(trade['buy_strike'], "{:.1f}"), 1)
                pdf.cell(col_widths[5], 10, format_value(trade['credit'], "${:.2f}"), 1)
                pdf.cell(col_widths[6], 10, format_value(trade['total_pnl'], "${:.2f}"), 1)
                pdf.cell(col_widths[7], 10, format_value(trade['iv'], "{:.4f}"), 1)
                pdf.cell(col_widths[8], 10, format_value(trade['sell_delta'], "{:.4f}"), 1)
                pdf.ln()
        
        # Save PDF
        pdf_path = os.path.join(self.log_dir, f"strategy_report_{self.timestamp}.pdf")
        pdf.output(pdf_path)
        self.logger.info(f"\nPDF report generated: {pdf_path}")
        
        # Generate and save trade analysis plots
        if not trades_df.empty:
            self._generate_trade_plots(trades_df)
    
    def _generate_trade_plots(self, trades_df):
        """Generate trade analysis plots using Plotly"""
        # Ensure date column is datetime
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        
        # Create subplots for comprehensive analysis
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Cumulative P&L', 'P&L Distribution',
                'Delta vs P&L', 'IV vs P&L',
                'Credit vs P&L', 'Monthly Performance'
            ),
            specs=[
                [{"type": "scatter"}, {"type": "histogram"}],
                [{"type": "scatter"}, {"type": "scatter"}],
                [{"type": "scatter"}, {"type": "bar"}]
            ]
        )
        
        # Cumulative P&L
        trades_df['cumulative_pnl'] = trades_df['total_pnl'].cumsum()
        fig.add_trace(
            go.Scatter(x=trades_df['date'], y=trades_df['cumulative_pnl'],
                      mode='lines+markers', name='Cumulative P&L'),
            row=1, col=1
        )
        
        # P&L Distribution
        fig.add_trace(
            go.Histogram(x=trades_df['total_pnl'], nbinsx=20,
                        name='P&L Distribution'),
            row=1, col=2
        )
        
        # Delta vs P&L
        fig.add_trace(
            go.Scatter(x=trades_df['sell_delta'], y=trades_df['total_pnl'],
                      mode='markers', name='Delta vs P&L',
                      marker=dict(
                          color=trades_df['total_pnl'],
                          colorscale='RdYlGn',
                          showscale=True
                      )),
            row=2, col=1
        )
        
        # IV vs P&L
        fig.add_trace(
            go.Scatter(x=trades_df['iv'], y=trades_df['total_pnl'],
                      mode='markers', name='IV vs P&L',
                      marker=dict(
                          color=trades_df['total_pnl'],
                          colorscale='RdYlGn',
                          showscale=True
                      )),
            row=2, col=2
        )
        
        # Credit vs P&L
        fig.add_trace(
            go.Scatter(x=trades_df['credit'], y=trades_df['total_pnl'],
                      mode='markers', name='Credit vs P&L',
                      marker=dict(
                          color=trades_df['total_pnl'],
                          colorscale='RdYlGn',
                          showscale=True
                      )),
            row=3, col=1
        )
        
        # Monthly Performance
        trades_df['month'] = trades_df['date'].dt.strftime('%Y-%m')
        monthly_pnl = trades_df.groupby('month')['total_pnl'].sum().reset_index()
        fig.add_trace(
            go.Bar(x=monthly_pnl['month'], y=monthly_pnl['total_pnl'],
                  name='Monthly P&L'),
            row=3, col=2
        )
        
        # Update layout
        fig.update_layout(
            height=1200,
            showlegend=False,
            title_text="Comprehensive Trade Analysis",
            title_x=0.5
        )
        
        # Update axes labels
        fig.update_xaxes(title_text="Date", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative P&L ($)", row=1, col=1)
        fig.update_xaxes(title_text="P&L ($)", row=1, col=2)
        fig.update_yaxes(title_text="Frequency", row=1, col=2)
        fig.update_xaxes(title_text="Sell Delta", row=2, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=2, col=1)
        fig.update_xaxes(title_text="IV", row=2, col=2)
        fig.update_yaxes(title_text="P&L ($)", row=2, col=2)
        fig.update_xaxes(title_text="Credit ($)", row=3, col=1)
        fig.update_yaxes(title_text="P&L ($)", row=3, col=1)
        fig.update_xaxes(title_text="Month", row=3, col=2)
        fig.update_yaxes(title_text="Total P&L ($)", row=3, col=2)
        
        # Save plots
        plots_dir = os.path.join(self.log_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        
        fig.write_html(os.path.join(plots_dir, f'trade_analysis_{self.timestamp}.html'))
        self.logger.info(f"Trade analysis plots saved in: {plots_dir}")