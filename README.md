# mbte
Minimal Back-Testing Engine

## Core Concepts

### Price Series
- time
- price (or OHLC)
- optional volume

### Signal
- function of past prices only
- outputs desired position (e.g. -1, 0, +1)

### Execution Model
- lag (signal at t executes at t+1)
- transaction costs
- slippage (fixed or proportional)

### Portfolio Accounting
- positoins
- cash
- P&L
- returns

### Metrics
- cumulative return
- drawdown
- Sharpe (simple)
- turnover


## Absolute Must-have Constraints

### Zero-signal test
- signal = 0 alaways gives PnL=0, costs=0, Sharpe=0
- otherwise it is a failure

### Random-signal test
- signal in {-1, +1} set randomly, expects negative PnL after costs, and Sharpe is around 0 or < 0
- if it makes money it is a bug

### Known-failure test
- moving average crossover on pure random walk, should not produce persistent alpha
- otherwise it is a bug or leakage


## Things to avoid
### Over-engineering too early 
- engines
- abstractions
- frameworks

### Jumping to Production realism
- order book simulation
- queue position modeling
- latency modeling

