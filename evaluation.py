#!/usr/bin/env python 
# -*- coding:utf-8 -*

import pandas as pd
import numpy as np
import sys

tick_data_file = sys.argv[1]
order_time_file = sys.argv[2]
symbol_file = '/opt/demos/SampleStocks.csv'

tick_data = pd.read_csv(tick_data_file, index_col=None)
order_data = pd.read_csv(order_time_file, index_col=None)
order_data = order_data[order_data['BSflag'] != 'N']
tick_sym = tick_data['COLUMN02'].tolist()
order_data['tickSym'] = [tick_sym[i] for i in order_data['dataIdx'].tolist()]
tick_tm = tick_data['COLUMN03'].tolist()
order_data['tickTm'] = [tick_tm[i] for i in order_data['dataIdx'].tolist()]
tick_prc = tick_data['COLUMN07'].tolist()
order_data['tickPrc'] = [tick_prc[i] for i in order_data['dataIdx'].tolist()]


def tm_to_ms(tm):
    hhmmss = tm // 1000
    ms = (hhmmss // 10000 * 3600 + (hhmmss // 100 % 100) * 60 + hhmmss % 100) * 1000 + tm % 1000
    return ms


def check_validity(df):
    if df.shape[0] >= 3:
        if np.array_equal(df['volume'], df['volume'].astype(int)):
            if (df['volume'] >= 1).all():
                if np.array_equal(df['symbol'], df['tickSym']):
                    if df['tickTm'].apply(tm_to_ms).diff().min() > 60000:
                        return True
    return False


symbol = pd.read_csv(symbol_file, index_col=None)['Code'].to_list()
profit = []
for sym in symbol:
    sym_data = tick_data[tick_data['COLUMN02'] == sym]
    mkt_mean_prc = sym_data.iloc[-1]['COLUMN49'] / sym_data.iloc[-1]['COLUMN48']

    sym_order_buy = order_data[(order_data['symbol'] == sym) & (order_data['BSflag'] == 'B')]
    assert check_validity(sym_order_buy), f'order of {sym} invalid'
    buy_mean_prc = (sym_order_buy['volume'] * sym_order_buy['tickPrc']).sum() / 100

    sym_order_sell = order_data[(order_data['symbol'] == sym) & (order_data['BSflag'] == 'S')]
    assert check_validity(sym_order_sell), f'order of {sym} invalid'
    sell_mean_prc = (sym_order_sell['volume'] * sym_order_sell['tickPrc']).sum() / 100
    profit.append((sell_mean_prc - buy_mean_prc) / mkt_mean_prc)

print('Earning rate is: {:.2f} bp'.format(np.mean(profit)))
