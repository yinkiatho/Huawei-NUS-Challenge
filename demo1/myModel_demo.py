#!/usr/bin/env python 
# -*- coding:utf-8 -*

import sys
import pandas as pd

input_path = sys.argv[1]
output_path = sys.argv[2]
symbol_file = '/opt/demos/SampleStocks.csv'

tick_data = open(input_path, 'r')
order_time = open(output_path, 'w')
symbol = pd.read_csv(symbol_file, index_col=None)['Code'].to_list()
idx_dict = dict(zip(symbol, list(range(len(symbol)))))

# ---------- Initialization ----------

target_vol = 100
od_nCount_buy = 5
od_nCount_sell = 10
od_vol_buy = target_vol // od_nCount_buy
od_vol_sell = target_vol // od_nCount_sell
od_idx_buy = [0] * len(symbol)
od_idx_sell = [0] * len(symbol)
cum_vol_buy = [0] * len(symbol)
cum_vol_sell = [0] * len(symbol)


def get_time_rate(tm):
    hhmmss = tm // 1000
    ms = (hhmmss // 10000 * 3600 + (hhmmss // 100 % 100) * 60 + hhmmss % 100) * 1000 + tm % 1000
    ms_from_open = ms - 34200000  # millisecond from stock opening
    if tm >= 130000000:
        ms_from_open -= 5400000
    return ms_from_open / 14400000


# --------------- Loop ---------------
# recursively read all tick lines from tickdata file,
# do decision with your strategy and write order to the ordertime file

tick_data.readline()  # header
order_time.writelines('symbol,BSflag,dataIdx,volume\n')
order_time.flush()

while True:
    tick_line = tick_data.readline()  # read one tick line
    if tick_line.strip() == 'stop' or len(tick_line) == 0:
        break
    row = tick_line.split(',')
    nTick = row[0]
    sym = row[1]
    tm = int(row[2])
    if sym not in symbol:
        order_time.writelines(f'{sym},N,{nTick},0\n')
        order_time.flush()
        continue

    # -------- Your Strategy Code Begin --------

    idx = idx_dict[sym]
    order_buy = 0
    if tm < 145000000:
        tm_rate = get_time_rate(tm)
        if tm_rate > od_idx_buy[idx] / od_nCount_buy:
            order_buy = od_vol_buy
            od_idx_buy[idx] += 1
            cum_vol_buy[idx] += od_vol_buy
    elif target_vol - cum_vol_buy[idx] > 0:  # force complete before market closes
        order_buy = target_vol - cum_vol_buy[idx]
        cum_vol_buy[idx] = target_vol

    order_sell = 0
    if tm < 145000000:
        tm_rate = get_time_rate(tm)
        if tm_rate > od_idx_sell[idx] / od_nCount_sell:
            order_sell = od_vol_sell
            od_idx_sell[idx] += 1
            cum_vol_sell[idx] += od_vol_sell
    elif target_vol - cum_vol_sell[idx] > 0:  # force complete before market closes
        order_sell = target_vol - cum_vol_sell[idx]
        cum_vol_sell[idx] = target_vol

    # merge duplicate parts
    if order_buy > order_sell:
        order = f'{sym},B,{nTick},{order_buy - order_sell}'
    elif order_buy == order_    sell:
        order = f'{sym},N,{nTick},0'
    else:
        order = f'{sym},S,{nTick},{order_sell - order_buy}'

    # write order
    order_time.writelines(order + '\n')
    order_time.flush()

    # -------- Your Strategy Code End --------

# ---------- Post Processing ----------

tick_data.close()
order_time.close()
