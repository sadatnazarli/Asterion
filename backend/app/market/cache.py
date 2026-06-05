import time

class MarketCache:
    def __init__(self, quote_ttl=60, history_ttl=3600):
        self.quotes = {}
        self.history = {}
        self.quote_ttl = quote_ttl
        self.history_ttl = history_ttl

    def get_quote(self, ticker):
        if ticker in self.quotes:
            data, timestamp = self.quotes[ticker]
            if time.time() - timestamp < self.quote_ttl:
                return data
        return None

    def set_quote(self, ticker, data):
        self.quotes[ticker] = (data, time.time())

    def get_history(self, ticker, range_str):
        key = f"{ticker}_{range_str}"
        if key in self.history:
            data, timestamp = self.history[key]
            if time.time() - timestamp < self.history_ttl:
                return data
        return None

    def set_history(self, ticker, range_str, data):
        key = f"{ticker}_{range_str}"
        self.history[key] = (data, time.time())
