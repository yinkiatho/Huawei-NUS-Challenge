#!/usr/bin/env python 
# -*- coding:utf-8 -*-

import glob
import pandas as pd

tick_path = '/opt/tickdata'
trainData_file = 'trainData.csv'


def get_ms(tm):
    hhmmss = tm // 1000
    ms = (hhmmss // 10000 * 3600 + (hhmmss // 100 % 100) * 60 + hhmmss % 100) * 1000 + tm % 1000
    ms_from_open = ms - 34200000  # millisecond from stock opening
    if tm >= 130000000:
        ms_from_open -= 5400000
    return ms_from_open

def get_h_l(i, bp_list, sp_list):
    high_price_b = max([bp_list[j][i] for j in range(10)])
    low_price_b = min([bp_list[j][i] for j in range(10)])
    high_price_s = max([sp_list[j][i] for j in range(10)])
    low_price_s = min([sp_list[j][i] for j in range(10)])
    return [max(high_price_b, high_price_s), min(low_price_b, low_price_s)]
    


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
        bp1 = sym_data['COLUMN28'].values
        bp2 = sym_data['COLUMN29'].values
        bp3 = sym_data['COLUMN30'].values
        bp4 = sym_data['COLUMN31'].values
        bp5 = sym_data['COLUMN32'].values
        bp6 = sym_data['COLUMN33'].values
        bp7 = sym_data['COLUMN34'].values
        bp8 = sym_data['COLUMN35'].values
        bp9 = sym_data['COLUMN36'].values
        bp10 = sym_data['COLUMN37'].values
        sp1 = sym_data['COLUMN08'].values
        sp2 = sym_data['COLUMN09'].values
        sp3 = sym_data['COLUMN10'].values
        sp4 = sym_data['COLUMN11'].values
        sp5 = sym_data['COLUMN12'].values
        sp6 = sym_data['COLUMN13'].values
        sp7 = sym_data['COLUMN14'].values
        sp8 = sym_data['COLUMN15'].values
        sp9 = sym_data['COLUMN16'].values
        sp10 = sym_data['COLUMN17'].values
        
        bp_list = [bp1, bp2, bp3, bp4, bp5, bp6, bp7, bp8, bp9, bp10]
        sp_list = [sp1, sp2, sp3, sp4, sp5, sp6, sp7, sp8, sp9, sp10]
        
        prior_ATR = []  # prior ATR
        curr_ATR = 1  # current ATR
        sampling_p = 0  # sampling pointer
        for i in range(len(ms)):
            if ms[i] - ms[sampling_p] < 60000:  # sampling every 1 minute
                continue

            # find the indexes at different time
            idx_1min, idx_2min, idx_3min, idx_4min, idx_5min, 
            idx_6min, idx_7min, idx_8min, idx_9min, idx_10min = 0, 0, 0, 0, 0, 0, 0, 0, 0, 0
            for j in range(i):
                if ms[i] - ms[j] >= 60000:
                    idx_1min = j
                if ms[i] - ms[j] >= 120000:
                    idx_2min = j
                if ms[i] - ms[j] >= 180000:
                    idx_3min = j
                if ms[i] - ms[j] >= 240000:
                    idx_4min = j
                if ms[i] - ms[j] >= 300000:
                    idx_5min = j
                if ms[i] - ms[j] >= 360000:
                    idx_6min = j
                if ms[i] - ms[j] >= 420000:
                    idx_7min = j
                if ms[i] - ms[j] >= 480000:
                    idx_8min = j
                if ms[i] - ms[j] >= 540000:
                    idx_9min = j
                if ms[i] - ms[j] >= 600000:
                    idx_10min = j
                
            idx_fwd_5min = 0
            for j in range(i, len(ms)):
                if ms[j] - ms[i] >= 300000:
                    idx_fwd_5min = j
                    break
            indexes = [idx_1min, idx_2min, idx_3min, idx_4min, idx_5min, idx_6min, idx_7min, idx_8min, idx_9min, idx_10min, idx_fwd_5min]
            # calculate a target variable and 10 factor variables
            if idx_10min != 0 and idx_fwd_5min != 0:
                
                for i in indexes:
                    TR_H, TR_L = (get_h_l(i, bp_list, sp_list)[
                                      0] + get_h_l(i, bp_list, sp_list)[1])/2 + 3 * curr_ATR, (get_h_l(i, bp_list, sp_list)
                                 [0] - get_h_l(i, bp_list, sp_list)[1])/2 + 3 * curr_ATR
                    TR = TR_H - TR_L
                    if (len(prior_ATR) == 10):
                        prior_ATR.pop(0)
                        
                    new_ATR = (TR + len(prior_ATR) * curr_ATR) / (len(prior_ATR) + 1)
                    prior_ATR.append(new_ATR)
                    
                    curr_ATR = new_ATR

                #10 factor variables are 1) - 10) ATR's of the Different Time Indexes
                train_data.append((
                    (price[idx_fwd_5min] / price[i] - 1) * 10000,  # target y
                    prior_ATR[0],  # factor 1
                    prior_ATR[1],  # factor 2
                    prior_ATR[2],  # factor 3
                    prior_ATR[3],  # factor 4
                    prior_ATR[4],  # factor 5
                    prior_ATR[5],  # factor 6
                    prior_ATR[6],  # factor 7
                    prior_ATR[7],  # factor 8
                    prior_ATR[8],  # factor 9
                    prior_ATR[9],  # factor 10
                ))
                sampling_p = i

                

train_data = pd.DataFrame(train_data, columns=['y'] + [f'x{i}' for i in range(1, 11)])
train_data.to_csv(trainData_file, index=False)
