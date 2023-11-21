
import os
import pickle
import random
import time
from multiprocessing import Queue, Process
from typing import Iterable
from xtquant.xttrader import XtQuantTraderCallback

import matplotlib.pyplot as plt
import datetime
import akshare
import numpy
import numpy as np
import pandas
import seaborn as seaborn
import xtquant
from xtquant import xtconstant
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import statsmodels
from pandas import Series
from statsmodels.tsa.stattools import coint, adfuller
import statsmodels.api

from miniQMT_trade.GUI import GUI

'''
定义常数-----------------------------------------------------
'''
BUY_ORDER_TBD = 11
#待报订单，程序发出指令后但回报函数未回报状态
BUY_ORDER_PD = 12
#已报订单，程序发出指令后回报函数已经回报
BUY_ORDER_CC_TBD = 21
#待撤订单，程序发出指令后回报函数未回报状态
SELL_ORDER_TBD = 31
#待报订单，程序发出指令后但回报函数未回报状态
SELL_ORDER_PD = 32
#已报订单，程序发出指令后回报函数已经回报
SELL_ORDER_CC_TBD = 41
#待撤订单，程序发出指令后回报函数未回报状态
END = 51
#已经卖出，结束
POS = 61
#正在持仓，无其他指令

'''
定义常数-----------------------------------------------------
'''




