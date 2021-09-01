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
# date_mode = 'quarterly'
date_mode = 'yearly'
df = df[(df.index >= '2018-01-01 00:00:00') & (df.index <= '2018-12-31 00:59:59')]


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
        self.size_buy = None
        self.size_sell = None

        if self.p.usebracket_buy:
            print('-' * 5, 'Using buy_bracket')
        if self.p.usebracket_sell:
            print('-' * 5, 'Using sell_bracket')

    params = dict(
        ma=bt.ind.SMA,
        p1=30,
        p2=60,
        limit=0.005,
        limdays=12 * 60,
        limdays2=1000,
        hold=24 * 60,
        usebracket_buy=False,  # buy use order_target_size
        switchp1p2_buy=False,  # buy switch prices of order1 and order2
        usebracket_sell=False,  # buy use order_target_size
        switchp1p2_sell=False,  # buy switch prices of order1 and order2

    )

    def next(self):
        if self.orefs:
            return  # pending orders do nothing

        # Buy Long
        if not self.position:
            if self.cross > 0.0:  # crossing up

                close = self.data.close[0]
                p1_buy = close * (1.0 - self.p.limit)
                p2_buy = p1_buy - 0.02 * close
                p3_buy = p1_buy + 0.02 * close

                valid1_buy = datetime.timedelta(self.p.limdays)
                valid2_buy = valid3_buy = datetime.timedelta(self.p.limdays2)

                if self.p.switchp1p2_buy:
                    p1_buy, p2_buy = p2_buy, p1_buy
                    valid1_buy, valid2_buy = valid2_buy, valid1_buy

                if not self.p.usebracket_buy:
                    self.size_buy = (
                            (self.broker.get_cash() / p1_buy) * 0.90
                    )
                    o1 = self.buy(exectype=bt.Order.Limit,
                                  price=p1_buy,
                                  valid=valid1_buy,
                                  size=self.size_buy,
                                  transmit=False)

                    print('{}: Oref {} / Buy at {}'.format(
                        self.datetime.date(), o1.ref, p1_buy))

                    o2 = self.sell(exectype=bt.Order.Stop,
                                   price=p2_buy,
                                   valid=valid2_buy,
                                   size=self.size_buy,
                                   parent=o1,
                                   transmit=False)

                    print('{}: Oref {} / Sell Stop at {}'.format(
                        self.datetime.date(), o2.ref, p2_buy))

                    o3 = self.sell(exectype=bt.Order.Limit,
                                   price=p3_buy,
                                   valid=valid3_buy,
                                   size=self.size_buy,
                                   parent=o1,
                                   transmit=True)

                    print('{}: Oref {} / Sell Limit at {}'.format(
                        self.datetime.date(), o3.ref, p3_buy))

                    self.orefs = [o1.ref, o2.ref, o3.ref]

                else:
                    os = self.buy_bracket(
                        price=p1_buy, valid=valid1_buy,
                        stopprice=p2_buy, stopargs=dict(valid=valid2_buy),
                        limitprice=p3_buy, limitargs=dict(valid=valid3_buy), )

                    self.orefs = [o.ref for o in os]

            # Sell Short
            elif self.cross < 0.0:  # crossing up:
                close = self.data.close[0]
                p1_sell = close * (1.0 + self.p.limit)
                p2_sell = p1_sell + 0.02 * close
                p3_sell = p1_sell - 0.02 * close

                valid1_sell = datetime.timedelta(self.p.limdays)
                valid2_sell = valid3_sell = datetime.timedelta(self.p.limdays2)

                if self.p.switchp1p2_sell:
                    p1_sell, p2_sell = p2_sell, p1_sell
                    valid1_sell, valid2_sell = valid2_sell, valid1_sell

                if not self.p.usebracket_sell:
                    self.size_sell = (
                            (self.broker.get_cash() / p1_sell) * 0.90
                    )
                    o1 = self.sell(exectype=bt.Order.Limit,
                                   price=p1_sell,
                                   valid=valid1_sell,
                                   size=self.size_sell,
                                   transmit=False)

                    print('{}: Oref {} / Sell at {}'.format(
                        self.datetime.date(), o1.ref, p1_sell))

                    o2 = self.buy(exectype=bt.Order.Stop,
                                  price=p2_sell,
                                  valid=valid2_sell,
                                  size=self.size_sell,
                                  parent=o1,
                                  transmit=False)

                    print('{}: Oref {} / Buy Stop at {}'.format(
                        self.datetime.date(), o2.ref, p2_sell))

                    o3 = self.buy(exectype=bt.Order.Limit,
                                  price=p3_sell,
                                  valid=valid3_sell,
                                  size=self.size_sell,
                                  parent=o1,
                                  transmit=True)

                    print('{}: Oref {} / Buy Limit at {}'.format(
                        self.datetime.date(), o3.ref, p3_sell))

                    self.orefs = [o1.ref, o2.ref, o3.ref]
                else:
                    os = self.sell_bracket(
                        price=p1_sell, valid=valid1_sell,
                        stopprice=p2_sell, stopargs=dict(valid=valid2_sell),
                        limitprice=p3_sell, limitargs=dict(valid=valid3_sell), )

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

quantstats.reports.html(returns, output='SMA/{}/Stats.html'.format(date_mode), title='BTC Sentiment')

returns.to_csv('SMA/{}/Stats_Returns.csv'.format(date_mode))
positions.to_csv('SMA/{}/Stats_Positions.csv'.format(date_mode))
transactions.to_csv('SMA/{}/Stats_transactions.csv'.format(date_mode))
gross_lev.to_csv('SMA/{}/Stats_gross_leverage.csv'.format(date_mode))
