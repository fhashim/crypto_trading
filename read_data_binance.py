import config
from binance.client import Client

API_KEY = config.API_KEY
SECRET_KEY = config.SECRET_KEY

client = Client(API_KEY, SECRET_KEY)
client.API_URL = 'https://testnet.binance.vision/api'



