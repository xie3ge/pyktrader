#-*- coding:utf-8 -*-
from base import *
from misc import *
from strategy import *
import pandas as pd
import data_handler
import order as order
import agent
 
class RBreakerTrader(Strategy):
    def __init__(self, name, underliers, agent = None, trade_unit = [], ratios = [], stop_loss = []):
        Strategy.__init__(name, underliers, trade_unit, agent)
        self.data_func = []   
        num_assets = len(underliers)
        self.ratios = [(0.35, 0.07, 0.25)]*num_assets
        if len(ratios) > 1:
            self.ratio = ratios
        elif len(ratios) == 1: 
            self.ratio = ratios*num_assets
        self.order_type = OPT_MARKET_ORDER
        self.ssetup = [0.0]*num_assets
        self.bsetup = [0.0]*num_assets
        self.senter = [0.0]*num_assets
        self.benter = [0.0]*num_assets
        self.sbreak = [0.0]*num_assets
        self.bbreak = [0.0]*num_assets
        self.start_min_id = 1505
        self.end_min_id = 2055
        self.freq = 1
        self.num_tick = 1
        self.num_trades = [0]*num_assets

    def initialize(self):
        self.load_state()
        for idx, underlier in enumerate(self.underliers):
            inst = underlier[0]
            ddf = self.agent.day_data[inst]
            (a, b, c) = self.ratios[idx]
            dhigh = ddf.ix[-1,'high']
            dlow = ddf.ix[-1,'low']
            dclose = ddf.ix[-1,'close']
            self.ssetup[idx] = dhigh + a*(dclose - dlow)
            self.bsetup[idx] = dlow  - a*(dhigh -  dclose)
            self.senter[idx] = (1 + b)*(dhigh + dclose)/2.0 - b*dlow
            self.benter[idx] = (1 + b)*(dlow  + dclose)/2.0 - b*dhigh
            self.bbreak[idx] = self.ssetup[idx] + c * (self.ssetup[idx] - self.bsetup[idx])
            self.sbreak[idx] = self.bsetup[idx] - c * (self.ssetup[idx] - self.bsetup[idx])    
        pass         

    def day_finalize(self):    
        #self.update_trade_unit()
        self.save_state()
        self.logger.info('strat %s is finalizing the day - update trade unit, save state' % self.name)
        self.num_trades = [0]*len(underliers)
        return
    
    def save_local_variables(self, file_writer):
        for idx, underlier in enumerate(self.underliers):
			inst = underlier[0]
			row = ['NumTrade', str(inst), self.num_trades[idx]]
			file_writer.writerow(row)
		return
    
    def load_local_variables(self, row):
        if row[0] == 'NumTrade':
			inst = str(row[1])
			idx = self.get_index([inst])
			if idx >=0:
				self.num_trades[idx] = int(row[2]) 
        return
		
    def run_min(self, inst, min_id):
        idx = self.get_index([inst])
        if idx < 0:
            self.logger.warning('the inst=%s is not in this strategy = %s' % (inst, self.name))
            return
        curr_min = int(min_id/100)*60+ min_id % 100
        if (curr_min % self.freq != 0) or (min_id < self.start_min_id):
            return
        price_unit = self.agent.instruments[inst].multiple
        curr_pos = None
        buysell = 0
        save_status = self.update_positions(idx)
        inst_obj = self.agent.instruments[inst]
        dhigh = self.cur_day[inst].high
        dlow  = self.cur_day[inst].low
        cur_price = inst_obj.price
        if len(self.positions[idx])>0:
            curr_pos = self.positions[idx][0]
            buysell = curr_pos.direction            

        if (min_id >= self.last_tick_id):
            if (buysell!=0):
                valid_time = self.agent.tick_id + 600
                etrade = order.ETrade( [inst], [-self.trade_unit[idx][0]*buysell], \
                                               [self.order_type], -curr_price*buysell, [self.num_tick], \
                                               valid_time, self.name, self.agent.name, price_unit, [price_unit])
                curr_pos.exit_tradeid = etrade.id
                self.submitted_pos[idx].append(etrade)
                self.agent.submit_trade(etrade)
        else:
            if (self.num_trades[idx]>=2) or (len(self.submitted_pos[idx])>0):
                return
            if ((cur_price >= self.bbreak[idx]) or (cur_price <= self.sbreak[idx])) and (buysell == 0):
                if  (cur_price >= self.bbreak[idx]):
                    buysell = 1
                else:
                    buysell = -1
                
                valid_time = self.agent.tick_id + 600
                etrade = order.ETrade( [inst], [self.trade_unit[idx][0]*buysell], \
                                       [self.order_type], buysell * cur_price, [self.num_tick],  \
                                       valid_time, self.name, self.agent.name, price_unit, [price_unit])
                tradepos = TradePos([inst], self.trade_unit[idx], buysell, cur_price, cur_price, price_unit)
                tradepos.entry_tradeid = etrade.id
                self.submitted_pos[idx].append(etrade)
                self.positions[inst].append(tradepos)
                self.agent.submit_trade(etrade)
                self.num_trades[idx] += 1 
            elif ((dhigh< self.bbreak[idx]) and (dhigh >= self.ssetup[idx]) and (cur_price < self.senter[idx]) and (buysell >=0)) or \
                 ((dlow > self.sbreak[idx]) and (dlow  <= self.bsetup[idx]) and (cur_price > self.benter[idx]) and (buysell <=0)):
                if buysell!=0:
                    valid_time = self.agent.tick_id + 600
                    etrade = order.ETrade( [inst], [-self.trade_unit[idx][0]*buysell], \
                                               [self.order_type], -curr_price*buysell, [self.num_tick], \
                                               valid_time, self.name, self.agent.name, price_unit, [price_unit])
                    curr_pos.exit_tradeid = etrade.id
                    self.submitted_pos[idx].append(etrade)
                    self.agent.submit_trade(etrade)
                if  (cur_price < self.senter[idx]):
                    buysell = -1
                else:
                    buysell = 1
                valid_time = self.agent.tick_id + 600
                etrade = order.ETrade( [inst], [self.trade_unit[idx][0]*buysell], \
                                       [self.order_type], buysell * cur_price, [self.num_tick],  \
                                       valid_time, self.name, self.agent.name, price_unit, [price_unit])
                tradepos = TradePos([inst], self.trade_unit[idx], buysell, \
                                        cur_price, cur_price, price_unit)
                tradepos.entry_tradeid = etrade.id
                self.submitted_pos[idx].append(etrade)
                self.positions[inst].append(tradepos)
                self.agent.submit_trade(etrade)    
                self.num_trades[idx] += 1
        return 
        
    def update_trade_unit(self):
        pass
