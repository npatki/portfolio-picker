import datetime
import json
import ystockquote

from collections import namedtuple
from flask import Flask
from flask import render_template
from flask import request
from numpy import array
from scipy.optimize import minimize

app = Flask(__name__)
app.debug = True

# TODO: Config file for easy tuning of the knobs.

@app.route('/')
def home():
    # TODO make template
    return render_template('home.html')

@app.route('/stock')
def _get_stock_returns():
    """ A wrapper for flask to ask get stock returns for a
    a particular ticker symbol."""
    value = get_stock_returns(request.args.get('ticker', ''))
    return json.dumps(value)

def get_stock_returns(ticker):
    """ Given args ticker=<symbol>, looks up the Yahoo!
    historical data for the company. Calculate the daily
    returns for it."""
    return_object = {}

    if ticker is None or ticker == '':
        return_object['error'] = 'No symbol given.'
        return return_object
    
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
            in historical.items()]

        if len(daily_close) < 3:
            return_object['error'] = 'Too few data points.'
            return return_object

        returns = []

        # TODO: Moving average?
        # Or add a smoothening factor to discard the day-to-day
        # noise in prices
        for i in range(len(daily_close)-1):
            now = daily_close[i]
            tomorrow = daily_close[i+1]
            returns.append((tomorrow-now)/now)
        
        # want them sorted from latest to earliest
        # because we later zip them up with similar lists
        # and some stocks may not have earlier information
        returns.reverse()

        return_object['results'] = returns
        return return_object

    # Yahoo! doesn't respond, ticker not given/valid
    except:
        return_object['error'] = 'Not a valid ticker.'
        return return_object

@app.route('/portfolio', methods=['POST'])
def _optimize():
    """ Build up the portfolio and find a set of weights
    for the portfolio with minimum risk (minimum variance)
    
    Expect POST data to be in the form:
    {
        <ticker name>: [list of values],
        <ticker name>: [list of values],
        ...
    }
    """
    return json.dumps(optimize(request.json))

def optimize(data):
    """ Perform the actual optimization of a porfolio for various
    levels of risk.
    :param data: Data describing the stock data, should be in the form:
            {
                <ticker name>: [list of returns],
                <ticker name>: [list of returns],
                ...
            }

    :returns an object describing the results for different levels
             of fixed risk. Is of the following format:
             {
                'fixed_risk': [
                    {
                        'return': <expected return>,
                        'values': {
                            <ticker name>: <proportion>,
                            <ticker name>: <proportion>,
                            ...
                        },
                        'risk': <std deviation>
                    },
                    ...
                ]
             }
             The list 'fixed_risk' shows results in order of increasing
             risk. There are currently a total of 10 levels.
    """

    Company = namedtuple("Company", ["ticker", "expected_return", "variance"])
    companies = []

    # create temp company object to track info
    for ticker in data:
        returns = data[ticker]
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
    # than another, then it's not worth buying any stocks
    # from it at the moment
    for i in range(len(companies)):
        add = True
        for j in range(len(companies)):
            if i == j:
                continue
            a = companies[i]
            b = companies[j]
            if a.expected_return < b.expected_return:
                if a.variance > b.variance:
                    add = False
                    break
        if add:
            name, ret, var = companies[i]
            tickers.append(name)
            expected_return[name] = ret
            sigma[frozenset([name])] = var

    for ticker_A in tickers:
        for ticker_B in tickers:

            returns_A = data[ticker_A]
            returns_B = data[ticker_B]
            key = frozenset([ticker_A, ticker_B])

            if key not in sigma:
                sigma[key] = covar(returns_A, returns_B)

    portfolio = Portfolio(tickers, expected_return, sigma)

    # TODO: integrate fixed return functionality with frontend
    response = {}
    fixed_risk = []

    for i in range(11):
        a = portfolio.get_highest_return(i)
        fixed_risk.append(a)

    response['fixed_risk'] = fixed_risk

    return response

def _get_monthly(daily_return):
    return (1+daily_return)**30 -1

def _get_std_dev(variance):
    return variance**0.5

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

