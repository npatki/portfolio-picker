# Portfolio Picker
Portfolio Picker's objective is to optimally allocate user-inputted stocks into a portfolio using modern portfolio theory (http://en.wikipedia.org/wiki/Modern_portfolio_theory).

It optimizes for the maximum return given an accepted risk (measured as standard deviation of the return). It represents a portfolio by specifying the weight that each stock is worth as a proportion of the overall portfolio. Note that there are no guarantees the resulting portfolio will actually perform as predicted.

### Results
For any portfolio, there are 10 optimizations performed -- 1 per risk level. These levels are separated by some delta value that depends on the stocks chosen. The first represents the safest portfolio and the last is the portfolio with the highest return (the riskiest). The middle ones are equally spaced in between the two values.

The results are returned as an object. Here is an example set of results from 3 stocks:
```python
{
    'fixed_risk': [{
        'return': 0.2,
        'values': {
            'stock_a': 0.3,
            'stock_b': 0.4,
            'stock_c': 0.3
        },
        'risk': 0.12
    }, {
        'return': 0.4,
        'values': {
            'stock_a': 0.2,
            'stock_b': 0.6,
            'stock_c': 0.2
        },
        'risk': 0.15
    },{
        ...
    }]
}
```

## API Points
API points for the backend are available for asset allocation, looking up stock values, or simply running the optimization using pre-determined values.

### Portfolio Asset Allocation
Use **allocate** with the desired ticker symbols for your portfolio. The returned data will include the expected return, risk (standard deviation), and the percentage breakup by company for differing values of risk.
```python
import portfolio

google = 'goog'
facebook = 'fb'
yelp = 'yelp'

portfolio.allocate([google, facebook])
portfolio.allocate([google, facebook, yelp])
```

### Stock Values
Use **get_stock_returns** with the desired ticker symbol to get back a list of returns averaged over the last 90 days.
```python
portfolio.get_stock_returns('goog')
```

### Optimization
If the returns of the stock are already known, use **optimize** to run the optimization with the hardcoded data.
```python
stock_data = {
    'stock_a': [1, 2, 3, 4, 5],
    'stock_b': [3, 5, 7, 9, 11]
}
portfolio.optimize(stock_data)
```

## FAQs
### Where does the stock info come from?
The daily adjusted closing prices are pulled from Yahoo! Finance for the past 90 days using the ystockquote API. This can be insalled with:
```python
pip install ystockquote 
```

### How does optimization work? Is it accurate?
Portfolio Picker performs an optimization to recover the maximum expected return given a risk (standard deviation) using scipy's minimize functionality with SLSQP (http://en.wikipedia.org/wiki/Sequential_quadratic_programming).

The overall problem is non-linear and contains both equality and inequality constraints. As a result, it may sometimes fail to find the absolute global maximum, leading to a slight discrepancy in the overall risk values.

This is apparent when adding more and more stocks to a portfolio. The safest possible portfolio should never become riskier upon adding more stocks, because it's always possible to ignore the recently-added stocks. However, sometimes the algorithm cannot optimize with the additional complexity, and the risk of the safest portfolio increases by about 0.05%.

### What are the constraints on the allocation values?
All the allocation values of the individual stocks will always add up to 1 for the portfolio. This corresponds to splitting 100% of the portfolio among the given stocks. 

Furthermore, the allocation for a single stock will be in the range [0, 1]. This means that no short-selling is possible. I plan to add a toggle in the future that will allow the user to turn on short-selling. This will mean allocations can be negative (corresponding to short selling the stock) or >1 (corresponding to buying more of the stock with the extra capital from short-selling).

### Why do some stocks have an allocation of 0 for all risk levels?
Part of optimizing means that it is unwise to buy certain stocks. For example, consider the following stocks:

| Name | Return | Risk |
| --- | --- | --- |
| A | 2% | 5% |
| B | 1% | 6% |
| C | 3% | 7% | 

In this case, stock A is strictly better than C because it has a higher return for a lower risk . Therefore, the proportion of C is always 0 while the risk-return tradeoff comes only from varying A and B.

In general, a stock with greater risk is expected to have greater return!

### Is there a webapp/visualization for this?
This is in the works!
