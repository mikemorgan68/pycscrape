#!/usr/bin/env python
#
# This script runs all of the tests against all of the compiler/simulators
#
#  Usage:
#    simulator_tests.py
#         Run all of the tests against all of the simulators
#    simulator_tests.py  sim=gcc5_arm32_m3_little  sim=gcc5_arm64_little
#         Run all of the tests against the two simulators 'gcc5_arm32_m3_little' 
#         and 'gcc5_arm64_little'
#    simulator_tests.py  test=test_01_sizeof  test=test_02_sizeof_user_type
#         Run all of the two tests 'test_01_sizeof' and 'test_02_sizeof_user_type' 
#         against all of the simulators
#    simulator_tests.py  test=test_01_sizeof  sim=gcc5_arm32_m3_little
#         Run all of the test 'test_01_sizeof' against the simulator 'gcc5_arm32_m3_little' 
#    simulator_tests.py  test=test_01_sizeof  always_compile
#         Run all of the test 'test_01_sizeof' and always compile rather than using the cached simulator result.
#

import os
import sys
import glob
import filecmp
import shutil
import re

try:
    pypath = os.environ['PYTHONPATH']
except:
    pypath = ''

# Add the library to the library path
project_folder = os.path.abspath(os.path.dirname(__file__) + '/..')
sys.path[0:0] = [project_folder]
pypath = project_folder + ':' + pypath

# FIXME ######################### Temp setting because we have not installed pycparser
print("FIXME install pycparser")
sys.path[0:0] = [os.path.abspath(project_folder + '/../pycparser-2.17')]
pypath = sys.path[0] + ':' + pypath
# FIXME ######################### 

import pycscrape


SRC_FILES_DIR = 'simulator_source_test_files'
SIM_DIR       = 'simulators'

def run_test(simulator_dir, src_dir, always_compile):
    simulator_name = os.path.basename(simulator_dir)
    # Make a cache folder
    cache_dir = simulator_dir + '/cache_' + os.path.basename(src_dir)
    try: 
        os.makedirs(cache_dir)
    except OSError:
        if not os.path.isdir(cache_dir):
            raise
    # Get a list of all the source test files (.c or .h)
    source_files = glob.glob(src_dir + '/*.[ch]')
    # Are any of the files different from the cached files?
    different = always_compile
    for file in source_files:
        if different:
            pass # No need to do anything, we know the file set is different
        elif not os.path.isfile(cache_dir + '/' + os.path.basename(file)):
            # The file does not exist - set as 'different'
            different = True
        elif not filecmp.cmp(file, cache_dir + '/' + os.path.basename(file), False):
            different = True

    # If the cached files are different, we need to compile and run the simulator again
    if different:
        print("Building test...")
        # Delete everything in the cache folder
        for f in glob.glob(cache_dir + '/*'):
            os.remove(f)
        # Run the script to create the new output
        cmd  = 'cd "' + cache_dir + '" ; '
        cmd += simulator_dir + '/compile_and_run'
        for f in glob.glob(src_dir + '/*.c'):
            cmd += ' "' + f + '"'
        os.system(cmd)

        # Does the results.txt file have 'TEST COMPLETED'?
        if not os.path.isfile(cache_dir + '/results.txt'):
            print("ERROR: No results.txt file")
            sys.exit(1)
        elif not '\nTEST COMPLETED\n' in open(cache_dir + '/results.txt').read():
            print("ERROR: Results file does not have 'TEST COMPLETED'")
            sys.exit(1)
        # Copy source files to cache folder - so we may compare then on the next run
        for f in source_files:
            shutil.copy2(f, cache_dir)

    #
    # Look for   \nCONFIG_NAME:<name>\n
    # in results file
    #
    with open(cache_dir + '/results.txt', 'rb') as f:
        results = f.read().decode('utf8')
    try:
        config_name = re.search('(?<=^CONFIG_NAME:).*$', results, re.MULTILINE).group(0)
    except:
        print("ERROR: Could not find 'CONFIG_NAME:'")
        sys.exit(1)
    print('Config Name: ' + config_name)

    # Parse the results looking for errors using the tests parser   parse_results.py
    errors=0

    cmd  = 'export PYTHONPATH="'+src_dir+'/../../..:'+pypath+'" ; '
    cmd += 'python2 "'+src_dir+'/parse_results.py" '
    cmd += '"' + simulator_name + '" '
    cmd += '"' + cache_dir + '/results.txt' + '" '
    cmd += '"' + cache_dir + '/results.map' + '" '
    cmd += '"' + config_name + '" '

    print("python2")
    if os.system(cmd) != 0:
        errors += 1

    cmd  = 'export PYTHONPATH="'+src_dir+'/../../..:'+pypath+'" ; '
    cmd += 'python3 "'+src_dir+'/parse_results.py" '
    cmd += '"' + simulator_name + '" '
    cmd += '"' + cache_dir + '/results.txt' + '" '
    cmd += '"' + cache_dir + '/results.map' + '" '
    cmd += '"' + config_name + '" '

    print("python3")
    if os.system(cmd) != 0:
        errors += 1

    return errors

            
def main():

    sims = []
    tests = []
    always_compile = False
    # Check the command line to see if specific tests / compilers have been specified
    for arg in sys.argv[1:]:
        if arg[:4] == 'sim=':
            sims.append(arg[4:])
        elif arg[:5] == 'test=':
            tests.append(arg[5:])
        elif arg == 'always_compile':
            always_compile = True
        else:
            print("ERROR: Unknown option %s" % arg)
            sys.exit(1)

    # Decide which simulators to test against
    if len(sims) == 0:
        # No simulators specified, get a list of simulators from the folder names
        simulator_dirs = glob.glob(project_folder + '/tests/' + SIM_DIR + '/*')
    else:
        simulator_dirs = []
        for sim in sims:
            simulator_dirs.append(project_folder + '/tests/' + SIM_DIR + '/' + sim)

    # Decide which tests to run
    if len(tests) == 0:
        # No tests specified, get a list of tests from the folder names
        src_dirs = glob.glob(project_folder + '/tests/' + SRC_FILES_DIR + '/*')
    else:
        src_dirs = []
        for test in tests:
            src_dirs.append(project_folder + '/tests/' + SRC_FILES_DIR + '/' + test)


    tests_with_errors = 0

    # Run each of the tests on each of the simulators
    for simulator_dir in simulator_dirs:
        for src_dir in src_dirs:
            print("Build type: " + os.path.basename(simulator_dir))
            print("Test      : " + os.path.basename(src_dir))
            tests_with_errors += run_test(simulator_dir, src_dir, always_compile)

    print("Tests with errors: %d" % tests_with_errors)

if __name__ == "__main__":
    main()

