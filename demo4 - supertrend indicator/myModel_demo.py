#!/usr/bin/env python 
# -*- coding:utf-8 -*

import sys
import pandas as pd
import numpy as np
import joblib

input_path = sys.argv[1]
output_path = sys.argv[2]
symbol_file = '/opt/demos/SampleStocks.csv'

tick_data = open(input_path, 'r')
order_time = open(output_path, 'w')
symbol = pd.read_csv(symbol_file, index_col=None)['Code'].to_list()
idx_dict = dict(zip(symbol, list(range(len(symbol)))))

# ---------- Initialization ----------

model_file = 'model.pkl'
model = joblib.load(model_file)
target_vol = 100
basic_vol = 2
cum_vol_buy = [0] * len(symbol)  # accumulate buying volume
cum_vol_sell = [0] * len(symbol)  # accumulate selling volume
unfinished_buy = [0] * len(symbol)  # unfinished buying volume in current round
unfinished_sell = [0] * len(symbol)  # unfinished selling volume in current round
last_od_ms = [0] * len(symbol)  # last order time
hist_ms_prc = [[] for i in range(len(symbol))]  # historic time and price
hist_ms_prc_h_l = [[] for i in range(len(symbol))]  # historic time, high and low
past_ATRs = [[] for i in range(len(symbol))]  # historic ATRs

def get_ms(tm):
    hhmmss = tm // 1000
    ms = (hhmmss // 10000 * 3600 + (hhmmss // 100 % 100) * 60 + hhmmss % 100) * 1000 + tm % 1000
    ms_from_open = ms - 34200000  # millisecond from stock opening
    if tm >= 130000000:
        ms_from_open -= 5400000
    return ms_from_open


def get_h_l(bp_list, sp_list):
    high_price_b = max(bp_list)
    low_price_b = min(bp_list)
    high_price_s = max(sp_list)
    low_price_s = min(sp_list)
    return [max(high_price_b, high_price_s), min(low_price_b, low_price_s)]


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
    tm_ms = get_ms(tm)
    prc = int(row[6])
    hist_ms_prc[idx].append((tm_ms, prc))
    order = ('N', 0)
    
    #get high price and low price
    curr_h, curr_l = get_h_l(row[28:38], row[8:18])
    
    #add to hist_ms_prc_h_l
    hist_ms_prc_h_l[idx].append((tm_ms, curr_h, curr_l))

    if tm_ms < 13800000:  # before 14:50:00
        if tm_ms - last_od_ms[idx] < 300000:  # execute the order every 5 minutes
            order_time.writelines(f'{sym},N,{nTick},0\n')
            order_time.flush()
            continue

        # find the indexes at different time
        ms_temp, prc_temp = zip(*(hist_ms_prc[idx]))
        idx_1min, idx_2min, idx_3min, idx_4min, idx_5min, 
        idx_6min, idx_7min, idx_8min, idx_9min, idx_10min = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
        for i, m in enumerate(ms_temp):
            if tm_ms - m >= 60000:
                idx_1min = i
            if tm_ms - m >= 120000:
                idx_2min = i
            if tm_ms - m >= 180000:
                idx_3min = i
            if tm_ms - m >= 240000:
                idx_4min = i
            if tm_ms - m >= 300000:
                idx_5min = i
            if tm_ms - m >= 360000:
                idx_6min = i
            if tm_ms - m >= 420000:
                idx_7min = i
            if tm_ms - m >= 480000:
                idx_8min = i
            if tm_ms - m >= 540000:
                idx_9min = i
            if tm_ms - m >= 600000:
                idx_10min = i

        # calculate the 10 factor variables and make prediction
        indexes = [idx_1min, idx_2min, idx_3min, idx_4min, idx_5min,
                   idx_6min, idx_7min, idx_8min, idx_9min, idx_10min]
        for i in indexes:
            curr_ATR = past_ATRs[idx][-1] if len(past_ATRs[idx]) > 0 else 1
            TR_H, TR_L = (hist_ms_prc_h_l[idx][-1][0] + hist_ms_prc_h_l[idx][-1][1])/2 + 3 * curr_ATR, 
            (hist_ms_prc_h_l[idx][-1][0] + hist_ms_prc_h_l[idx][-1][2])/2 - 3 * curr_ATR
            
            TR = TR_H - TR_L
            if (len(past_ATRs[idx]) == 10):
                past_ATRs[idx].pop(0)

            new_ATR = (TR + len(past_ATRs[idx]) * curr_ATR) / (len(past_ATRs[idx]) + 1)
            past_ATRs[idx].append(new_ATR)
        
        
        if idx_10min != 0:
            x = np.array([
                past_ATRs[idx][0],
                past_ATRs[idx][1],
                past_ATRs[idx][2],
                past_ATRs[idx][3],
                past_ATRs[idx][4],
                past_ATRs[idx][5],
                past_ATRs[idx][6],
                past_ATRs[idx][7],
                past_ATRs[idx][8],
                past_ATRs[idx][9],
                past_ATRs[idx][0],
            ]).reshape(1, -1)
            y = model.predict(x)[0]

            if y >= 0:
                od_vol = basic_vol + unfinished_buy[idx]
                if target_vol - cum_vol_buy[idx] >= od_vol:
                    order = ('B', od_vol)
                    cum_vol_buy[idx] += od_vol
                else:
                    order = ('B', target_vol - cum_vol_buy[idx])
                    cum_vol_buy[idx] = target_vol
                unfinished_buy[idx] = 0
                unfinished_sell[idx] += basic_vol
            else:
                od_vol = basic_vol + unfinished_sell[idx]
                if target_vol - cum_vol_sell[idx] >= od_vol:
                    order = ('S', od_vol)
                    cum_vol_sell[idx] += od_vol
                else:
                    order = ('S', target_vol - cum_vol_sell[idx])
                    cum_vol_sell[idx] = target_vol
                unfinished_sell[idx] = 0
                unfinished_buy[idx] += basic_vol
    else:  # force complete before market closes
        if tm_ms - last_od_ms[idx] >= 60000:
            if target_vol - cum_vol_buy[idx] > 0:
                order = ('B', target_vol - cum_vol_buy[idx])
                cum_vol_buy[idx] = target_vol
            elif target_vol - cum_vol_sell[idx] > 0:
                order = ('S', target_vol - cum_vol_sell[idx])
                cum_vol_sell[idx] = target_vol

    # write order
    if order[0] == 'N':
        order_time.writelines(f'{sym},N,{nTick},0\n')
        order_time.flush()
    else:
        last_od_ms[idx] = tm_ms
        order_time.writelines(f'{sym},{order[0]},{nTick},{order[1]}\n')
        order_time.flush()

    # -------- Your Strategy Code End --------

# ---------- Post Processing ----------

tick_data.close()
order_time.close()