def allocate(stock_names):
    """ API point for backend. Performs the same function as frontend.
    :param stock_names: a list of string stock ticker symbols we wish
                        to put in a portfolio
    :returns the result of calling get_portfolio for the returns given
             by stock_names.
             Returns 'Error' if something goes wrong."""
    data = {}
    for name in stock_names:
        try:
            if name in data:
                continue
            result = get_stock_returns(name)
            data[name] = result['results']
        except:
            continue
    try:
        return optimize(data)
    except:
        return 'Error'

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
        self.max_result = None
        self.min_result = None

        self.min_variance = self._get_lowest_variance()
        self.max_variance = self._get_highest_variance()
        self.delta_variance = (self.max_variance - self.min_variance)/10.0

        # set the min to 0 if it's actually a negative return
        # the optimization may not be feasible with positive bounds
        # but at least this will force the least possible min
        min_overall = min(self.expected_return.values())
        self.min_return = max(min_overall, 0)
        max_overall = max(self.expected_return.values())
        self.delta_return = (max(max_overall, 0) - self.min_return)/10.0


    def _get_highest_variance(self):
        max_variance = max([self.sigma[key] for key in self.sigma if len(key) == 1])
        out = self.get_highest_return(-1)
        if out['risk']**2 > max_variance:
            max_variance = out['risk'] ** 2
            self.max_result = out
        return max_variance

    def _get_lowest_variance(self):
        try:
            min_variance = min([self.sigma[key] for key in self.sigma
                if len(key) == 1 and self.expected_return[list(key)[0]] > 0])
        except ValueError:
            min_variance = None
        out = self.get_lowest_risk(-1)

        if min_variance is None or out['risk']**2 < min_variance:
            min_variance = out['risk']**2
            self.min_result = out

        return min_variance

    def get_highest_return(self, risk_factor):
        """ Returns an optimization that maximizes the return for
        a given risk_factor.

        :param risk_factor: A number in [0, 10] that indicates how
                            much risk we are willing to take.
                            0 is the lowest variance of an individual
                            stock, while 10 is the highest.
        """

        # functions that tell us the variance & return given weights
        var = self._fn_variance()
        ret = self._fn_return()

        if risk_factor == 0 and self.min_result is not None:
            return self.min_result
        if risk_factor == 10 and self.max_result is not None:
            return self.max_result

        # create a constraint to look for a specific variance
        if risk_factor >= 0:
            get_variance = self.min_variance + (self.delta_variance*risk_factor)

            variance_constraint = {
                'type': 'eq',
                'fun': self._fn_variance(get_variance),
                'jac': self._fn_variance_jacobian()
            }

            cons = (self._weight_constraint(), variance_constraint)
        else:
            cons = (self._weight_constraint(),)


        bnds = []
        for i in self.tickers:
            bnds.append((0.0, None))

        res = minimize(
            # maximize the returns with these constraints
            ret,
            # guess that all weights are equal
            [1.0/len(self.tickers)]*len(self.tickers),
            # maximizing so must inverse the minimizing
            args=(-1.0,),
            method='slsqp',
            jac=self._fn_return_jacobian(),
            constraints=cons,
            bounds=tuple(bnds)
        )

        # make these into a pretty object to be sent back
        values = {}

        for i in range(len(res.x)):
            values[self.tickers[i]] = res.x[i]

        response = {
            'values': values,
            'return': _get_monthly(ret(res.x)),
            'risk': _get_std_dev(var(res.x))
        }

        return response

    def get_lowest_risk(self, profit_factor):
        """ Runs an optimization that minimizes the variance for
        a given profit_factor.

        :param profit_factor: A number in [0, 10] that indicates
                              how high of a return we want overall
                              0 is the lowest return of an individual
                              stock, while 10 is the highest.
        
        :returns A list of length len(self.tickers). Number in index
                 i represents the weight of company i in self.tickers
                 (all weights add to 1)
        """
        
        # functions that tell us the variance & return given weights
        var = self._fn_variance()
        ret = self._fn_return()

        pos_ret = [i for i in self.expected_return.values() if i > 0.0]

        # edge case: when all returns are negative, just choose
        # the least negative one and return a portfolio with 100% of that
        if len(pos_ret) == 0:
            best_option = max(self.expected_return, key=self.expected_return.get)
            return self._single_stock_portfolio(
                best_option,
                _get_monthly(self.expected_return[best_option]),
                _get_std_dev(self.sigma[frozenset([best_option])])
            )

        if profit_factor >= 0:
            get_return = self.min_return + (self.delta_return*profit_factor)

            # create a constraint to look for a specific return
            return_constraint = {
                'type': 'eq',
                'fun': self._fn_return(get_return),
                'jac': self._fn_return_jacobian()
            }

            cons = (self._weight_constraint(), return_constraint)
        else:
            zero_return = {
                'type': 'ineq',
                'fun': self._fn_return(0.0),
                'jac': self._fn_return_jacobian()
            }
            cons = (self._weight_constraint(), zero_return)

        bnds = []
        for i in self.tickers:
            bnds.append((0.0, None))
        
        res = minimize(
            # minimize the variance with these constraints
            var,
            # guess that all the weights are equal
            [1.0/len(self.tickers)]*len(self.tickers),
            method='slsqp',
            jac=self._fn_variance_jacobian(),
            constraints=cons,
            bounds=tuple(bnds)
        )
        
        # make these into a pretty object to be sent back 
        values = {}

        for i in range(len(res.x)):
            values[self.tickers[i]] = res.x[i]

        response = {
            'values': values,
            'risk': _get_std_dev(var(res.x)),
            'return': _get_monthly(ret(res.x))
        }

        return response

    def _single_stock_portfolio(self, name, ret, var):
        values = {}
        for symbol in self.tickers:
            values[symbol] = 0.0
        values[name] = 1.0
        return {
            'values': values,
            'risk': _get_std_dev(var),
            'return': _get_monthly(ret)
        }

    def _fn_variance(self, val=0):
        """ Returns a function that calculates the risk of
        the portfolio given an array x of stock weights. """

        def _variance(x):
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

            return out

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
        """ Returns a dictionary representing the constraint that
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
