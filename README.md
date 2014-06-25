# Portfolio Picker
Portfolio Picker's objective is to optimally allocate user-inputted stocks into a portfolio using on modern portfolio theory (http://en.wikipedia.org/wiki/Modern_portfolio_theory).

## Stock Information
Given a valid ticker symbol, Portfolio Picker looks up historical stock data on Yahoo! Finance for the past 90 days using ystockquote. It uses the daily adjusted closing price to calculate the stock's expected return, risk, and covariance with other stocks given.

A period of 90 days is equivalent to the period of a financial quarter. The adjusted closing price is chosen in case of any dividends or stock splits.

## Optimization
Portfolio Picker can optimize for minimum risk given an expected return or the maximum return given an accepted risk using scipy's minimize functionality with SLSQP (http://en.wikipedia.org/wiki/Newton%27s_method). For now, it assumes short-selling is always possible. It does not (yet) allow adding riskless assets (bonds) to decrease the risk of the portfolio.

It returns portfolio by specifying the weight that each stock is worth. A negative weight indicates short-selling. Note that there are no guarantees the resulting portfolio will actually perform as predicted.

## WebApp Usage
Coming soon!
