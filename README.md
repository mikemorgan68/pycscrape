# pycscrape
A Python library for gathering information from C source files.


TODO: THIS LIBRARY IS NOT YET FINISHED. PYPI INSTALL NOT WORKING CORRECTLY.


=========
pyCScrape
=========

:Author: `Mike Morgan`


.. contents::
    :backlinks: none

.. sectnum::


Introduction
============

What is pyScrape?
-----------------

**pyCScrape** is a library for extracting information from C source code. It is built upon pycparser,
but is easier to use.  It's main use case is allowing Python scripts to interact with C applications.

Using gdbserver, it would be possible to peek and poke variables by name.

PyCScrape works with Python 2 or Python 3.


Required libraries
------------------
PyCScrape imports the pycparser library (v2.17 or higher).


How do you gather information about a C application?
----------------------------------------------------

It is assumed you have access to the C source for the application. You simply need to create the pyCScrape 
object and parse the file. E.g.

Consider the C file  main.c:
    
    typedef enum { JAN, FEB, MARCH, APR, MAY, JUNE, JULY, AUG, SEPT, OCT, NOV, DEC } Month_t;
    Month_t month;

    void main(void)
    {
        month = JAN;
        process_Month(month);
    }
 
We could write a script to print all of the Month_t enum names and values

    import pycscrape

    data = pycscrape.CScrape()
    data.parse_file('main.c')  # Add info from main.c to data

    # Print the values of all Month_t enums
    enums = data.enum_type(typename='Month_t') # Get a dict of all Month_t enum values
    for enum_name in enums:
        print("%s = %d" % (enum_name, enums[enum_name]['value']))

PyCScrape will gather information about enums, global variables (including addresses), typedefs, 
structures and functions (including addresses).  Obtaining the addresses of variables and functions 
requires an extra step of processing the linkler output not shown in the example above.


Do I need to supply my C source code with my python script?
-----------------------------------------------------------
No. PyCScrape can collate all the information it has gathered into a json data string. Scraping can
be performed at the compilation stage and the json string created then.  Only the string needs to be
supplied with your script.


Installing
==========

Using pip
---------
TODO

Install directly
----------------
PyCScrape requires pycparser.  TODO


