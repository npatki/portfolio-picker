import datetime
import json
import os
import ystockquote

from flask import Flask
from flask import request
from numpy import array
from scipy.optimize import minimize

app = Flask(__name__)

@app.route('/')
def hello():
    return __name__ 

@app.route('/stock')
def get_stock_returns():
    """ Given args ticker=<symbol>, looks up the Yahoo!
    historical data for the company. Calculate the daily
    returns for it."""

    return_object = {}

    ticker = request.args.get('ticker', '')
    if ticker is None:
        return_object['message'] = 'No symbol given.'
    
    # look at last quarter of data
    now = datetime.datetime.now()
    before = now - datetime.timedelta(days=90)
    
    now_string = now.strftime('%Y-%m-%d')
    before_string = before.strftime('%Y-%m-%d')

    try:
        # grab quotes from Yahoo! finance
        historical = ystockquote.get_historical_prices(
                ticker,
                before_string,
                now_string)

        # use adjusted close for calculating
        # daiy returns
        daily_close = [
                float(stats['Adj Close'])
                for date, stats
                in historical.items()
                ]

        returns = []
        for i in range(len(daily_close)-1):
            now = daily_close[i]
            tomorrow = daily_close[i+1]
            returns.append((tomorrow-now)/now)
        
        # we cannot do much with 0 or 1 values
        if len(returns) < 2:
            return_object['error'] = 'Too few data points.'
            return json.dumps(return_object)
        
        # want them sorted from latest to earliest
        returns.reverse()

        return_object['results'] = returns
        return json.dumps(return_object)

    # Yahoo! doesn't respond, ticker not given/valid
    except:
        return_object['error'] = 'Not a valid ticker.'
        return json.dumps(return_object) 

@app.route('/portfolio', methods=['POST'])
def get_portfolio_min_risk():
    """ Build up the portfolio and find the set of weights
    for the portfolio with minimum risk (minimum variance)"""

    tickers = []
    expected_return = {}
    sigma = {}
    messages = []

    for ticker in request.json:
        returns = request.json[ticker]
        tickers.append(ticker)
        expected_return[ticker] = (
                reduce(lambda x, y: x+y, returns)/len(returns))

    for ticker_A in request.json:
        for ticker_B in request.json:
            returns_A = request.json[ticker_A]
            returns_B = request.json[ticker_B]
            key = frozenset([ticker_A, ticker_B])
            if key not in sigma:
                sigma[key] = covar(returns_A, returns_B)

    portfolio = Portfolio(tickers, expected_return, sigma)
    weights = portfolio.get_min_risk()
    
    min_soln = {}
    for i in range(len(tickers)):
        min_soln[tickers[i]] = weights[i]

    out = {}
    out['min_risk'] = min_soln

    return json.dumps(out)

def covar(a, b):
    """ Given that a and b are lists of daily returns, 
    returns the covariance."""

    avg_A = reduce(lambda x, y: x+y, a)/len(a)
    avg_B = reduce(lambda x, y: x+y, b)/len(b)

    points = zip(a, b)
    total = 0
    for a, b in points:
        total += (a-avg_A)*(b-avg_B)
    return total/(len(points)-1)


class Portfolio:

    """ Represents a portfolio of stock weights that
    add up to 100%.

    :param tickers: list of strick ticker symbols that
                    represent companies
    :param expected_return: dictionary of ticker --> E[return]
    :param sigma: map a single company --> variance
                  ever group of 2 companies --> covariance
                  where the keys are frozen set objects """


    def __init__(self, tickers, expected_return, sigma):
        self.tickers = tickers
        self.expected_return = expected_return
        self.sigma = sigma

    def get_min_risk(self):
        """ Runs an optimization and returns a list 
        representing the weights of the minimimum weight portfolio. 
        
        The weight in index i represents the percent of equity
        in company i of self.tickers. """
        
        cons = (self._weight_constraint(),)
        res = minimize(
            self._fn_variance(),
            [1]*len(self.tickers),
            method='slsqp',
            jac=self._fn_variance_jacobian(),
            constraints=cons
            )

        # TODO: We got min variance, but there can be multiple
        # solns for this. Optimize for max return with added
        # variance constraint for this variance.

        return res.x

    def _fn_variance(self):
        """ Returns a function that calculates the risk of
        the portfolio given an array x of stock weights. """

        def _variance(x, sign=1.0):
            out = 0

            for key, covar in self.sigma.items():
                if len(key) == 1:
                    # represents variance of single company
                    pos, = self._get_pos(key)
                    out += covar*(x[pos]**2)
                elif len(key) == 2:
                    # represents covar of two companies
                    pos1, pos2 = self._get_pos(key)
                    out += 2*x[pos1]*x[pos2]*covar

            return sign*out

        return _variance

    def _fn_variance_jacobian(self):
        """ Returns a function that calculates the jacobian 
        matrix of the risk of a portfolio given an array x of
        stock weights. """

        def _jacobian(x):
            # setup the matrix
            out = [0]*len(self.tickers)

            for key, covar in self.sigma.items():
                if len(key) == 1:
                    # represents a single company
                    pos, = self._get_pos(key)
                    out[pos] += 2*x[pos]*covar
                elif len(key) == 2:
                    # represents two companies
                    pos1, pos2 = self._get_pos(key)
                    out[pos1] += 2*x[pos2]*covar
                    out[pos2] += 2*x[pos1]*covar

            return array(out)
                
        return _jacobian

    def _weight_constraint(self):
        """ Returns a dictionary reprsenting the constraint that
        the total weights of all companies in the portfolio
        must sum to 1. """

        def _weight(x):
            out = -1
            for i in range(len(self.tickers)):
                out += x[i]
            return out

        def _jacobian(x):
            return array([1]*len(self.tickers))

        return {
                'type': 'eq',
                'fun': _weight,
                'jac': _jacobian
            }

    def _get_pos(self, fs):
        """ Returns a tuple of indicies in self.tickers that 
        are respresented in frozen set fs."""

        out = []
        for i in range(len(self.tickers)):
            if self.tickers[i] in fs:
                out.append(i)
        return tuple(out)
