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

typedef struct          // Ensure that a simple struct is handled correctly
{
  int a;
} my_type1;

typedef struct         // Ensure that a struct is handled correctly
{
  int a;
  int b;
} my_type2;

typedef struct 
{
  char a;              // Ensure that b is aligned correctly after a char
  int b;
} my_type3;

typedef struct 
{
  char a;
  my_type3 my_var;     // Ensure that my_type3 size is embedded correctly
  int b;
} my_type4;


typedef struct 
{
  char a;
  unsigned char b[13]; // Ensure that arrays are handled
  int c;
} my_type5;

typedef struct 
{
  char a;
  my_type4 b[13];      // Ensure that arrays of structs are handled correctly
  int c;
} my_type6;

typedef struct 
{
  char a;
  my_type4 b[13];  
  char c;              // Ensure that c is placed correctly after the struct
} my_type7;


typedef struct 
{
  char a;
  my_type4* b;  
  char c;              // Ensure that pointers are handled correctly
} my_type8;


typedef struct 
{
  char a;              // Ensure shorts are packed correctly
  char b;
  short c;
} my_type9;



void main(void)
{
    static int FIXME1 __attribute__((used)) = 0;
    TEST_INT("obj.type_size('my_type1')", 8*sizeof(my_type1));
    TEST_INT("obj.type_size('my_type2')", 8*sizeof(my_type2));
    TEST_INT("obj.type_size('my_type3')", 8*sizeof(my_type3));
    TEST_INT("obj.type_size('my_type4')", 8*sizeof(my_type4));
    TEST_INT("obj.type_size('my_type5')", 8*sizeof(my_type5));
    TEST_INT("obj.type_size('my_type6')", 8*sizeof(my_type6));
    TEST_INT("obj.type_size('my_type7')", 8*sizeof(my_type7));
    TEST_INT("obj.type_size('my_type8')", 8*sizeof(my_type8));
    TEST_INT("obj.type_size('my_type9')", 8*sizeof(my_type9));
}

