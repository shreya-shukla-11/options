import logging
from datetime import datetime
import os
from fpdf import FPDF
import pandas as pd

class StrategyLogger:
    def __init__(self, strategy_name="Call Credit Spread"):
        self.strategy_name = strategy_name
        self.log_dir = "logs"
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        # Setup logging
        self.logger = logging.getLogger(strategy_name)
        self.logger.setLevel(logging.INFO)
        
        # File handler
        log_file = os.path.join(self.log_dir, f"{strategy_name}_{self.timestamp}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Initialize trade data collection
        self.trades = []
        self.entry_times = []
        self.exit_times = []
        self.sell_strikes = []
        self.buy_strikes = []
        
    def log_data_summary(self, equity_data, options_data):
        self.logger.info("=== Data Summary ===")
        self.logger.info(f"Equity Data Rows: {len(equity_data)}")
        self.logger.info(f"Options Data Rows: {len(options_data)}")
        self.logger.info(f"Date Range: {equity_data['ts'].min()} to {equity_data['ts'].max()}")
        
    def log_strategy_details(self):
        self.logger.info("\n=== Strategy Details ===")
        self.logger.info("Strategy: Call Credit Spread")
        self.logger.info("Entry Conditions:")
        self.logger.info("- MA5 change < 1%")
        self.logger.info("- IV < 75%")
        self.logger.info("- Credit > 0.25")
        self.logger.info("Exit Conditions:")
        self.logger.info("- Stop loss: Credit + 0.03")
        self.logger.info("- Market close (2:30 PM)")
        
    def log_trade(self, trading_day, entry_time, exit_time, sell_strike, buy_strike, 
                 credit, exit_pnl, total_pnl):
        trade_data = {
            'trading_day': trading_day,
            'entry_time': entry_time,
            'exit_time': exit_time,
            'sell_strike': sell_strike,
            'buy_strike': buy_strike,
            'credit': credit,
            'exit_pnl': exit_pnl,
            'total_pnl': total_pnl
        }
        self.trades.append(trade_data)
        self.entry_times.append(entry_time)
        self.exit_times.append(exit_time)
        self.sell_strikes.append(sell_strike)
        self.buy_strikes.append(buy_strike)
        
        self.logger.info(f"\n=== Trade Executed ===")
        self.logger.info(f"Date: {trading_day}")
        self.logger.info(f"Entry Time: {entry_time}")
        self.logger.info(f"Exit Time: {exit_time}")
        self.logger.info(f"Sell Strike: {sell_strike}")
        self.logger.info(f"Buy Strike: {buy_strike}")
        self.logger.info(f"Credit: ${credit:.2f}")
        self.logger.info(f"Exit P&L: ${exit_pnl:.2f}")
        self.logger.info(f"Total P&L: ${total_pnl:.2f}")
        
    def generate_pdf_report(self):
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, f'{self.strategy_name} Strategy Report', 0, 1, 'C')
        pdf.ln(10)
        
        # Data Summary
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Data Summary', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 10, f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
        pdf.ln(5)
        
        # Strategy Details
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Strategy Details', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 10, '''
        Strategy: Call Credit Spread
        Entry Conditions:
        - MA5 change < 1%
        - IV < 75%
        - Credit > 0.25
        Exit Conditions:
        - Stop loss: Credit + 0.03
        - Market close (2:30 PM)
        ''')
        pdf.ln(5)
        
        # Trade Summary
        pdf.set_font('Arial', 'B', 12)
        pdf.cell(0, 10, 'Trade Summary', 0, 1)
        pdf.set_font('Arial', '', 10)
        
        if self.trades:
            trades_df = pd.DataFrame(self.trades)
            total_trades = len(trades_df)
            total_pnl = trades_df['total_pnl'].sum()
            win_rate = len(trades_df[trades_df['total_pnl'] > 0]) / total_trades * 100
            
            pdf.cell(0, 10, f'Total Trades: {total_trades}', 0, 1)
            pdf.cell(0, 10, f'Total P&L: ${total_pnl:.2f}', 0, 1)
            pdf.cell(0, 10, f'Win Rate: {win_rate:.1f}%', 0, 1)
            
            # Trade Details
            pdf.ln(5)
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 10, 'Trade Details', 0, 1)
            pdf.set_font('Arial', '', 8)
            
            # Table headers
            headers = ['Date', 'Entry', 'Exit', 'Sell Strike', 'Buy Strike', 'Credit', 'P&L']
            col_widths = [30, 30, 30, 25, 25, 20, 20]
            
            for i, header in enumerate(headers):
                pdf.cell(col_widths[i], 10, header, 1)
            pdf.ln()
            
            # Table data
            for trade in self.trades:
                pdf.cell(col_widths[0], 10, str(trade['trading_day']), 1)
                pdf.cell(col_widths[1], 10, str(trade['entry_time']), 1)
                pdf.cell(col_widths[2], 10, str(trade['exit_time']), 1)
                pdf.cell(col_widths[3], 10, f"${trade['sell_strike']:.2f}", 1)
                pdf.cell(col_widths[4], 10, f"${trade['buy_strike']:.2f}", 1)
                pdf.cell(col_widths[5], 10, f"${trade['credit']:.2f}", 1)
                pdf.cell(col_widths[6], 10, f"${trade['total_pnl']:.2f}", 1)
                pdf.ln()
        
        # Save PDF
        pdf_path = os.path.join(self.log_dir, f"{self.strategy_name}_{self.timestamp}.pdf")
        pdf.output(pdf_path)
        self.logger.info(f"PDF report generated: {pdf_path}")
        
    def get_trade_data(self):
        return {
            'entry_times': self.entry_times,
            'exit_times': self.exit_times,
            'sell_strikes': self.sell_strikes,
            'buy_strikes': self.buy_strikes,
            'trades': self.trades
        } 