#!/usr/bin/env python 
# -*- coding:utf-8 -*-

import glob
import pandas as pd
import numpy as np

tick_path = '/opt/tickdata'
trainData_file = 'trainData.csv'


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
            increase = (price_now - curr_price)/price_now * 100 #in percentage
            average_increase = [average_increase[0] + increase, average_increase[1] + 1]
            curr_price = price_now
        elif price_now < curr_price:
            decrease = (curr_price - price_now)/price_now * 100 #in percentage
            average_decrease = [average_decrease[0] + decrease, average_decrease[1] + 1]
            curr_price = price_now
    
    return [average_increase[0]/average_increase[1], average_decrease[0]/average_decrease[1]]
            


tick_files = glob.glob(f'{tick_path}/*.csv')[:3]  # select some files for training
train_data = []
for f in tick_files:
    print(f)
    tick_data = pd.read_csv(f, index_col=None)
    symbol = list(tick_data['COLUMN02'].unique())

    for sym in symbol:
        sym_data = tick_data[tick_data['COLUMN02'] == sym]
        ms = sym_data['COLUMN03'].apply(lambda x: get_ms(x)).values
        price = sym_data['COLUMN07'].values
        buying_volume = sym_data['COLUMN50'].values
        selling_volume = sym_data['COLUMN51'].values
        sampling_p = 0  # sampling pointer
        for i in range(len(ms)):
            if ms[i] - ms[sampling_p] < 60000:  # sampling every 1 minute
                continue

            # find the indexes at different time
            idx_5min, idx_10min, idx_15min, idx_20min, idx_25min = 0, 0, 0, 0, 0
            for j in range(i):
                if ms[i] - ms[j] >= 300000:
                    idx_5min = j
                if ms[i] - ms[j] >= 600000:
                    idx_10min = j
                if ms[i] - ms[j] >= 900000:
                    idx_15min = j
                if ms[i] - ms[j] >= 1200000:
                    idx_20min = j
                if ms[i] - ms[j] >= 1500000:
                    idx_25min = j
            idx_fwd_5min = 0
            for j in range(i, len(ms)):
                if ms[j] - ms[i] >= 300000:
                    idx_fwd_5min = j
                    break

            # calculate a target variable and 10 factor variables
            if idx_25min != 0 and idx_fwd_5min != 0:

                #10 factor variables are 1) - 5) RSI indexes of Current Price to 5 Different Time Indexes
                #                        6) - 10 Average Gains/Losses of 5 Different Time Indexes from past

                #av_gain_loss for each time index
                av_gain_loss_5_min = get_av_gain_loss(price, idx_5min, i)
                av_gain_loss_10_min = get_av_gain_loss(price, idx_10min, i)
                av_gain_loss_15_min = get_av_gain_loss(price, idx_15min, i)
                av_gain_loss_20_min = get_av_gain_loss(price, idx_20min, i)
                av_gain_loss_25_min = get_av_gain_loss(price, idx_25min, i)
                
                #factor variables would be ratio and RSI indexes
                
                
                train_data.append((
                    (price[idx_fwd_5min] / price[i] - 1) * 10000,  # target y
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
                ))
                sampling_p = i

                

train_data = pd.DataFrame(train_data, columns=['y'] + [f'x{i}' for i in range(1, 11)])
train_data.to_csv(trainData_file, index=False)
