import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.stats import norm
from scipy.optimize import brentq
import os
import plotly.graph_objects as go
from logger import StrategyLogger
import json

DATA_DIR = "../data"
EQ_DIR = f"{DATA_DIR}/equity/SPY"
OPT_DIR = f"{DATA_DIR}/options/SPY"

# Initialize logger
logger = StrategyLogger()

equity_files = [os.path.join(EQ_DIR, f"2025-{month:02d}.parquet") for month in [3, 4, 5]]

equity_data = pd.concat([pd.read_parquet(f) for f in equity_files if os.path.exists(f)], ignore_index=True)
equity_data['ts'] = pd.to_datetime(equity_data['ts'], unit='ms')

option_files = [os.path.join(OPT_DIR, f) for f in os.listdir(OPT_DIR) if f.endswith('.parquet')]

# Log data summary
logger.log_data_summary(equity_data, pd.DataFrame())

# Log strategy details
logger.log_strategy_details()

daily_closes = equity_data.groupby(equity_data['ts'].dt.date)['c'].last().reset_index()
daily_closes['ts'] = pd.to_datetime(daily_closes['ts'])
daily_closes.set_index('ts', inplace=True)
daily_closes['ma5'] = daily_closes['c'].rolling(window=5).mean()
daily_closes['ma5_change'] = daily_closes['ma5'].pct_change() * 100

option_info = []
for f in option_files:
    parts = f.split('/')[-1].split('.')[0].split(':')[1]
    date_str = parts[3:9]
    option_type = parts[9]
    strike_str = parts[10:]
    expiration = pd.to_datetime('20' + date_str)
    strike = int(strike_str) / 1000.0
    option_info.append({'file_path': f, 'expiration': expiration, 'type': option_type, 'strike': strike})
option_info_df = pd.DataFrame(option_info)

options_data = pd.DataFrame()
for f in tqdm(option_files):
    try:
        temp_df = pd.read_parquet(f).assign(option_id=f)
        options_data = pd.concat([options_data, temp_df], ignore_index=True)
    except Exception as e:
        print(f"Error loading option file {f}: {e}")
options_data['ts'] = pd.to_datetime(options_data['ts'],unit='ms')
if options_data.empty:
    raise ValueError("No options data loaded")
print(f"Loaded {len(options_data)} rows of options data")

trading_days = sorted(equity_data['ts'].dt.date.unique())
pnl_list = []

