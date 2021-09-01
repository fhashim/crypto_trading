from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import pandas as pd

import datetime  # For datetime objects

# Import the backtrader platform
import backtrader as bt

# Import quantstats to generate report.
import quantstats

df = pd.read_csv(r'Data/BTCUSDT_20170901_20210731.csv')
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)

df.loc[:, "OpenInterest"] = 0.0
df.set_index('Datetime', inplace=True)
# df = df[(df.index >= '2017-10-01 00:00:00') & (df.index <= '2017-12-31 00:59:59')]
date_mode = 'yearly'
df = df[(df.index >= '2018-01-01 00:00:00') & (df.index <= '2018-12-31 00:59:59')]


# class Binance(bt.CommissionInfo):
#     params = (
#         ("commission", 0.00075),
#         ("mult", 1.0),
#         ("margin", None),
#         ("commtype", None),
#         ("stocklike", False),
#         ("percabs", False),
#         ("interest", 0.0),
#         ("interest_long", False),
#         ("leverage", 1.0),
#         ("automargin", False),
#     )
#
#
# def getsize(self, price, cash):
#     """Returns fractional size for cash operation @price"""
#     return self.p.leverage * (cash / price)


class St(bt.Strategy):

    def notify_order(self, order):
        print('{}: Order ref: {} / Type {} / Status {}'.format(
            self.data.datetime.date(0),
            order.ref, 'Buy' * order.isbuy() or 'Sell',
            order.getstatusname()))

        if order.status == order.Completed:
            self.holdstart = len(self)

        if not order.alive() and order.ref in self.orefs:
            self.orefs.remove(order.ref)

    def __init__(self):
        ma1, ma2 = self.p.ma(period=self.p.p1), self.p.ma(period=self.p.p2)
        self.cross = bt.ind.CrossOver(ma1, ma2)

        self.orefs = list()
        self.size1 = None
        self.size2 = None
        self.size3 = None

        if self.p.usebracket:
            print('-' * 5, 'Using buy_bracket')

    params = dict(
        ma=bt.ind.SMA,
        p1=5,
        p2=15,
        limit=0.005,
        limdays=12*60,
        limdays2=1000,
        hold=24*60,
        usebracket=False,  # use order_target_size
        switchp1p2=False,  # switch prices of order1 and order2

    )

    def next(self):
        if self.orefs:
            return  # pending orders do nothing

        if not self.position:
            if self.cross > 0.0:  # crossing up

                close = self.data.close[0]
                p1 = close * (1.0 - self.p.limit)
                p2 = p1 - 0.02 * close
                p3 = p1 + 0.02 * close

                valid1 = datetime.timedelta(self.p.limdays)
                valid2 = valid3 = datetime.timedelta(self.p.limdays2)

                if self.p.switchp1p2:
                    p1, p2 = p2, p1
                    valid1, valid2 = valid2, valid1

                if not self.p.usebracket:
                    self.size1 = (
                            (self.broker.get_cash() / p1) * 0.98
                    )
                    o1 = self.buy(exectype=bt.Order.Limit,
                                  price=p1,
                                  valid=valid1,
                                  size=self.size1,
                                  transmit=False)

                    print('{}: Oref {} / Buy at {}'.format(
                        self.datetime.date(), o1.ref, p1))

                    self.size2 = (
                            (self.broker.get_cash() / p2) * 0.98
                    )
                    o2 = self.sell(exectype=bt.Order.Stop,
                                   price=p2,
                                   valid=valid2,
                                   size=self.size1,
                                   parent=o1,
                                   transmit=False)

                    print('{}: Oref {} / Sell Stop at {}'.format(
                        self.datetime.date(), o2.ref, p2))

                    self.size3 = (
                            (self.broker.get_cash() / p3) * 0.98
                    )
                    o3 = self.sell(exectype=bt.Order.Limit,
                                   price=p3,
                                   valid=valid3,
                                   size=self.size1,
                                   parent=o1,
                                   transmit=True)

                    print('{}: Oref {} / Sell Limit at {}'.format(
                        self.datetime.date(), o3.ref, p3))

                    self.orefs = [o1.ref, o2.ref, o3.ref]

                else:
                    os = self.buy_bracket(
                        price=p1, valid=valid1,
                        stopprice=p2, stopargs=dict(valid=valid2),
                        limitprice=p3, limitargs=dict(valid=valid3), )

                    self.orefs = [o.ref for o in os]

        else:  # in the market
            if (len(self) - self.holdstart) >= self.p.hold:
                pass  # do nothing in this case


cerebro = bt.Cerebro()
cerebro.broker.set_cash(1000)
cerebro.broker.setcommission(commission=0.00075)
data = bt.feeds.PandasData(dataname=df)

cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=1)
cerebro.addstrategy(St)
cerebro.addanalyzer(bt.analyzers.PyFolio)
print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
results = cerebro.run()
print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())
strat = results[0]
pyfoliozer = strat.analyzers.getbyname('pyfolio')
returns, positions, transactions, gross_lev = pyfoliozer.get_pf_items()

# To make it compatible with quantstats, remove the timezone awareness using the built-in tz_convert function.
returns.index = returns.index.tz_convert(None)


quantstats.reports.html(returns, output='SMA/Stats_{}.html'.format(date_mode), title='BTC Sentiment')
