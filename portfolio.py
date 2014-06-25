import datetime
import json
import os
import ystockquote

from collections import namedtuple
from flask import Flask
from flask import request
from numpy import array
from scipy.optimize import minimize

app = Flask(__name__)
app.debug = True

@app.route('/')
def home():
    # Soon to be the main template
    return "Hello world!"

@app.route('/stock')
def get_stock_returns():
    """ Given args ticker=<symbol>, looks up the Yahoo!
    historical data for the company. Calculate the daily
    returns for it."""

    return_object = {}
    ticker = request.args.get('ticker', '')

    if ticker is None or ticker == '':
        return_object['error'] = 'No symbol given.'
        return json.dumps(return_object)
    
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

        if len(daily_close) < 3:
            return_object['error'] = 'Too few data points.'
            return json.dumps(return_object)

        returns = []

        for i in range(len(daily_close)-1):
            now = daily_close[i]
            tomorrow = daily_close[i+1]
            returns.append((tomorrow-now)/now)
        
        # want them sorted from latest to earliest
        # because we later zip them up with similar lists
        # and some stocks may not have earlier information
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

    Company = namedtuple("Company", ["ticker", "expected_return", "variance"])
    companies = []

    # create temp company object to track info
    for ticker in request.json:
        returns = request.json[ticker]
        company = Company(ticker=ticker,
            expected_return=(reduce(lambda x,y: x+y, returns)/len(returns)),
            variance=covar(returns,returns))
        companies.append(company)

    # we want to sort by expected_return, then by variance
    def fn_compare(a, b):
        if a.expected_return < b.expected_return:
            return -1
        if a.expected_return > b.expected_return:
            return 1
        if a.variance < b.variance:
            return -1
        return 1

    companies = sorted(companies, cmp=fn_compare)

    # the actual state we want to compute
    tickers = []
    expected_return = {}
    sigma = {}
    messages = []

    # if a company has a lower return and a higher variance
    # than another, then it's now worth buying any stocks
    # from it at the moment
    for i in range(len(companies)-1):
        low_ret = companies[i]
        high_ret = companies[i+1]

        if low_ret.variance < high_ret.variance:
            name, ret, var = low_ret
            tickers.append(name)
            expected_return[name] = ret
            sigma[frozenset([name])] = var

    # it may always be worth buying stocks from the
    # company with the highest return
    name, ret, var = companies[-1]
    tickers.append(name)
    expected_return[name] = ret
    sigma[frozenset([name])] = var

    for ticker_A in tickers:
        for ticker_B in tickers:

            returns_A = request.json[ticker_A]
            returns_B = request.json[ticker_B]
            key = frozenset([ticker_A, ticker_B])

            if key not in sigma:
                sigma[key] = covar(returns_A, returns_B)

    portfolio = Portfolio(tickers, expected_return, sigma)

    return json.dumps(portfolio.get_median_risk())

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

    :param tickers: list of string ticker symbols that
                    represent companies
    :param expected_return: dictionary of ticker --> E[return]
    :param sigma: map a single company --> variance
                  or a group of 2 companies --> covariance
                  where the keys are frozen set objects """


    def __init__(self, tickers, expected_return, sigma):
        self.tickers = tickers
        self.expected_return = expected_return
        self.sigma = sigma

    def get_median_risk(self):
        """ Runs an optimization. Returns the weights of a portfolio
        with expected return that is half way between the minimum
        and maximum paying individual stocks. Minimizes the overall
        risk as it does so.
        
        The weight in index i represents the percent of equity
        in company i of self.tickers wrt the entire portfolio."""
        
        # functions that tell us the variance & return given weights
        var = self._fn_variance()
        ret = self._fn_return()

        # create a constraint to look for the average return
        # among the stocs we have left
        min_return = min(self.expected_return.values())
        max_return = max(self.expected_return.values())
        return_constraint = {
                'type': 'eq',
                'fun': self._fn_return((min_return + max_return)/2.0),
                'jac': self._fn_return_jacobian()
                }

        cons = (self._weight_constraint(), return_constraint)
        
        # minimize the variance with these constraints
        res = minimize(
            var,
            [1/len(self.tickers)]*len(self.tickers),
            method='slsqp',
            jac=self._fn_variance_jacobian(),
            constraints=cons
            )
        
        # make these into a pretty object that to be sent back 
        values = {}

        for i in range(len(res.x)):
            values[self.tickers[i]] = res.x[i]

        response = {
                'values': values,
                'return': ret(res.x),
                'variance': var(res.x),
                'expected': (min_return+max_return)/2.0
                }
        
        return response

    def _fn_variance(self, val=0):
        """ Returns a function that calculates the risk of
        the portfolio given an array x of stock weights. """

        def _variance(x, sign=1.0):
            out = -val 

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

    def _fn_return(self, val=0):
        """ Returns a function that calculates the overall
        expected return of the portfolio given an array x of
        stock weights. """

        def _return(x, sign=1.0):
            out = -val

            for i in range(len(self.tickers)):
                name = self.tickers[i]
                out += x[i]*self.expected_return[name]

            return sign*out

        return _return

    def _fn_return_jacobian(self):
        """ Returns a function that calculates the jacobian
        matrix of the portfolio's expected return given an array
        x of stock weights. """

        def _jacobian(x, sign=1.0):
            out = []
            for name in self.tickers:
                out.append(self.expected_return[name]*sign)

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
