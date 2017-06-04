// This test ensures that standard types are the expected sizes

#include <stdbool.h>
#include <stdint.h>
#include "test.h"

//---
// Standard functions
//---

// Print a string
void print_str(const char *s);

// Print an unsigned int as a hexadecimal number
void print_hex(const unsigned long long int x);

// Print a signed int as decimal
void print_int(const long long int x);

// Used when the evaluated Python expression must equal the C expression. Result is printed as a signed integer.
#define TEST_INT(PY_EXPR, C_VALUE)     print_int(__LINE__); print_str(":INT:" PY_EXPR); print_str("="); print_int(C_VALUE); print_str("\n"); 

// Used when the evaluated Python expression must equal the C expression. Result is printed as an unsigned hex value.
#define TEST_HEX(PY_EXPR, C_VALUE)     print_int(__LINE__); print_str(":HEX:" PY_EXPR); print_str("="); print_hex(C_VALUE); print_str("\n"); 

// Used when the evaluated Python expression is expected to cause an exception. The Exception string must match the provided string
#define TEST_EXP(PY_EXPR, PY_EXP_STR)  print_int(__LINE__); print_str(":EXP:" PY_EXPR); print_str("="); print_str(PY_EXP_STR); print_str("\n"); 

//--------------------------------------------------------

void main(void)
{
    TEST_INT("obj.type_size('bool')",                   8*sizeof(bool));
    TEST_INT("obj.type_size('unsigned char')",          8*sizeof(char));
    TEST_INT("obj.type_size('short int')",              8*sizeof(short int));
    TEST_INT("obj.type_size('unsigned int')",           8*sizeof(unsigned int));
    TEST_INT("obj.type_size('unsigned long int')",      8*sizeof(long int));
    TEST_INT("obj.type_size('unsigned long long int')", 8*sizeof(long long int));
    TEST_INT("obj.type_size('float')",                  8*sizeof(float));
    TEST_INT("obj.type_size('double')",                 8*sizeof(double));
    TEST_INT("obj.type_size('long double')",            8*sizeof(long double));
    TEST_INT("obj.type_size('unsigned int*')",          8*sizeof(unsigned int*));
}

