import operator
import numpy as np

# we allow sorting of the resource contents (if sensible for the resource)
SORT_PARAM = 'sort_vals'
ASCENDING = '[asc]'
DESCENDING = '[desc]'
SORTING_OPTIONS = [ASCENDING, DESCENDING]

# for query filter params:
# When providing query filters, we will have something like:
# <url>/?paramA=<comparison>:<val>, 
# /e.g. <url>/?pval=[lte]:0.01?log2FoldChange=[gte]:2
# which will filter for pval <= 0.01 and log fold change >= 2
# The delimiter between the comparison and the value is given below:
QUERY_PARAM_DELIMITER = ':'
LESS_THAN = '[lt]'
LESS_THAN_OR_EQUAL = '[lte]'
GREATER_THAN = '[gt]'
GREATER_THAN_OR_EQUAL = '[gte]'
ABS_VAL_GREATER_THAN = '[absgt]'
ABS_VAL_LESS_THAN = '[abslt]'

def abs_val_gt(x,y):
    return np.abs(x) > y

def abs_val_lt(x,y):
    return np.abs(x) < y

OPERATOR_MAPPING = {
    LESS_THAN: operator.lt,
    LESS_THAN_OR_EQUAL: operator.le,
    GREATER_THAN: operator.gt,
    GREATER_THAN_OR_EQUAL: operator.ge,
    ABS_VAL_GREATER_THAN: abs_val_gt,
    ABS_VAL_LESS_THAN: abs_val_lt
}

