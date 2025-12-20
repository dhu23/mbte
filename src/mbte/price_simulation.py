# Generate simulated prices

import math
import random
import numpy as np

from mbte.statistics import GBMParameters, generate_log_returns


def generate_gbm_prices(
        gbm_params: GBMParameters, init_price: float, n: int, rng: random.Random
):
    '''
    This generates all log returns first, r1, r2, r3, ...
    Let the initial price be S0, 
    The end result of generated prices should be
    S0 = S0 * exp(0)
    S1 = S0 * exp(0) * exp(r1) = S0 * exp(r1) 
    S2 = S0 * exp(0) * exp(r1) * exp(r2) = S0 * exp(r1 + r2)
    ....
    
    :param gbm_params: Description
    :type gbm_params: GBMParameters
    :param init_price: Description
    :type init_price: float
    :param n: Description
    :type n: int
    :param rng: Description
    :type rng: random.Random
    '''
    dt = 1
    log_returns = generate_log_returns(gbm_params, n-1, dt, rng)
    prices = init_price * np.exp(np.concatenate([[0.], np.cumsum(log_returns)]))
    return (log_returns, prices)