class Trade(XtQuantTraderCallback):
    def __init__(self,order_live_max_num=1,sleep_time=2.8,order_amount=10,stragety_name='harvest',max_epoach=4,max_buy_epoach=8,max_sell_epoach=3,penny_jump=0.21,penny_jump_mode=True,move_cut_loss_value=0.45):
        self.order_live_max_num = order_live_max_num

        self.order_live_dict = {}
        #dict结构:code:{order_status:(),buy_order_id:(),sell_order_id:(),is_responded:True/False}
        self.sleep_time = sleep_time

        self.order_amount = order_amount
        self.stragety_name = stragety_name

        self.max_epoach = max_epoach
        self.max_buy_epoach = max_buy_epoach
        self.max_sell_epoach = max_sell_epoach
        self.penny_jump = penny_jump
        self.penny_jump_mode = penny_jump_mode
        self.move_cut_loss_value = move_cut_loss_value
    def initial_trade(self):
        self.path = 'D:\\国金证券QMT交易端\\userdata_mini'
        self.session_id = random.randint(100000, 999999)
        self.xt_trader = XtQuantTrader(self.path, self.session_id)

        # self.xt_trader.set_relaxed_response_order_enabled(True)
        self.acc = StockAccount('')

        callback = self
        self.xt_trader.register_callback(callback)
        # 启动交易线程
        self.xt_trader.start()
        # 建立交易连接，返回0表示连接成功
        connect_result = self.xt_trader.connect()
        if connect_result != 0:
            import sys
            sys.exit('链接失败，程序即将退出 %d' % connect_result)
        subscribe_result = self.xt_trader.subscribe(self.acc)
        if subscribe_result != 0:
            print('账号订阅失败 %d' % subscribe_result)
    '''
    回调类函数-------------------------------------------------------------------------------------------------------
    '''

    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print("connection lost")

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print("我是委托回报推送")
        print(order.stock_code, order.order_status, order.order_sysid)

    def on_stock_asset(self, asset):
        """
        资金变动推送  注意，该回调函数目前不生效
        :param asset: XtAsset对象
        :return:
        """
        print("on asset callback")
        print(asset.account_id, asset.cash, asset.total_asset)

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print("已经成交！！！")
        self.handle_on_stock_trade(trade)
        print(trade.account_id, trade.stock_code, trade.order_id)

    def on_stock_position(self, position):
        """
        持仓变动推送  注意，该回调函数目前不生效
        :param position: XtPosition对象
        :return:
        """
        print("on position callback")
        print(position.stock_code, position.volume)

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        print("on order_error callback")
        print(order_error.order_id, order_error.error_id, order_error.error_msg)

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print("on cancel_error callback")
        print(cancel_error.order_id, cancel_error.error_id, cancel_error.error_msg)

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print("已经下单！！！！")

        print(response.account_id)
        self.handle_order_async_response(response)

        print(response.account_id, response.order_id, response.seq, response.order_remark)

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        print("on_account_status")
        print(status.account_id, status.account_type, status.status)

    def on_cancel_order_stock_async_response(self, response):
        """
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        self.handle_cancel_respond(response)
        print('异步撤单回报')

    def handle_order_async_response(self, response):
        '''
        异步下单回报推送处理
        :return:
        '''
        order_remark = response.order_remark
        side = order_remark[:1]
        code = order_remark[1:]
        if (side == 'b'):
            if (self.order_live_dict[code]['order_status'] == BUY_ORDER_TBD):
                self.order_live_dict[code]['order_status'] = BUY_ORDER_PD
                self.order_live_dict[code].update({'buy_order_id': response.order_id})
                # 新增1
                if ('wait_epoach' not in self.order_live_dict[code]):
                    self.order_live_dict[code].update({'wait_epoach': 0})
                else:
                    self.order_live_dict[code]['wait_epoach'] = 0


        else:
            if (self.order_live_dict[code]['order_status'] == SELL_ORDER_TBD):
                self.order_live_dict[code]['order_status'] = SELL_ORDER_PD
                self.order_live_dict[code].update({'sell_order_id': response.order_id})
                if ('wait_epoach' not in self.order_live_dict[code]):
                    self.order_live_dict[code].update({'wait_epoach': 0})
                else:
                    self.order_live_dict[code]['wait_epoach'] = 0

    def handle_on_stock_trade(self, trade):
        '''
        成交回报推送处理
        :return:
        '''
        order_remark = trade.order_remark
        side = order_remark[:1]
        code = order_remark[1:]
        if (side == 'b'):
            if ('buy_order_id' in self.order_live_dict[code]):
                self.order_live_dict[code]['order_status'] = POS
                self.order_live_dict[code].update({'buy_traded_price': trade.traded_price})
                self.order_live_dict[code].update({'pos_epoach':0})

            else:
                self.order_live_dict[code].update({'buy_order_id': trade.order_id})
                self.order_live_dict[code]['order_status'] = POS
                self.order_live_dict[code].update({'buy_traded_price': trade.traded_price})
                self.order_live_dict[code].update({'pos_epoach':0})


            if ('wait_epoach' in self.order_live_dict[code]):
                self.order_live_dict[code]['wait_epoach'] = 0
        else:
            if ('sell_order_id' in self.order_live_dict[code]):
                self.order_live_dict[code]['order_status'] = END
            else:
                self.order_live_dict[code].update({'sell_order_id': trade.order_id})
                self.order_live_dict[code]['order_status'] = END
            if ('wait_epoach' in self.order_live_dict[code]):
                self.order_live_dict[code]['wait_epoach'] = 0

    def handle_cancel_respond(self, response):
        buy_cancel_dict = {k: v for k, v in self.order_live_dict.items() if v['buy_order_id'] == response.order_id}
        sell_cancel_dict = {k: v for k, v in self.order_live_dict.items() if v['sell_order_id'] == response.order_id}
        if (len(buy_cancel_dict) == 1):
            code = list(buy_cancel_dict.keys())[0]
            if (self.order_live_dict[code]['order_status'] == BUY_ORDER_CC_TBD):
                if (response.cancel_result == 0):
                    self.order_live_dict[code]['order_status'] = END
                else:
                    self.order_live_dict[code]['order_status'] = POS
        elif (len(sell_cancel_dict) == 1):
            code = list(buy_cancel_dict.keys())[0]
            if (self.order_live_dict[code]['order_status'] == SELL_ORDER_CC_TBD):
                if (response.cancel_result == 0):
                    self.order_live_dict[code]['order_status'] = POS
                else:
                    self.order_live_dict[code]['order_status'] = END
        else:
            print('撤单order_id在buy和sell均不存在')

    '''
       回调类函数-------------------------------------------------------------------------------------------------------
    '''
    def create_order_live(self,code):
        new_order_live_dict = {code:{'order_status':11}}
        self.order_live_dict.update(new_order_live_dict)
        return self

    def update_order_pending(self):
        #更新所有pending状态的epoach
        buy_pending_code_list = [k for k, v in self.order_live_dict.items() if v['order_status'] == BUY_ORDER_PD]
        sell_pending_code_list = [k for k, v in self.order_live_dict.items() if v['order_status'] == SELL_ORDER_PD]

        for code in (buy_pending_code_list+sell_pending_code_list):
            self.order_live_dict[code]['wait_epoach'] = self.order_live_dict[code]['wait_epoach'] + 1
        #更新所有pos epoach
        pos_code_list = [k for k, v in self.order_live_dict.items() if (v['order_status'] == POS or v['order_status'] == SELL_ORDER_PD)]
        for code in pos_code_list:
            self.order_live_dict[code]['pos_epoach'] = self.order_live_dict[code]['pos_epoach'] + 1


        return self


    def get_cancel_code_list(self,buy_list,sell_list):
        buy_pending_code_list = [k for k, v in self.order_live_dict.items() if v['order_status'] == BUY_ORDER_PD]
        sell_pending_code_list = [k for k, v in self.order_live_dict.items() if v['order_status'] == SELL_ORDER_PD]
        cancel_buy_pending_code_list = [k for k, v in self.order_live_dict.items() if k in buy_pending_code_list if(
                (v['wait_epoach'] >= self.max_buy_epoach and k not in buy_list))]
       
        cancel_sell_pending_code_list = [k for k, v in self.order_live_dict.items() if k in sell_pending_code_list
                                             if ((v['wait_epoach'] >= self.max_sell_epoach and k not in sell_list))]
        return cancel_buy_pending_code_list,cancel_sell_pending_code_list

    # def handle_input_list(self,buy_list,sell_list):
    #     '''
    #     处理买单
    #     '''
    #     if(len(buy_list)>0):
    #         buy_list_in_order_live = list(set(buy_list) & set(list(self.order_live_dict.keys())))
    #         buy_list_not_in_order_live = list(set(buy_list)-set(buy_list_in_order_live))
    #         #将买单分为在dict和不在dict中
    #         if(len(buy_list_in_order_live)>0):
    #             buy_dict_in_order_live = {k: v for k, v in self.order_live_dict.items() if k in buy_list_in_order_live}
    #             result_cancel_sell_dict = dict(filter(lambda x: x[1]['order_status'] in [SELL_ORDER_PD], buy_dict_in_order_live.items()))
    #
    #             #如果在dict中，则对卖单已报的单进行撤单
    #         else:
    #             result_cancel_sell_dict = {}
    #             #如果不在dict中则不用撤
    #         if(len(buy_list_not_in_order_live)>0 and len(self.order_live_dict)<self.order_live_max_num):
    #             need_buy_num = self.order_live_max_num-len(self.order_live_dict)
    #             if(len(buy_list_not_in_order_live)>need_buy_num):
    #                 result_send_buy_list = buy_list_not_in_order_live[:need_buy_num]
    #             else:
    #                 result_send_buy_list = buy_list_not_in_order_live
    #             #计算不在dict的买单情况
    #         else:
    #             result_send_buy_list = []
    #     else:
    #         result_cancel_sell_dict = {}
    #         result_send_buy_list = []
    #         #buy_list为空的情况
    #     '''
    #     处理卖单
    #     '''
    #
    #     if (len(sell_list) > 0):
    #         sell_list_in_order_live = list(set(sell_list) & set(list(self.order_live_dict.keys())))
    #
    #         if (len(sell_list_in_order_live) > 0):
    #             sell_dict_in_order_live = {k: v for k, v in self.order_live_dict.items() if k in sell_list_in_order_live
    #                                       }
    #             result_cancel_buy_dict = dict(
    #                 filter(lambda x: x[1]['order_status'] in [BUY_ORDER_PD], sell_dict_in_order_live.items()))
    #
    #             result_send_sell_dict = dict(
    #                 filter(lambda x: x[1]['order_status'] in [POS], sell_dict_in_order_live.items()))
    #
    #
    #         else:
    #             result_cancel_buy_dict = {}
    #             result_send_sell_dict = {}
    #     else:
    #         result_cancel_buy_dict = {}
    #         result_send_sell_dict = {}
    #     return result_cancel_buy_dict,result_cancel_sell_dict,result_send_buy_list,result_send_sell_dict

    def handle_input_list(self, buy_list, sell_list):
        '''
        处理买单
        '''
        if (len(buy_list) > 0):
            buy_list_in_order_live = list(set(buy_list) & set(list(self.order_live_dict.keys())))
            buy_list_not_in_order_live = list(set(buy_list) - set(buy_list_in_order_live))

            # 将买单分为在dict和不在dict中
            # if (len(buy_list_in_order_live) > 0):
            #     buy_dict_in_order_live = {k: v for k, v in self.order_live_dict.items() if k in buy_list_in_order_live}
            #     result_cancel_sell_dict = dict(
            #         filter(lambda x: x[1]['order_status'] in [SELL_ORDER_PD], buy_dict_in_order_live.items()))

                # 如果在dict中，则对卖单已报的单进行撤单
            # else:
            #     result_cancel_sell_dict = {}
                # 如果不在dict中则不用撤
            if (len(buy_list_not_in_order_live) > 0 and len(self.order_live_dict) < self.order_live_max_num):
                need_buy_num = self.order_live_max_num - len(self.order_live_dict)
                if (len(buy_list_not_in_order_live) > need_buy_num):
                    result_send_buy_list = buy_list_not_in_order_live[:need_buy_num]
                else:
                    result_send_buy_list = buy_list_not_in_order_live
                # 计算不在dict的买单情况
            else:
                result_send_buy_list = []
        else:
            # result_cancel_sell_dict = {}
            result_send_buy_list = []
            # buy_list为空的情况
        '''
        处理卖单
        '''

        if (len(sell_list) > 0):
            result_send_sell_list = [k for k,v in self.order_live_dict.items() if (k in sell_list and v['order_status']==POS)]
            # sell_list_in_order_live = list(set(sell_list) & set(list(self.order_live_dict.keys())))
            #
            # if (len(sell_list_in_order_live) > 0):
            #     sell_dict_in_order_live = {k: v for k, v in self.order_live_dict.items() if k in sell_list_in_order_live
            #                                }
            #     # result_cancel_buy_dict = dict(
            #     #     filter(lambda x: x[1]['order_status'] in [BUY_ORDER_PD], sell_dict_in_order_live.items()))
            #
            #     result_send_sell_dict = dict(
            #         filter(lambda x: x[1]['order_status'] in [POS], sell_dict_in_order_live.items()))

        else:
            # result_cancel_buy_dict = {}
            result_send_sell_list = []
        return result_send_buy_list, result_send_sell_list


    def cut_loss(self):
        cancel_order_list = []
        sell_order_list = []
        for key,value in self.order_live_dict.items():
            if(value['order_status']==POS and ( (value['max_bid_price']-value['now_bid_price']>self.move_cut_loss_value) or
                                               (value['pos_epoach']>20 and value['max_bid_price']-value['now_bid_price']>self.move_cut_loss_value/2) ) ):
                sell_order_list.append(key)
            if(value['order_status']==SELL_ORDER_PD and ( (value['max_bid_price']-value['now_bid_price']>self.move_cut_loss_value) or (value['pos_epoach']>20 and value['max_bid_price']-value['now_bid_price']>self.move_cut_loss_value/2) ) ):
                if(value['sell_order_price']>self.core.ask_list_dict[key][-1][0]):
                    cancel_order_list.append(key)
                    sell_order_list.append(key)
        return cancel_order_list,sell_order_list

    def stop_in_rest_time(self):
        today = datetime.datetime.today()
        end_time = datetime.datetime(today.year, today.month, today.day, 11, 30, 0)
        start_time = datetime.datetime(today.year, today.month, today.day, 13, 00, 0)
        if (today > end_time and today < start_time):
            time.sleep((start_time - today).total_seconds() + 2)
        return self
    def change_parm(self,parm_name,value):
        if(parm_name=='待成交最大等待轮'):
            self.max_epoach = value
        elif(parm_name=='最大处理单数'):
            self.order_live_max_num = value
        elif(parm_name=='搜索间隔时间'):
            self.sleep_time = value
        elif(parm_name=='每单持仓'):
            self.order_amount = value
        elif(parm_name=='启动窗口长度'):
            self.core.list_window = value
        elif(parm_name=='z_score下限'):
            self.core.z_score_min = value
        elif(parm_name=='z_score上限'):
            self.core.z_score_max = value
        elif(parm_name=='当前价最小分位值'):
            self.core.buy_percentile = value
        elif(parm_name=='最低R值'):
            self.core.R_min = value
        elif(parm_name=='最大p_value'):
            self.core.p_value_max = value
        elif(parm_name=='最大窗口长度'):
            self.core.max_window_length = value
        elif(parm_name=='趋向筛选比例'):
            self.core.min_trend_filter_dlt = value
        elif(parm_name=='penny_jump'):
            self.penny_jump = value
        elif(parm_name=='penny_jump_mode'):
            self.penny_jump_mode = value
        else:
            print('变量不存在')
        return

    def control_change_parm(self,handle_queue):
        if(handle_queue.empty()==False):
            handle_dict = handle_queue.get()
            self.change_parm(handle_dict['parm_name'],handle_dict['value'])
        return self

    def send_now_parm_value(self,info_queue):
        parm_value_dict = {'启动窗口长度':self.core.list_window,'最大窗口长度':self.core.max_window_length,'当前价最小分位值':self.core.buy_percentile,
                           '最低R值':self.core.R_min,'最大p_value':self.core.p_value_max,'趋向筛选比例':self.core.min_trend_filter_dlt,'z_score下限':
                           self.core.z_score_min,'z_score上限':self.core.z_score_max,'最大处理单数':self.order_live_max_num,'每单持仓':self.order_amount,
                           '待成交最大等待轮':self.max_epoach,'搜索间隔时间':self.sleep_time,'penny_jump':self.penny_jump,'penny_jump_mode':self.penny_jump_mode}
        info_queue.put(parm_value_dict)
        return self

    def send_detail_value(self,detail_queue):
        detail_dict = {'order_live_dict':self.order_live_dict,'z_score_store_dict':self.core.z_score_store_dict,'trade_pair_dict':self.core.trade_pair_dict,
                       'tick_series_dict':self.core.tick_series_dict}
        detail_queue.put(detail_dict)
        return self
    #将penny_jump_mode永久关闭
    def penny_jump_mode_auto_switch(self):
        today = datetime.datetime.today()
        penny_end_time = datetime.datetime(today.year, today.month, today.day, 11, 00, 0)
        penny_break_time = datetime.datetime(today.year, today.month, today.day, 11, 25, 0)

        if(today>penny_end_time and len(self.order_live_dict)==0):
            self.penny_jump_mode = False
        elif(today>penny_break_time):
            self.penny_jump_mode = False
        return

    def trade(self,info_queue,handle_queue):
        self.initial_trade()
        '''
        外部初始化区分割线---------------------------------------------
        '''
        self.core = PairTrade()
        '''
        外部初始化区分割线---------------------------------------------
        '''
        while True:
            self.stop_in_rest_time()
            # self.penny_jump_mode_auto_switch()


            '''
            调用区分割线-------------------------------------------
            '''
            buy_list,sell_list = self.core.generate_buy_sell_list()
            '''
            调用区分割线-------------------------------------------
            '''

            '''
            删除已经终止的订单
            '''
            if(len(self.order_live_dict)>0):
                self.order_live_dict = {k: v for k, v in self.order_live_dict.items() if v['order_status'] != END}
            print('order_live_dict为',self.order_live_dict)
            '''
            更新order_live_dict中的max_bid_price和bid_price
            '''
            for key,value in self.order_live_dict.items():
                now_bid_price = self.core.bid_list_dict[key][-1][0]
                if(self.order_live_dict[key]['max_bid_price']<now_bid_price):
                    self.order_live_dict[key]['max_bid_price'] = now_bid_price
                self.order_live_dict[key]['now_bid_price'] = now_bid_price
            '''
            获得买单和卖单
            '''
            buy_list, raw_sell_list = self.handle_input_list(buy_list,sell_list)
            # print('撤买单',result_cancel_buy_dict,'撤卖单',result_cancel_sell_dict,'买',result_send_buy_list,'卖',result_send_sell_dict)
            print('买',buy_list,'卖',raw_sell_list)
            '''
            获得撤单列表
            '''
            cancel_buy_pending_code_list, raw_cancel_sell_pending_code_list = self.get_cancel_code_list(buy_list,raw_sell_list)
            '''
            更新epoach
            '''
            self.update_order_pending()
            '''
            止损模块
            '''
            cut_loss_cancel_order_list,cut_loss_sell_order_list = self.cut_loss()

            print('止损卖出列表',cut_loss_sell_order_list)
            '''
            合并止损项和撤单/卖项
            '''
            sell_list = list(set(raw_sell_list)|set(cut_loss_sell_order_list))
            cancel_sell_pending_code_list = list(set(raw_cancel_sell_pending_code_list)|set(cut_loss_cancel_order_list))
            '''
            取消买单区
            '''
            for code in cancel_buy_pending_code_list:
                self.order_live_dict[code]['order_status'] = BUY_ORDER_CC_TBD
                result = self.xt_trader.cancel_order_stock(self.acc,self.order_live_dict[code]['buy_order_id'])
                if(result==0):
                    self.order_live_dict[code]['order_status'] = END
                    self.order_live_dict[code]['wait_epoach'] = 0
                else:
                    self.order_live_dict[code]['order_status'] = POS
                    self.order_live_dict[code]['wait_epoach'] = 0
            '''
            取消卖单区
            '''
            for code in cancel_sell_pending_code_list:
                 self.order_live_dict[code]['order_status'] = SELL_ORDER_CC_TBD
                 result = self.xt_trader.cancel_order_stock(self.acc, self.order_live_dict[code]['sell_order_id'])
                 if (result == 0):
                     self.order_live_dict[code]['order_status'] = POS
                     self.order_live_dict[code]['wait_epoach'] = 0

                 else:
                     self.order_live_dict[code]['order_status'] = END
                     self.order_live_dict[code]['wait_epoach'] = 0
            '''
            发买单区
            '''
            for b_code in buy_list:
                self.order_live_dict.update({b_code:{'order_status':BUY_ORDER_TBD}})

                seq = self.xt_trader.order_stock_async(self.acc, b_code,
                                                                    xtconstant.STOCK_BUY, self.order_amount, xtconstant.FIX_PRICE,
                                                                    self.core.bid_list_dict[b_code][-1][0]+0.002, self.stragety_name,'b'+b_code)

                self.order_live_dict[b_code]['buy_order_price'] = self.core.bid_list_dict[b_code][-1][0]+0.002
                self.order_live_dict[b_code]['now_bid_price'] = self.core.bid_list_dict[b_code][-1][0]
                self.order_live_dict[b_code]['max_bid_price'] = self.core.bid_list_dict[b_code][-1][0]


            '''
            发卖单区
            '''
            for key in sell_list:
                self.order_live_dict[key]['order_status'] = SELL_ORDER_TBD

                seq = self.xt_trader.order_stock_async(self.acc, key,
                                                                xtconstant.STOCK_SELL, self.order_amount, xtconstant.FIX_PRICE,
                                                                self.core.ask_list_dict[key][-1][0]-0.002, self.stragety_name,'s'+key)
                self.order_live_dict[key]['sell_order_price'] = self.core.ask_list_dict[key][-1][0]-0.002

            '''
            实验性:penny jump
            '''
            # if(self.penny_jump_mode):
            #     for key, value in {k: v for k, v in self.order_live_dict.items() if v['order_status'] == POS}.items():
            #         self.order_live_dict[key]['order_status'] = SELL_ORDER_TBD
            #         seq = self.xt_trader.order_stock_async(self.acc, key,
            #                                                xtconstant.STOCK_SELL, self.order_amount, xtconstant.FIX_PRICE,
            #                                                self.order_live_dict[key]['buy_traded_price']+self.penny_jump, self.stragety_name,
            #                                                's' + key)
            #         self.order_live_dict[key]['sell_order_price'] = self.order_live_dict[key]['buy_traded_price'] + self.penny_jump

            '''
            更改变量
            '''
            self.control_change_parm(handle_queue)
            '''
            发送当前信息
            '''
            self.send_now_parm_value(info_queue)
            # self.send_detail_value(detail_queue)
            time.sleep(self.sleep_time)




if __name__ == '__main__':

    info_queue = Queue(10)
    handle_queue = Queue(10)
    # detail_queue = Queue(10)

    p_trade = Process(target=Trade().trade,args=(info_queue,handle_queue))
    p_gui = Process(target=GUI(info_queue,handle_queue).gui, args=())
    p_trade.start()
    p_gui.start()
    p_trade.join()
    p_gui.join()
