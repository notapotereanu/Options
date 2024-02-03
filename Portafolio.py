class Portfolio:
    def __init__(self, capital):
        self.totalCapital = capital
        self.unrializedPnL = 0
        self.rializedPnL = 0
        self.stocksOwned = 0
        self.stocksPriceBoughtAt = 0
        self.putOwned = 0
        self.putOwnedSoldAt = 0
        self.putOwnedContract = ""
        self.callOwned = 0
        self.callOwnedSoldAt = 0
        self.callOwnedContract = ""
        
        self.putStrikePrice = 0
        self.callStrikePrice = 0
    
    def __str__(self):
        return f"Total Capital: {self.totalCapital}\nUnrialized PnL: {self.unrializedPnL}\nStocks Owned: {self.stocksOwned}\nStocks Price Bought At: {self.stocksPriceBoughtAt}\nPut Owned: {self.putOwned}\nPut Owned Sold At: {self.putOwnedSoldAt}\nPut Owned Contract: {self.putOwnedContract}\nCall Owned: {self.callOwned}\nCall Owned Sold At: {self.callOwnedSoldAt}\nCall Owned Contract: {self.callOwnedContract}\nPut Strike Price: {self.putStrikePrice}\nCall Strike Price: {self.callStrikePrice}"