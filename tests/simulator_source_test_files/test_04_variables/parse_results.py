#!/usr/bin/env python

#
# This test checks access to variables
#

import os
import sys
import re

import pycscrape

# Test script always provides the same parameters
simulator_name = sys.argv[1]
results_file   = sys.argv[2]
map_file       = sys.argv[3]
config_name    = sys.argv[4]

# Read results file to a string
with open(results_file, 'rb') as f:
    results = f.read().decode('utf8')

errors_in_test = 0

# Set up CScrape and parse the C source files
obj = pycscrape.CScrape(debug_level=0)
obj.config(config_name)
obj.parse_file(os.path.dirname(results_file) + '/test.h')
obj.parse_file(os.path.dirname(results_file) + '/test.c')
obj.parse_readelf_output(map_file)

# Search results file for lines of the type
#    <line number<:<HEX|STR|INT|EXP>:<python expression>=<value>
line_nos           = re.findall('([0-9]*):...:.*=.*$', results, re.MULTILINE)
test_types         = re.findall('[0-9]*:(...):.*=.*$', results, re.MULTILINE)
python_expressions = re.findall('[0-9]*:...:(.*)=.*$', results, re.MULTILINE)
c_values           = re.findall('[0-9]*:...:.*=(.*)$', results, re.MULTILINE)

for index in range(len(python_expressions)):
    line_no    = int(line_nos[index])
    test_type  = test_types[index]
    py_expr    = python_expressions[index]
    c_value    = c_values[index]
    if test_type == 'STR':
        # The test expects the python expression to generate a string
        py_value = eval(py_expr)
        str = "%4d: '%s' (%d) = '%s'" % (line_no, py_expr, py_value, c_value)

    elif test_type == 'EXP':
        # The test expects the Python expression to raise an exception
        try:
            x = eval(py_expr)
            str = "%4d: eval(%s) = NO EXCEPTION" % (line_no, py_value)
            py_value = "NO EXCEPTION"
        except Exception as e:
            py_value = ('%r' % e)[:len(c_value)]  # Limit the scope of the result comparison to the C string length
            str = "%4d: eval(%s) (EXCEPTION:%r) = %s" % (line_no, py_expr, py_value, c_value)

    elif test_type == 'INT':
        # The test expects the Python expression to generate a signed integer
        py_value = eval(py_expr)
        c_value  = eval(c_value)
        str = "%4d: eval(%s) (%d) = %d" % (line_no, py_expr, py_value, c_value)

    elif test_type == 'HEX':
        # The test expects the Python expression to generate an unsigned hex number
        py_value = eval(py_expr)
        c_value  = eval(c_value)
        str = "%4d: eval(%s) (0x%08x) = 0x%08x" % (line_no, py_expr, py_value, c_value)

    else:
        str = 'Unknown test type %s at line %d' % (test_type, line_no)
        c_expr = 'X'
        c_expr = 'Y'
        

    sys.stdout.write(str)   # Print with no new-line

    # Was there an error?
    if py_value != c_value:
        errors_in_test += 1
        print('    ERROR %d' % errors_in_test)
    else:
        print('    OK')


print("ERRORS=%d" % errors_in_test)

sys.exit(errors_in_test)  # The actual value may not be returned correctly by the os. Only 0 is guarenteed.

