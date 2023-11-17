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


def get_ms(tm):
    hhmmss = tm // 1000
    ms = (hhmmss // 10000 * 3600 + (hhmmss // 100 % 100) * 60 + hhmmss % 100) * 1000 + tm % 1000
    ms_from_open = ms - 34200000  # millisecond from stock opening
    if tm >= 130000000:
        ms_from_open -= 5400000
    return ms_from_open


def get_av_gain_loss(price, idx, i):
    curr_price = price[idx_5min]
    average_increase = [0, 0]
    average_decrease = [0, 0]
    for j in range(idx, i + 1):
        price_now = price[j]
        if price_now > curr_price:
            increase = (price_now - curr_price) / \
                price_now * 100  # in percentage
            average_increase = [average_increase[0] +
                                increase, average_increase[1] + 1]
            curr_price = price_now
        elif price_now < curr_price:
            decrease = (curr_price - price_now) / \
                price_now * 100  # in percentage
            average_decrease = [average_decrease[0] +
                                decrease, average_decrease[1] + 1]
            curr_price = price_now

    return [average_increase[0]/average_increase[1], average_decrease[0]/average_decrease[1]]


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

    if tm_ms < 13800000:  # before 14:50:00
        if tm_ms - last_od_ms[idx] < 300000:  # execute the order every 5 minutes
            order_time.writelines(f'{sym},N,{nTick},0\n')
            order_time.flush()
            continue

        # find the indexes at different time
        ms_temp, prc_temp = zip(*(hist_ms_prc[idx]))
        idx_5min, idx_10min, idx_15min, idx_20min, idx_25min = 0, 0, 0, 0, 0
        for i, m in enumerate(ms_temp):
            if tm_ms - m >= 300000:
                idx_5min = i
            if tm_ms - m >= 600000:
                idx_10min = i
            if tm_ms - m >= 900000:
                idx_15min = i
            if tm_ms - m >= 1200000:
                idx_20min = i
            if tm_ms - m >= 1500000:
                idx_25min = i

        # calculate the 10 factor variables and make prediction
        
        # 10 factor variables are 1) - 5) RSI indexes of Current Price to 5 Different Time Indexes
                #                        6) - 10 Average Gains/Losses of 5 Different Time Indexes from past

                # av_gain_loss for each time index
        av_gain_loss_5_min = get_av_gain_loss(prc_temp, idx_5min, tm_ms)
        av_gain_loss_10_min = get_av_gain_loss(prc_temp, idx_10min, tm_ms)
        av_gain_loss_15_min = get_av_gain_loss(prc_temp, idx_15min, tm_ms)
        av_gain_loss_20_min = get_av_gain_loss(prc_temp, idx_20min, tm_ms)
        av_gain_loss_25_min = get_av_gain_loss(prc_temp, idx_25min, tm_ms)
        
        if idx_25min != 0:
            x = np.array([
                100 - (100/(1 + av_gain_loss_5_min[0]/av_gain_loss_5_min[1])),  # factor 1
                100 - (100/(1 + av_gain_loss_10_min[0]/av_gain_loss_10_min[1])),# factor 2
                100 - (100/(1 + av_gain_loss_15_min[0]/av_gain_loss_15_min[1])),# factor 3
                100 - (100/(1 + av_gain_loss_20_min[0]/av_gain_loss_20_min[1])),# factor 4
                100 - (100/(1 + av_gain_loss_25_min[0]/av_gain_loss_25_min[1])),# factor 5
                av_gain_loss_5_min[0]/av_gain_loss_5_min[1],
                av_gain_loss_10_min[0]/av_gain_loss_10_min[1],
                av_gain_loss_15_min[0]/av_gain_loss_15_min[1],
                av_gain_loss_20_min[0]/av_gain_loss_20_min[1],
                av_gain_loss_25_min[0]/av_gain_loss_25_min[1],
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
