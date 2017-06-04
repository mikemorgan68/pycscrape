// This test checks access to variables

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

enum { MY_ENUM };
enum my_enum2_t { MY_ENUM2_A, MY_ENUM2_B=-5 };

void f1(void)
{
    enum { FUNC_ENUM=10 };
}

void f2(void)
{
    enum { FUNC_ENUM=20 };
}

void f3(void)
{
    enum { FUNC_ENUM2=100 };
}


enum type1 { MY_ENUM_T=77 };
#if 0 // CScrape will parse the type2 enum because it ignores pre-processor directives
      // We are simulating enum type2 being parsed in different scope.
enum type2 { MY_ENUM_T=88 };
#endif

enum MyList_e
{
    ONE = 1,
    TWO,
    THREE,        // Comment with THREE
    TEN   = 10,   // Line for TEN
    ELEVEN
};

typedef enum Life_e {DEAD,ALIVE} Life_t;


void main(void)
{
    //
    // obj.enum()
    //

    // Simple enum without a typename
    TEST_INT("obj.enum('MY_ENUM')",      MY_ENUM);

    // Unknown enum raises an exception
    TEST_EXP("obj.enum('UNKNOWN')", "Exception(\"Missing enum 'enum:*:*:*:UNKNOWN'\",)");

    // Enum with a specified value
    TEST_INT("obj.enum('MY_ENUM2_A')",   MY_ENUM2_A);
    TEST_INT("obj.enum('MY_ENUM2_B')",   MY_ENUM2_B);
    TEST_INT("obj.enum('MY_ENUM2_B', typename='my_enum2_t')",   MY_ENUM2_B);
    TEST_EXP("obj.enum('MY_ENUM2_B', typename='my_enum_tX')", "Exception(\"Missing enum 'enum:*:*:my_enum_tX:MY_ENUM2_B'\",)");

    // Enum in header file
    TEST_INT("obj.enum('MY_ENUM_H0')",   MY_ENUM_H0);
    TEST_INT("obj.enum('MY_ENUM_H1')",   MY_ENUM_H1);
    TEST_INT("obj.enum('MY_ENUM_H99')",  MY_ENUM_H99);
    TEST_INT("obj.enum('MY_ENUM_H100')", MY_ENUM_H100);

    // Enum with the same name in two different functions
    TEST_INT("obj.enum('FUNC_ENUM', function='f1')", 10);
    TEST_INT("obj.enum('FUNC_ENUM', function='f2')", 20);
    TEST_EXP("obj.enum('FUNC_ENUM')", "Exception(\"Duplicate enum 'enum:*:*:*:FUNC_ENUM'");  // We must specify the function

    // Enum with the same name in two different files
    TEST_INT("obj.enum('FUNC_ENUM2', filename='test.c')", 100);
    TEST_INT("obj.enum('FUNC_ENUM2', filename='test.h')", 200);
    TEST_EXP("obj.enum('FUNC_ENUM2')", "Exception(\"Duplicate enum 'enum:*:*:*:FUNC_ENUM2'");  // We must specify the filename

    // Enum with the same name but with a different type. (Not allowed by C compiler, but possible if in different scope)
    TEST_INT("obj.enum('MY_ENUM_T', typename='type1')", 77);
    TEST_INT("obj.enum('MY_ENUM_T', typename='type2')", 88);
    TEST_EXP("obj.enum('MY_ENUM_T')", "Exception(\"Duplicate enum 'enum:*:*:*:MY_ENUM_T'");  // We must specify the typename

    // Enum with simpe typedef
    TEST_INT("obj.enum('DEAD',  typename='Life_e')", 0);
    TEST_INT("obj.enum('ALIVE', typename='Life_e')", 1);
    TEST_INT("obj.enum('DEAD',  typename='Life_t')", 0);
    TEST_INT("obj.enum('ALIVE', typename='Life_t')", 1);

    
    //
    // obj.enum_type()
    //
    TEST_INT("len(obj.enum_type(typename='MyList_e'))", 5);
    TEST_INT("obj.enum_type(typename='MyList_e')['ONE']['value']", 1);
    TEST_INT("obj.enum_type(typename='MyList_e')['TWO']['value']", 2);
    TEST_INT("obj.enum_type(typename='MyList_e')['THREE']['value']", 3);
    TEST_INT("obj.enum_type(typename='MyList_e')['TEN']['value']", 10);
    TEST_INT("obj.enum_type(typename='MyList_e')['ELEVEN']['value']", 11);
    TEST_INT("int('// Comment with THREE' in obj.enum_type(typename='MyList_e')['THREE']['line'])", 1);  // Demonstrate getting the source line
}


