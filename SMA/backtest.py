import pandas as pd
import backtrader as bt

df = pd.read_csv(r'Data/BTCUSDT_20170901_20210731.csv')
df['Datetime'] = pd.to_datetime(df['Datetime'], utc=True)

df.loc[:,"OpenInterest"] = 0.0
df.set_index('Datetime', inplace=True)
# df = df[df.Close.notnull()]

class Binance(bt.CommissionInfo):
    params = (
        ("commission", 0.00076), #0.00075
        ("mult", 1.0),
        ("margin", None),
        ("commtype", None),
        ("stocklike", False),
        ("percabs", False),
        ("interest", 0.0),
        ("interest_long", False),
        ("leverage", 1.0),
        ("automargin", False),
    )
def getsize(self, price, cash):
        """Returns fractional size for cash operation @price"""
        return self.p.leverage * (cash / price)


class MACD(bt.Strategy):
    params = (
        ("macd1", 12),
        ("macd2", 26),
        ("macdsig", 9),
        # Percentage of portfolio for a trade. Something is left for the fees
        # otherwise orders would be rejected
        ("portfolio_frac", 0.98),
    )

    def __init__(self):
        self.val_start = self.broker.get_cash()  # keep the starting cash
        self.size = None
        self.order = None

        self.macd = bt.ind.MACD(
            self.data,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig,
        )
        # Cross of macd and macd signal
        self.mcross = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if self.order:
            return  # pending order execution. Waiting in orderbook

        print(
            f"DateTime {self.datas[0].datetime.datetime(0)}, "
            f"Price {self.data[0]:.2f}, Mcross {self.mcross[0]}, "
            f"Position {self.position.upopened}"
        )

        if not self.position:  # not in the market
            if self.mcross[0] > 0.0:
                print("Starting buy order")
                self.size = (
                        self.broker.get_cash() / self.datas[0].close * self.p.portfolio_frac
                )
                self.order = self.buy(size=self.size)
        else:  # in the market
            if self.mcross[0] < 0.0:
                print("Starting sell order")
                self.order = self.sell(size=self.size)

cerebro = bt.Cerebro()

cerebro.broker.set_cash(1000)

# data = bt.feeds.GenericCSVData(
#     dataname=dataset_filename,
#     dtformat="%Y-%m-%dT%H:%M:%S",
#     timeframe=bt.TimeFrame.Ticks,
# )

data = bt.feeds.PandasData(dataname=df)
cerebro.adddata(data)

cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=60)

cerebro.addstrategy(MACD)

cerebro.broker.addcommissioninfo(Binance())

# Add TimeReturn Analyzers to benchmark data
cerebro.addanalyzer(
    bt.analyzers.TimeReturn, _name="alltime_roi", timeframe=bt.TimeFrame.NoTimeFrame
)

cerebro.addanalyzer(
    bt.analyzers.TimeReturn,
    data=data,
    _name="benchmark",
    timeframe=bt.TimeFrame.NoTimeFrame,
)


# Execute
results = cerebro.run()
st0 = results[0]

for alyzer in st0.analyzers:
    alyzer.print()

cerebro.plot()