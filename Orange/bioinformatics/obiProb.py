import math    

def _lngamma(z):
    x = 0
    x += 0.1659470187408462e-06 / (z + 7)
    x += 0.9934937113930748e-05 / (z + 6)
    x -= 0.1385710331296526 / (z + 5)
    x += 12.50734324009056 / (z + 4)
    x -= 176.6150291498386 / (z + 3)
    x += 771.3234287757674 / (z + 2)
    x -= 1259.139216722289 / (z + 1)
    x += 676.5203681218835 / (z)
    x += 0.9999999999995183
    
    return math.log(x) - 5.58106146679532777 - z + (z - 0.5) * math.log(z + 6.5)
        
class LogBin(object):
    _max = 2
    _lookup = [0.0, 0.0]
    _max_factorial = 1
    def __init__(self, max=1000):
        self._extend(max)

    @staticmethod
    def _extend(max):
        if max <= LogBin._max:
            return
        for i in range(LogBin._max, max):
            if i > 1000: ## an arbitrary cuttof
                LogBin._lookup.append(LogBin._logfactorial(i))
            else:
                LogBin._max_factorial *= i
                LogBin._lookup.append(math.log(LogBin._max_factorial))
        LogBin._max = max

    def _logbin(self, n, k):
        if n >= self._max:
            self._extend(n + 100)
        if k < n and k >= 0:
            return self._lookup[n] - self._lookup[n - k] - self._lookup[k]
        else:
            return 0.0

    @staticmethod
    def _logfactorial(n):
        if (n <= 1):
            return 0.0
        else:
            return _lngamma(n + 1)

class Binomial(LogBin):

    def __call__(self, k, N, m, n):
        p = 1.0 * m / N
        if p == 0.0:
            if k == 0:
                return 1.0
            else:
                return 0.0
        elif p == 1.0:
            if n == k:
                return 1.0
            else:
                return 0.0
        try:
            return min(math.exp(self._logbin(n, k) + k * math.log(p) + (n - k) * math.log(1.0 - p)), 1.0)
        except (OverflowError, ValueError), er:
            print k, N, m, n
            raise
##        return math.exp(self._logbin(n, k) + math.log((p**k) * (1.0 - p)**(n - k)))

    def p_value(self, k, N, m, n):
        subtract = n - k + 1 > k
        result = sum([self.__call__(i, N, m, n) for i in (range(k) if subtract else range(k, n+1))])
        return max(1.0 - result if subtract else result, 0.0)

class Hypergeometric(LogBin):

    def __call__(self, k, N, m, n):
        if k < max(0, n + m - N) or k > min(n, m):
            return 0.0
        try:
            return min(math.exp(self._logbin(m, k) + self._logbin(N - m, n - k) - self._logbin(N, n)), 1.0)
        except (OverflowError, ValueError), er:
            print k, N, m, n
            raise

    def p_value(self, k, N, m, n):
        subtract = n - k + 1 > k
##        result = sum([math.exp(self._logbin(m, i) + self._logbin(N - m, n - i)) for i in (range(k) if subtract else range(k, n+1))])
        result = sum([self.__call__(i, N, m, n) for i in (range(k) if subtract else range(k, n+1))])
##        result /= math.exp(self._logbin(N, n))
        return max(1.0 - result if subtract else result, 0.0)


## to speed-up FDR, calculate ahead sum([1/i for i in range(1, m+1)]), for m in [1,100000]. For higher values of m use an approximation, with error less or equal to 4.99999157277e-006. (sum([1/i for i in range(1, m+1)])  ~ log(m) + 0.5772..., 0.5572 is an Euler-Mascheroni constant) 
c = [1.0]
for m in range(2, 100000):
    c.append( c[-1] + 1.0/m)

def is_sorted(l):
    return all(l[i] <= l[i+1] for i in xrange(len(l)-1))

def FDR(p_values, dependent=False, m=None, ordered=False):
    """
    If the user is sure that pvalues as already sorted nondescendingly
    setting ordered=True will make the computation faster.
    """

    if not ordered:
        ordered = is_sorted(p_values)

    if not ordered:
        joined = [ (v,i) for i,v in enumerate(p_values) ]
        joined.sort()
        p_values = [ p[0] for p in joined ]
        indices = [ p[1] for p in joined ]

    if not m:
        m = len(p_values)
    if m <= 0 or not p_values:
        return []

    if dependent: # correct q for dependent tests
        k = c[m-1] if m <= len(c) else math.log(m) + 0.57721566490153286060651209008240243104215933593992
        m = m * k

    tmp_fdrs = [p*m/(i+1.0) for (i, p) in enumerate(p_values)]
    fdrs = []
    cmin = tmp_fdrs[-1]
    for f in reversed(tmp_fdrs):
        cmin = min(f, cmin)
        fdrs.append( cmin)
    fdrs.reverse()

    if not ordered:
        new = [ None ] * len(fdrs)
        for v,i in zip(fdrs, indices):
            new[i] = v
        fdrs = new

    return fdrs

def Bonferroni(p_values, m=None):
    if not m:
        m = len(p_values)
    if m == 0:
        return []
    m = float(m)
    return [p/m for p in p_values]