for i, trading_day in enumerate(trading_days):
    if i == 0:
        print(f"Skipping {trading_day}: No previous MA data")
        continue
    prev_day = trading_days[i - 1]
    if daily_closes[daily_closes.index.date == prev_day].empty:
        print(f"Skipping {trading_day}: No data for previous day {prev_day}")
        continue
    ma5_change_prev = daily_closes.loc[daily_closes.index.date == prev_day, 'ma5_change'].iloc[0]
    if ma5_change_prev > 1:
        print(f"Skipping {trading_day}: Upward trend ({ma5_change_prev:.2f}%)")
        continue

    print(f"\nProcessing {trading_day}")
    day_equity = equity_data[equity_data['ts'].dt.date == trading_day]
    day_options_all = options_data[options_data['ts'].dt.date == trading_day]
    if day_equity.empty:
        print(f"Skipping {trading_day}: No equity data")
        continue
    if day_options_all.empty:
        print(f"Skipping {trading_day}: No options data")
        continue
    
    ts_entry = day_options_all['ts'].min()
    if pd.isna(ts_entry):
        print(f"Skipping {trading_day}: No valid timestamps")
        continue
    print(f"Entry timestamp: {ts_entry}")
    
    equity_ts_diff = (day_equity['ts'] - ts_entry).abs()
    closest_equity_ts = day_equity.iloc[equity_ts_diff.argmin()]['ts']
    S = day_equity[day_equity['ts'] == closest_equity_ts]['c'].values[0]
    if S <= 0:
        print(f"Skipping {trading_day}: Invalid underlying price {S}")
        continue
    print(f"Underlying price: {S}")
    
    active_calls = option_info_df[(option_info_df['expiration'] > pd.to_datetime(trading_day)) & (option_info_df['type'] == 'C')]
    if active_calls.empty:
        print(f"Skipping {trading_day}: No active calls")
        continue
    print(f"Active calls (rows: {len(active_calls)})")
    
    day_options = day_options_all[day_options_all['ts'] == ts_entry]
    day_options = day_options.merge(active_calls[['file_path', 'strike']], left_on='option_id', right_on='file_path')
    if day_options.empty:
        print(f"Skipping {trading_day}: No call option prices at {ts_entry}")
        continue
    print(f"Available strikes at entry:\n{day_options[['strike', 'c', 'option_id']]}")
    
    strikes = active_calls['strike'].values
    strike_diffs = np.abs(strikes - S)
    sorted_indices = np.argsort(strike_diffs)
    atm_option = None
    atm_price = np.nan
    atm_strike = np.nan
    for idx in sorted_indices:
        candidate_strike = strikes[idx]
        candidate_option = active_calls[active_calls['strike'] == candidate_strike].iloc[0]
        price = day_options[day_options['option_id'] == candidate_option['file_path']]['c'].values[0] if not day_options[day_options['option_id'] == candidate_option['file_path']].empty else np.nan
        if not np.isnan(price) and price > 0:
            atm_option = candidate_option
            atm_price = price
            atm_strike = candidate_strike
            break
    if atm_option is None:
        print(f"Skipping {trading_day}: No valid ATM price")
        continue
    expiration = atm_option['expiration']
    T = (expiration - ts_entry).total_seconds() / (365.25 * 86400)
    if T <= 0:
        print(f"Skipping {trading_day}: Invalid expiration (T={T})")
        continue
    print(f"ATM strike: {atm_strike}, price: {atm_price}, T: {T}")
    
    r = 0.01
    C = atm_price
    try:
        IV = brentq(lambda sigma: S * norm.cdf((np.log(S / atm_strike) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))) - atm_strike * np.exp(-r * T) * norm.cdf((np.log(S / atm_strike) + (r - 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))) - C, 0.001, 2.0)
    except Exception as e:
        print(f"Skipping {trading_day}: IV calculation failed: {e}")
        continue
    if np.isnan(IV) or IV <= 0:
        print(f"Skipping {trading_day}: Invalid IV {IV}")
        continue
    if IV > 0.75:
        print(f"Skipping {trading_day}: High IV ({IV})")
        continue
    print(f"IV: {IV}")
    
    active_calls['delta'] = np.nan
    for idx, row in active_calls.iterrows():
        strike = row['strike']
        if strike <= 0:
            print(f"Invalid strike {strike} for option {row['file_path']}")
            continue
        T = (row['expiration'] - ts_entry).total_seconds() / (365.25 * 86400)
        if T <= 0:
            print(f"Invalid T {T} for option {row['file_path']}")
            continue
        try:
            d1 = (np.log(S / strike) + (r + 0.5 * IV**2) * T) / (IV * np.sqrt(T))
            delta = norm.cdf(d1)
            active_calls.at[idx, 'delta'] = delta
        except Exception as e:
            print(f"Delta calculation failed for option {row['file_path']}: {e}")
    
    # Select sell options with delta < 0.35
    sell_options = active_calls[active_calls['delta'].notna() & (active_calls['delta'] < 0.35)].sort_values('delta', ascending=False)
    if sell_options.empty:
        print(f"Skipping {trading_day}: No options with delta < 0.35")
        print(f"Delta range: {active_calls['delta'].min()} to {active_calls['delta'].max()}")
        continue
    
    # Find sell option with valid price
    sell_option = None
    for _, opt in sell_options.iterrows():
        price = day_options[day_options['option_id'] == opt['file_path']]['c'].values[0] if not day_options[day_options['option_id'] == opt['file_path']].empty else np.nan
        if not np.isnan(price) and price > 0:
            sell_option = opt
            break
    if sell_option is None:
        print(f"Skipping {trading_day}: No sell options with valid prices")
        continue
    sell_strike = sell_option['strike']
    sell_delta = sell_option['delta']
    sell_price = day_options[day_options['option_id'] == sell_option['file_path']]['c'].values[0]
    print(f"Sell option: strike={sell_strike}, delta={sell_delta}, price={sell_price}")
    
    # Select buy option with strike >= sell_strike + 5
    higher_strikes = active_calls[active_calls['strike'] >= sell_strike + 5].sort_values('strike')
    buy_option = None
    for _, opt in higher_strikes.iterrows():
        price = day_options[day_options['option_id'] == opt['file_path']]['c'].values[0] if not day_options[day_options['option_id'] == opt['file_path']].empty else np.nan
        if not np.isnan(price) and price > 0:
            buy_option = opt
            break
    if buy_option is None:
        print(f"Skipping {trading_day}: No buy options with valid prices")
        continue
    buy_strike = buy_option['strike']
    buy_price = day_options[day_options['option_id'] == buy_option['file_path']]['c'].values[0]
    print(f"Buy option: strike={buy_strike}, price={buy_price}")
    
    credit = sell_price - buy_price
    if credit <= 0.25:
        print(f"Skipping {trading_day}: Credit too low ({credit})")
        continue
    print(f"Credit: {credit}")
    
    stop_loss = credit + 0.03
    print(f"Stop-loss set at: {stop_loss}")
    
    day_ts = day_options_all[day_options_all['ts'] > ts_entry]['ts'].unique()
    exit_pnl = None
    exit_time = None
    for ts in day_ts:
        if ts.hour >= 14 and ts.minute >= 30:  # Exit at or after 2:30 PM
            opt_prices = day_options_all[day_options_all['ts'] == ts]
            sell_opt_price = opt_prices[opt_prices['option_id'] == sell_option['file_path']]['c'].values[0] if not opt_prices[opt_prices['option_id'] == sell_option['file_path']].empty else np.nan
            buy_opt_price = opt_prices[opt_prices['option_id'] == buy_option['file_path']]['c'].values[0] if not opt_prices[opt_prices['option_id'] == buy_option['file_path']].empty else np.nan
            if np.isnan(sell_opt_price) or np.isnan(buy_opt_price):
                continue
            spread_value = sell_opt_price - buy_opt_price
            if spread_value >= stop_loss:
                exit_pnl = credit - stop_loss
                exit_time = ts
                print(f"Stop-loss triggered at {ts}: Spread={spread_value}")
                break
            exit_pnl = credit - spread_value
            exit_time = ts
            print(f"Exiting at {ts}: Spread={spread_value}")
            break
    
    if exit_pnl is None:
        ts_close = day_options_all['ts'].max()
        opt_prices_close = day_options_all[day_options_all['ts'] == ts_close]
        sell_opt_price_close = opt_prices_close[opt_prices_close['option_id'] == sell_option['file_path']]['c'].values[0] if not opt_prices_close[opt_prices_close['option_id'] == sell_option['file_path']].empty else np.nan
        buy_opt_price_close = opt_prices_close[opt_prices_close['option_id'] == buy_option['file_path']]['c'].values[0] if not opt_prices_close[opt_prices_close['option_id'] == buy_option['file_path']].empty else np.nan
        if np.isnan(sell_opt_price_close) or np.isnan(buy_opt_price_close):
            print(f"Skipping {trading_day}: No closing prices")
            continue
        spread_value_close = sell_opt_price_close - buy_opt_price_close
        exit_pnl = credit - spread_value_close
        exit_time = ts_close
        print(f"Exiting at close {ts_close}: Spread={spread_value_close}")
    
    total_pnl = 200 * exit_pnl - 2.5
    pnl_list.append(total_pnl)
    
    # Log trade
    logger.log_trade(
        trading_day=trading_day,
        entry_time=ts_entry,
        exit_time=exit_time,
        sell_strike=sell_strike,
        buy_strike=buy_strike,
        credit=credit,
        exit_pnl=exit_pnl,
        total_pnl=total_pnl
    )
    
    print(f"Trade executed for {trading_day}: P&L=${total_pnl:.2f} (for 2 lots)")

total_pnl = sum(pnl_list)
print(f"\nTotal trades: {len(pnl_list)}")
print(f"Total P&L: ${total_pnl:.2f}")

# Generate PDF report
logger.generate_pdf_report()

# Save trade data for Streamlit app
trade_data = logger.get_trade_data()
with open(os.path.join(logger.log_dir, f"trade_data_{logger.timestamp}.json"), 'w') as f:
    json.dump(trade_data, f, default=str)