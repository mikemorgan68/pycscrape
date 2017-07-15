#-----------------------------------------------------------------
#    pycscrape: Python library for gathering information from C source files.
#    Copyright (C) 2017  Mike Morgan  (mikemorgan@blueyonder.co.uk)
#
#    This library is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This library is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this library.  If not, see <http://www.gnu.org/licenses/>.
#-----------------------------------------------------------------
#
#  FIXME - about the library and this file
#-----------------------------------------------------------------
__version__ = '0.07'

import sys
import os
import json
import re
import copy


class CScrape():
    class objx: 
        pass
    def __init__(self, debug_level=0):
        self.functions = []
        # The typdef member is a dict whose key is the typedef name and has the following keys
        #   'filename'       - Filename the 'typedef' was defined in
        #   'line_number'    - Line number the 'typedef' was defined on
        #   'size'           - Number of bits taken up byt the type
        #   'exception'      - Either None or an expection object explaining the problem with the typedef.
        #   'types'          - List object containing all the types. For a simple 'typedef int name', this would have only one element.
        #      []            - Each item in the list consists of a dict object with the following elements
        #      'type_name'   - Name of the type
        #      'var_name'    - For simple 'typedef int name', this would be None. For struct typedefs, this would be the element name.
        #      'line_number' - Line number the 'typedef struct' element was defined on
        #      'line'        - Text of source line the element was defined on
        #      'array'       - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]
        #      'ptr'         - Number of ptr specifiers. E.g. 'int**' would be 2.
        #      'offset'      - Bit offset of the element from the start of the list
        #      'size'        - Bit size of the element
        self.typedefs = dict()

        # The variables member is an array of dict items with following keys
        #   'name'          - Name of variable
        #   'filename'      - Filename the variable was declared in
        #   'line_number'   - Line number the variable was declared on
        #   'line'          - C Source line containing the declaration
        #   'type'          - Name of type e.g. 'int'
        #   'array'         - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]
        #   'ptr'           - Number of ptr specifiers. E.g. 'int**' would be 2.
        #   'size'          - Size of the variable in bits.
        #   'function'      - The function the variable is defined in (or None if defined in module scope).
        #   'exception'     - Either None or an expection object explaining the problem with the declaration.
        self.variables = []

        # The enums member is a list of dict elements each with the following keys
        #   'function'       - Function name if enum was defined in a function. Otherwise None
        #   'filename'       - Filename the function was defined in
        #   'line_number'    - Line number the function was defined on
        #   'name'           - Typename of the enum
        #   'exception'      - Either None or an expection object explaining the problem with the function definition.
        #   'values'         - dict with entry for each enum. enum name is the key
        #       'line_number'- Line number for the value
        #       'line'       - Source line the value was defined on
        #       'value'      - Value of enum
        self.enums = []

        # The types member is a dict of fundamental types. The key is the type name (e.g. 'unsigned short'). Each
        # element is a dict with the following keys
        #    'bit_size'    - Size of the object in bits
        #    'alignment'   - The alignment that the compiler will use (in bits)
        #    'signed'      - Decides if the type is signed or unsigned.
        # Note: The naming of the types follows the naming defined in collate_types()
        self.types = dict()

        self.previous_queries = dict() # Speeds up access to previously searched for queries
        self.debug_level = debug_level # Debug output level
        self.source_lines = []         # Parsed source lines of previous parse call.
        self.within_function = None    # Set to the function name when processing inside a function.
        self.level = 0                 # Set to the 'child' level currently processing
        self.filename = None
        self.enum_type_mix = None
        self.class_name = 'CScrape'
        self.types['int8_t']             = { 'bit_size': 8, 'alignment': 8, 'signed': True  }
        self.types['uint8_t']            = { 'bit_size': 8, 'alignment': 8, 'signed': False }
        self.types['int16_t']            = { 'bit_size':16, 'alignment':16, 'signed': True  }
        self.types['uint16_t']           = { 'bit_size':16, 'alignment':16, 'signed': False }
        self.types['int32_t']            = { 'bit_size':32, 'alignment':32, 'signed': True  }
        self.types['uint32_t']           = { 'bit_size':32, 'alignment':32, 'signed': False }
        self.types['int64_t']            = { 'bit_size':64, 'alignment':64, 'signed': True  }
        self.types['uint64_t']           = { 'bit_size':64, 'alignment':64, 'signed': False }
        self.config_arm32()
        
        # The map_var_data paramater is an array of dict items. Each item corresponds to an element found
        # in the map file (or equivalent).
        # The dict has the following keys
        #   'name' - Name of variable
        #   'func' - Function that the variable was defined in (in the case of static). If global,
        #            the value is ''. If unknown, the value is None.
        #   'size' - The size of the object or None if unknown.
        #   'addr' - The address of the object or None if unknown.
        #   'file' - The C source file (excluding path) that the variable was found in or None if unknown.
        self.map_var_data  = []

        # The map_func_data paramater is an array of dict items derived from the map file (or equivalent). Each 
        # element corresponds to a function found. The dict has the following keys
        #   'name' - Name of function
        #   'addr' - Address of function or None if unknown
        #   'size' - Size of the function or None if unknown
        #   'file' - The C source file (excluding path) that the function was found in or None if unknown.
        self.map_func_data = []

        
    def config(self, config_name):
        if config_name=='arm32':
            self.config_arm32()
        else:
            raise Exception("Unknown configuration name " + config_name)
   
    # Configure the object for a generic 32 bit ARM compiler
    def config_arm32(self):
        self.types['bool']               = { 'bit_size': 8, 'alignment': 8, 'signed': False }
        self.types['_Bool']              = self.types['bool']
        self.types['float']              = { 'bit_size':32, 'alignment':32, 'signed': True }
        self.types['double']             = { 'bit_size':64, 'alignment':64, 'signed': True }
        self.types['double long']        = { 'bit_size':64, 'alignment':64, 'signed': True }
        self.types['signed char']        = self.types['int8_t']
        self.types['unsigned char']      = self.types['uint8_t']
        self.types['signed short']       = self.types['int16_t']
        self.types['unsigned short']     = self.types['uint16_t']
        self.types['signed int']         = self.types['int32_t']
        self.types['unsigned int']       = self.types['uint32_t']
        self.types['signed long']        = self.types['int32_t']
        self.types['unsigned long']      = self.types['uint32_t']
        self.types['signed long long']   = self.types['int64_t']
        self.types['unsigned long long'] = self.types['uint64_t']
        self.DEFAULT_CHAR_SIGN = 'signed'        # Is 'char' signed or unsigned? Either 'signed' or 'unsigned'
        self.endian            = 'little'        # 'little' or 'big' - as used by to_bytes and from_bytes functions
        self.ENUM_TYPE         = 'signed int'    # Standard C
        self.POINTER_SIZE      = 32
        self.DEFAULT_ALIGNMENT = 32
        self.STRUCT_ALIGNMENT  = 32

        
    # Take an array of type names, e.g. ['short', 'int'] and return a single name e.g. 'signed short'    
    # e.g.
    #   int                  --> signed int
    #   int short            --> signed short
    #   short int            --> signed short
    #   unsigned short int   --> unsigned short
    #   short unsigned int   --> unsigned short
    #   short int unsigned   --> unsigned short
    def collate_types(self, names):
        # Sort the list into alphabetical order
        names.sort();
        str = ''
        for n in names:
            if n != '':
                str += n + ' '
        str = str[:-1]
        # int
        if str == 'int':                      str = 'signed int'
        if str == 'int unsigned':             str = 'unsigned int'
        if str == 'int signed':               str = 'signed int'
        # short
        if str == 'short':                    str = 'signed short'
        if str == 'short unsigned':           str = 'unsigned short'
        if str == 'short signed':             str = 'signed short'
        if str == 'int short':                str = 'signed short'
        if str == 'int short unsigned':       str = 'unsigned short'
        if str == 'int short signed':         str = 'signed short'
        # char
        if str == 'char':                     str = self.DEFAULT_CHAR_SIGN + ' char'
        if str == 'char unsigned':            str = 'unsigned char'
        if str == 'char signed':              str = 'signed char'
        # long
        if str == 'long':                     str = 'signed long'
        if str == 'long unsigned':            str = 'unsigned long'
        if str == 'long signed':              str = 'signed long'
        if str == 'int long':                 str = 'signed long'
        if str == 'int long unsigned':        str = 'unsigned long'
        if str == 'int long signed':          str = 'signed long'
        # long long
        if str == 'long long':                str = 'signed long long'
        if str == 'long long unsigned':       str = 'unsigned long long'
        if str == 'lobg long signed':         str = 'signed long long'
        if str == 'int long long':            str = 'signed long long'
        if str == 'int long long unsigned':   str = 'unsigned long long'
        if str == 'int long long signed':     str = 'signed long long'

        return str


    # Return the size in bits of the given type    
    def type_size(self, type_name):
        # If the type name is a pointer, return the pointer size
        if type_name[-1] == '*':
            return self.POINTER_SIZE
        # If the type name is something like 'unsigned char', make it into a formal name
        if type_name.find(' ') != -1:
            type_name = self.collate_types(type_name.split(' '))
        # See if the type is a standard type
        try:
            return self.types[type_name]['bit_size']
        except:
            pass
        # The type must be a user defined type
        try:
            return self.typedefs[type_name]['size']
        except:
            pass
        raise SyntaxError('Unknown type %s' % type_name)
        
    
    # Return the alignment in bits of the given type    
    def type_alignment(self, type_name):
        # If the type name is a pointer, return the pointer alignment
        if type_name[-1] == '*':
            return self.POINTER_SIZE
        try:
            return self.types[type_name]['alignment']
        except:
            pass
        try:
            return self.typedefs[type_name]['alignment']
        except:
            pass
        raise SyntaxError('Unknown type %s' % type_name)
        
    
    # Get the value of the node.
    # If the node is an expression, it will be calculated e.g. '5 * sizeof(int)'
    def GetValue(self, node):
        # See if the node is a simple value
        if node.__class__.__name__ == 'Constant':
            value = node.value
            original_value = value
            try:
                while value[-1] == 'U' or \
                      value[-1] == 'u' or \
                      value[-1] == 'L' or \
                      value[-1] == 'l':
                    value = value[:-1]
                if value[0] == "'":
                    return ord(value[1])
                value = eval(value)
                if (type(value) is float) or (type(value) is int):
                    return value
                raise
            except:
                raise SyntaxError("Could not parse constant '" + original_value + "'")
        
        if node.__class__.__name__ == 'BinaryOp':
            left  = self.GetValue(node.left)
            right = self.GetValue(node.right)
            if node.op == '+':
                return left + right
            if node.op == '-':
                return left - right
            if node.op == '*':
                return left * right
            if node.op == '/':
                if (type(left)  is int) and \
                   (type(right) is int):
                    return left // right
                else:
                    return left / right
            if node.op == '<<':
                    return left << right
            if node.op == '>>':
                    return left >> right
            if node.op == '&':
                    return left & right
            if node.op == '|':
                    return left | right
            if node.op == '^':
                    return left ^ right
            raise SyntaxError("Unknown BinaryOp '" + node.op + "'")
        
        if node.__class__.__name__ == 'UnaryOp':
            right = self.GetValue(node.expr)
            if node.op == '+':
                return right
            if node.op == '-':
                return -right
            if node.op == '~':
                return ~right
            if node.op == 'sizeof':
                return (self.type_size(right) + 7) // 8  # Divide by 8 because sizeof() returns bytes
            raise SyntaxError("Unknown UnaryOp '" + node.op + "'")
        
        if node.__class__.__name__ == 'Typename':
            return self.collate_types(node.type.type.names)
            
        raise SyntaxError("Unknown expression type '" + node.__class__.__name__ + "'")
        return 0
        
    
    # Process a Decl (variable declaration). 
    # e.g. 'int* MyVar;'
    # Append to self.variables a dict() object with the following keys
    # All variables outside of functions are added. Only static functions within functions are added.
    #   'name'          - Name of variable
    #   'filename'      - Filename the variable was declared in
    #   'line_number'   - Line number the variable was declared on
    #   'line'          - C Source line containing the declaration
    #   'type'          - Name of type e.g. 'int'
    #   'array'         - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]
    #   'ptr'           - Number of ptr specifiers. E.g. 'int**' would be 2.
    #   'size'          - Size of the variable in bits.
    #   'function'      - The function the variable is defined in (or None if defined in module scope).
    #   'exception'     - Either None or an expection object explaining the problem with the declaration.
    #
    # Variables declared within a function will only be added if defined as 'static'.
    #
    # Returns True if an item was added to self.variables
    #
    # @todo
    #   int x[];
    #
    def handle_decl(self, node):
        # Is this a variable defined within a function but without the 'static' keyword. If so, ignore the declaration.
        if self.within_function != None and not 'static' in node.storage:
            return False
        if 'enumerators' in dir(node):
            # This happens when enums are used e.g.  'typedef enum Life_e {DEAD,ALIVE} Life_t;'. 
            return False
        var_data = dict()
        var_data['name']        = node.name
        var_data['filename']    = self.filename
        var_data['line_number'] = node.coord.line
        var_data['line']        = self.source_lines[node.coord.line]
        var_data['exception']   = None
        var_data['line']        = self.source_lines[node.coord.line]
        try:
            node_name, node = node.children()[0]
            node_name, possible_enum_node = node.children()[0]
            # Handle enums e.g.  enum enum_type { A, B} var_name;
            if possible_enum_node.__class__.__name__ == 'Enum':
                self.handle_enum(possible_enum_node)
            # Handle arrays
            array = []
            while node.__class__.__name__ == 'ArrayDecl':
                value = self.GetValue(node.dim)
                array.append(int(value))
                node_name, node = node.children()[0]
            # Handle ptrs
            ptr = ''
            while node.__class__.__name__ == 'PtrDecl':
                node_name, node = node.children()[0]
                ptr += '*'
            
            # Is this not a variable declaration?
            if node.__class__.__name__ != 'TypeDecl':
                return
            if not possible_enum_node.__class__.__name__ == 'Enum':
                var_data['type'] = self.collate_types(node.type.names)
            else:
                var_data['type'] = 'enum'
                var_data['enum_name'] = possible_enum_node.name
            var_data['ptr'] = len(ptr)
            var_data['function'] = self.within_function
            var_data['array'] = array
            # Calculate the size of the variable
            var_data['size'] = self.type_size(var_data['type'])
            if len(ptr) != 0:
                var_data['size'] = self.POINTER_SIZE
            for i in array:
                var_data['size'] *= i
        except Exception as e:
            var_data['exception'] = e
        # Append the variable to variables dictionary
        self.variables.append(var_data)
        if self.debug_level >= 10:
            print('%s: Variable: %s' % (self.class_name, repr(var_data)))
        return True
    
        
    # Process 'Enum'
    # e.g. enum numbers {ONE=1, TWO=2 };
    # Append to self.enums a dict with the following keys:
    #   'function'       - Function name if enum was defined in a function. Otherwise None
    #   'filename'       - Filename the function was defined in
    #   'line_number'    - Line number the function was defined on
    #   'name'           - Name of the enum
    #   'exception'      - Either None or an expection object explaining the problem with the function definition.
    #   'values'         - dict with entry for each enum. enum name is the key
    #       'line_number'- Line number for the value
    #       'line'       - Source line the value was defined eith
    #       'value'      - Value of enum
    def handle_enum(self, node):
        enum = dict()
        enum['filename'] = self.filename
        enum['line_number'] = node.coord.line
        enum['function'] = self.within_function
        enum['name'] = node.name
        enum['exception'] = None
        values = dict()
        enum_value = 0
        # Get the values
        try:
            node = node.values
            if node == None:  # Does the enum have no enumerators e.g.   'enum my_enum_type var_name;'
                return
            for value_node in node.enumerators:
                enum_item = dict()
                enum_item['line_mumber'] = value_node.coord.line
                enum_item['line'] = self.source_lines[value_node.coord.line]
                if value_node.value == None:
                    enum_item['value'] = enum_value
                else:
                    enum_item['value'] = int(self.GetValue(value_node.value))
                enum_value = enum_item['value'] + 1
                values[value_node.name] = enum_item
        except Exception as e:
            enum['exception'] = e
        enum['values'] = values
        if self.debug_level >= 10:
            print('%s: Enum: %s' % (self.class_name, repr(enum)))
        self.enums.append(enum)
        # Was this enum like 'typedef enum Life_e {DEAD,ALIVE} Life_t;' ?
        if self.enum_type_mix != None:
            # Create an identical enum with the name 'Life_t'
            enum2 = copy.deepcopy(enum)
            enum2['name'] = copy.deepcopy(self.enum_type_mix)
            self.enum_type_mix = None 
            self.enums.append(enum2)
            
        
    
    # Process a FuncDef. (Function definition) 
    # e.g. 'int* MyFunc(const int value)'
    # Append to self.functions a dict() object with the following keys:
    #   'name'           - Name of function
    #   'filename'       - Filename the function was defined in
    #   'line_number'    - Line number the function was defined on
    #   'line'           - Source line for the definition
    #   'type'           - Name of return type e.g. 'int'
    #   'ptr'            - Number of ptr specifiers for return type.  E.g. 'int**' would be 2.
    #   'exception'      - Either None or an expection object explaining the problem with the function definition.
    #   'params'         - List of parameters - each element is a dict() with the following keys
    #      'name'  - Name of parameter type e.g. 'x'
    #      'type'  - Type of parameter type e.g. 'int'
    #      'ptr'   - Number of ptr specifiers for parameter type.  E.g. 'int**' would be 2; 'int' would be 0.
    #      'array' - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]; 'int' would be []
    # TODO: 
    #    Varidac '...' not working.
    def handle_funcdef(self, node):
        node_name, decl_node      = node.children()[0]
        node_name, funcdecl_node  = decl_node.children()[0]
        node_name, paramlist_node = funcdecl_node.children()[0]
        func_name = decl_node.name
        func_data = dict()
        ptr = ''
        node = decl_node.type.type
        while node.__class__.__name__ == 'PtrDecl':
            node_name, node = node.children()[0]
            ptr += '*'
        func_data['name'] = decl_node.name
        func_data['filename'] = self.filename
        func_data['line_number'] = node.coord.line
        func_data['exception'] = None
        func_data['line'] = self.source_lines[node.coord.line]
        try:
            func_data['type'] = self.collate_types(node.type.names)
            func_data['ptr'] = len(ptr)
            func_data['params'] = []
            
            for param_node in paramlist_node.params:
                param = dict()
                param['name'] = param_node.name
                param_node = param_node.type
                # Handle ptrs
                ptr = ''
                while param_node.__class__.__name__ == 'PtrDecl':
                    param_name, param_node = param_node.children()[0]
                    ptr += '*'
                param['type'] = self.collate_types(param_node.type.names)
                param['ptr'] = len(ptr)
                if param['name'] != None:  # Function may not have any parameters
                    func_data['params'].append(param)
        except Exception as e:
            func_data['exception'] = e
            
        self.functions.append(func_data)
        if self.debug_level >= 10:
            print('%s: Function: %s' % (self.class_name, repr(func_data)))
        # Remember the function we are in
        self.within_function = func_name
            
        
    # Handle 'typedef' keyword. Append to self.typedefs a dict() object with the 
    # following elements
    #   'filename'       - Filename the 'typedef' was defined in
    #   'line_number'    - Line number the 'typedef' was defined on
    #   'size'           - Number of bits taken up byt the type
    #   'exception'      - Either None or an expection object explaining the problem with the typedef.
    #   'types'          - List object containing all the types. For a simple 'typedef int name', this would have only one element.
    #      []            - Each item in the list consists of a dict object with the following elements
    #      'type_name'   - Name of the type
    #      'var_name'    - For simple 'typedef int name', this would be None. For struct typedefs, this would be the element name.
    #      'line_number' - Line number the 'typedef struct' element was defined on
    #      'line'        - Text of source line the element was defined on
    #      'array'       - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]
    #      'ptr'         - Number of ptr specifiers. E.g. 'int**' would be 2.
    #      'offset'      - Bit offset of the element from the start of the list
    #      'size'        - Bit size of the element
    def handle_typedef(self, node):
        # Determine the type of typedef
        typedef_type = 'unknown'
        try:
            type = node.type.type.names   # This will raise an exception if the typedef is not a simple typedef
            typedef_type = 'simple'
        except:
            pass
        try:
            type = node.type.type.name    # This will raise an exception if the typedef is not a struct typedef
            typedef_type = 'struct'
        except:
            pass
            
        typedef_data = dict()
        typedef_data['filename'] = self.filename
        typedef_data['line_number'] = node.coord.line
        typedef_data['line'] = self.source_lines[node.coord.line]
        typedef_data['exception'] = None
        typedef_name = node.name
        ignore_until_line_no = 0
        if typedef_type == 'simple':
            types = []
            type_element = dict()
            type_element['typedef_type'] = typedef_type
            type_element['line_number'] = typedef_data['line_number']
            type_element['line'] = typedef_data['line']
            type_element['type_name'] = self.collate_types(node.type.type.names)
            type_element['var_name'] = None # This is meaningless for simple typedefs
            type_element['offset'] = 0
            type_element['array']       = []
            type_element['ptr']         = ''
            type_element['size'] = self.type_size(type_element['type_name'])
            type_element['alignment'] = self.type_alignment(type_element['type_name'])
            types.append(type_element)
            typedef_data['types'] = types
            typedef_data['size'] = type_element['size']
            typedef_data['alignment'] = self.type_alignment(type_element['type_name'])
        elif typedef_type == 'struct':
            types = []
            # Set self.within_function to None to ensure struct elements are added.
            within_function = self.within_function
            self.within_function = None
            alignment = 1
            offset = 0
            # Search all children
            for name, element_node in node.type.type.children():
                if self.handle_decl(element_node):
                    element = self.variables[-1]
                    self.variables = self.variables[:-1]
                    if element['exception'] != None:
                        self.within_function = within_function
                        raise element['exception']
                
                    # Align offset if required
                    align = self.type_alignment(element['type'])
                    offset = (offset + (align-1)) & ~(align-1)
                    
                    type_element = dict()
                    type_element['type_name']   = element['type']
                    type_element['var_name']    = element['name']
                    type_element['line_number'] = element['line_number']
                    type_element['line']        = element['line']
                    type_element['size']        = element['size']
                    type_element['array']       = element['array']
                    type_element['ptr']         = element['ptr']
                    type_element['exception']   = None
                    type_element['offset']      = offset
                    type_element['alignment']   = self.type_alignment(type_element['type_name'])
                    if type_element['alignment'] > alignment:
                        alignment = type_element['alignment']
                    offset += type_element['size']
                    types.append(type_element)
                    ignore_until_line_no = element['line_number']
                elif 'enumerators' in dir(element_node):
                    # This happens when enums are used e.g.  'typedef enum Life_e {DEAD,ALIVE} Life_t;'. 
                    # In this case, we want to add an enum type called 'Life_t' which is equivalent to 'Life_e'
                    # But this will not have been proocessed yet, so we will set a flag to indicate that when
                    # the enum is processed, the type should also be assigned.
                    self.enum_type_mix = typedef_name
            
            self.ignore_until_line_no = ignore_until_line_no+1
            typedef_data['size'] = offset
            # Increase the size to match the alignment of structs
            typedef_data['size'] = (typedef_data['size']+self.STRUCT_ALIGNMENT-1) & ~(self.STRUCT_ALIGNMENT-1)
            typedef_data['alignment'] = alignment
            if alignment < self.STRUCT_ALIGNMENT:
                typedef_data['alignment'] = self.STRUCT_ALIGNMENT
            typedef_data['types'] = types
            # Restore self.within_function
            self.within_function = within_function

        # Check that there is not an existing typedef with the same name
        if typedef_name in self.typedefs:
            # An existing typedef has the same name
            # We will now compare them to see if it is the same typedef used twice. Filenames and line numbers need to be ignored.
            a = typedef_data
            b = self.typedefs[typedef_name]
            a_str = json.dumps(a, sort_keys=True)
            b_str = json.dumps(b, sort_keys=True)
            # Delete  'line_number': <integer>
            # Delete  'filename': None
            # Delete  'filename': '<text>'
            p = re.compile('("filename": null|"filename": ".*"|line_number": [0123456789]*)')
            a_str = p.sub('', a_str)
            b_str = p.sub('', b_str)
            if a_str != b_str:
                raise Exception("Duplicate typedef name '%s' in %s:%d and %s:%d" % (typedef_name, a['filename'], a['line_number'],
                                                                                                  b['filename'], b['line_number']))
        else:
            self.typedefs[typedef_name] = typedef_data
        if self.debug_level >= 10:
            print('%s: typedef: %s' % (self.class_name, repr(typedef_data)))
            
        
    # Look at the node type and decide if it is one we are interested in
    def handle_node(self, node):
        # Try and print the line currently being processed
        if self.debug_level >= 20:
            try:
                if node.coord.line != 0:
                    if self.last_line != node.coord.line:
                        for i in range(self.last_line+1, node.coord.line+1):
                            print('%s: Line %d: %s' % (self.class_name, i, self.source_lines[i]))
                        if self.last_line < node.coord.line:
                            self.last_line = node.coord.line
            except:
                pass
        # If the node type one of the ones we are looking out for?
        if self.debug_level >= 100:
            print("%s: node.__class__.__name__=%s" % (self.class_name, node.__class__.__name__))
        if 'line' in dir(node.coord) and node.coord.line < self.ignore_until_line_no:
            pass
        else:
            if node.__class__.__name__ == 'FuncDef':
                self.handle_funcdef(node)
            if node.__class__.__name__ == 'Decl':
                self.handle_decl(node)
            if node.__class__.__name__ == 'Typedef':
                self.handle_typedef(node)
            if node.__class__.__name__ == 'Enum':
                self.handle_enum(node)
        
    # Iterate through all nodes passing a node to handle_node
    def parse_node(self, node):
        self.handle_node(node)
        self.level += 1
        if 'children' in dir(node):
            for child_name, child_node in node.children():
                self.parse_node(child_node)
            if self.level == 2:
                self.within_function = None
        self.level -= 1
    

    # This function will parse a string containing C code.
    # filename - File containing C source code
    def parse_file(self, filename):
        # Read file to a string
        with open(filename, 'rb') as f:
            c_source_code = f.read().decode('utf8')
        self.parse_string(c_source_code, filename=filename)
        

    # This function will parse a string containing C code.
    # str      - multi-line string of C source code
    # filename - Name of string - in case it came from a file. 
    def parse_string(self, str, filename = None):
        self.filename = filename
        self.last_line = 0
        self.ignore_until_line_no = 0
        # Convert str to an array of lines
        self.source_lines = []
        self.source_lines.append('') # Make line 0 and empty line
        i = -1
        while i != None:
            j = i+1
            i = str.find('\n', i+1)
            if i != -1:
                self.source_lines.append(str[j:i])
            else:
                i = None

        # Pass the original string through CParser but remove comments, preprocessor lines and attricutes 
        # because CParser does not handle them.
        # We import pycparser here so that the library is only required if CScrape is used to parse C code.
        import pycparser
        self.parser = pycparser.CParser()
        str = CScrape.remove_comments(str)
        str = CScrape.remove_preprocessor(str)
        str = CScrape.remove_attributes(str)
        self.ast = self.parser.parse(str)
        self.parse_node(self.ast)


    # Parse a GNU readelf output and put data into self.map_var_data & self.map_func_data

    # The gcc map file is inadequate for CScrape. Instead, the output from readelf utility is required.
    # E.g.
    #   arm-linux-gnueabi-ld -T test.ld startup.o cstartup.o myprogram.o -o results.elf
    #   arm-linux-gnueabi-objcopy -O binary results.elf results.bin
    #   readelf --all results.elf >results.data
    # Here, the file results.data would be passed to this function
    #
    # Note: Some variables/functions may be optimised away unless no optimisation (-O0) is selected as 
    # a compile flag or '__attribute__((used))' is added to fix the variable/function. E.g.
    #
    #    static int my_variable __attribute__((used)) = 99;
    #
    # The function returns a tuple of  (var_data, func_data) where each is an array of found
    # functions and variables. See add_map_var_data() and add_map_func_data()
    #
    # The expected format of the file is:
    #-------------------
    #     <ANY TEXT>
    #     Symbol table '.symtab' contains 47 entries:
    #        Num:    Value  Size Type    Bind   Vis      Ndx Name
    #          0: 00000000     0 NOTYPE  LOCAL  DEFAULT  UND 
    #          1: 00010000     0 SECTION LOCAL  DEFAULT    1 
    #         25: 00010130     0 NOTYPE  LOCAL  DEFAULT    2 $a
    #         26: 00010160     0 NOTYPE  LOCAL  DEFAULT    2 $d
    #         28: 00000000     0 FILE    LOCAL  DEFAULT  ABS test.c
    #         29: 00010170     0 NOTYPE  LOCAL  DEFAULT    2 $a
    #         30: 000102b4     0 NOTYPE  LOCAL  DEFAULT    5 $a
    #         34: 00010438     4 OBJECT  LOCAL  DEFAULT    6 my_static_function_var.4270
    #         35: 0001043c     4 OBJECT  LOCAL  DEFAULT    6 my_static_function_var.4266
    #         36: 00010170     4 FUNC    GLOBAL DEFAULT    2 main2
    #         37: 00010044    76 FUNC    GLOBAL DEFAULT    2 print_str
    #         38: 00010434     1 OBJECT  GLOBAL DEFAULT    6 my_char_var
    #         39: 00010440     4 OBJECT  GLOBAL DEFAULT    6 my_int_var
    #         40: 00011448     0 NOTYPE  GLOBAL DEFAULT    6 stack_top
    #         41: 00010130    64 FUNC    GLOBAL DEFAULT    2 c_entry
    #         42: 00010010    52 FUNC    GLOBAL DEFAULT    2 c_put
    #         43: 000102b4   384 FUNC    GLOBAL DEFAULT    5 main
    #
    #     <ANY TEXT>
    #-------------------
    # Note: Local elements after '28:' belong to 'test.c'
    # Note: Global objects contain items for all files. So the filename for global objects is unknown.
    # Note: Two functions in test.c have static variables called 'my_static_function_var'. It is
    #       impossible to tell them apart.
 
    def parse_readelf_output(self, filename):
        data_lines = []
        # Read file to a string
        with open(filename, 'rb') as f:
            map_data_str = f.read().decode('utf8')
        # Look for the line 'Symbol table '<string>' contains <number> entries:'
        
        sym_search = re.compile("^Symbol table '.*' contains [0-9]* entries:$", re.MULTILINE)
        match = sym_search.search(map_data_str)
        # Is there no symbol table in the file?
        if match == None:
            raise Exception("No symbol table found in %s" % filename)
        # Look at all the symbol tables
        while match != None:
            # Delete everything before the line and the line itself
            start = match.end()+1
            # Move end to after the 'Symbol table' line
            # Typically 'Num:    Value  Size Type    Bind   Vis      Ndx Name'
            while map_data_str[start] != '\n':
                start += 1
            start += 1
            # Find a blank line
            end = map_data_str.find('\n\n', start)
            if end == -1:
                end = len(map_data_str)
            data_lines.extend(map_data_str[start:end].split('\n'))
            # Is there another symbol table?
            match = sym_search.search(map_data_str, end)
        
        # data_lines is an array of string of the format
        #    '    33: 00010010    52 FUNC    GLOBAL DEFAULT    2 c_put'
        file      = None
        for line in data_lines:
            parts=line.split()
            # [0] Symbol ID - ignore
            # [1] Symbol address (hex)
            # [2] Symbol size (decimal)
            # [3] Symbol type (string)  'FILE', 'FUNC', 'OBJECT'
            # [4] Symbol scope 'LOCAL', 'GLOBAL'
            # [5] 'Vis' ? - Ignore
            # [6] 'Ndx' ? - Ignore
            # [7] Symbol name. Note: Static function variables may have .<number> appended.

            # Initialise an empty object
            data = dict()
            data['name'] = None
            data['addr'] = None
            data['size'] = None
            data['file'] = None
            if parts[3] == 'FILE':
                file = parts[7]
            if parts[3] == 'FUNC':
                data['name'] = parts[7]
                data['addr'] = int(parts[1], base=16)
                data['size'] = int(parts[2], base=10)
                data['func'] = None # Can't figure out how to associate a static function variable to a function from map file data.
                if parts[4] == 'LOCAL':
                    data['file'] = file
                self.map_func_data.append(data)
            if parts[3] == 'OBJECT':
                # If the name is NAME.1234, remove the .1234
                if parts[7].find('.') != -1:
                    parts[7] = parts[7][:parts[7].find('.')]
                data['name'] = parts[7]
                data['addr'] = int(parts[1], base=16)
                data['size'] = int(parts[2], base=10)
                data['func'] = None  # We can not work out the function from this data
                if parts[4] == 'LOCAL':
                    data['file'] = file
                self.map_var_data.append(data)
                

    # This function parses the given map (or equivalent) file and adds the data to the existing C Scrape data.
    # It tries all of the map file parsers it knows of until it finds one that does not throw an exception.
    #
    def parse_output(self, filename):
        data = None

        # Try all the map file parsers
        try:
            if data == None:
                data = self.parse_readelf_output(filename)
        except:
            pass
        ####

        if data == None:
            raise Exception("Could not extract data from %s" % filename)

    # This function returns all of the class data as a json string. The purpose of this function is to allow
    # the class to parse a C project, store the data to a file. The file can then be released with the project 
    # executable (flash image) and used without having to release the project source.
    #
    # NOTE: The source lines defining functions and variables are included in the data (including comments)
    #
    def json_dump(self):
        data = dict()
        data['functions']     = self.functions
        data['typedefs']      = self.typedefs
        data['variables']     = self.variables
        data['enums']         = self.enums
        data['types']         = self.types
        data['map_var_data']  = self.map_var_data
        data['map_func_data'] = self.map_func_data
        return json.dumps(data)

    # This function takes a string returned by json_out() and re-creates the data
    #
    def json_load(self, str):
        data = json.loads(str)
        self.functions        = data['functions']
        self.typedefs         = data['typedefs']
        self.variables        = data['variables']
        self.enums            = data['enums']
        self.types            = data['types']
        self.map_var_data     = data['map_var_data']
        self.map_func_data    = data['map_func_data']

    # Return the basename (including extension) of the given filename. If the parameter is None, return None
    @staticmethod
    def simple_filename(filename):
        if filename == None:
            return None
        return os.path.basename(filename)

    # Return a copy of the C source with comments removed
    # Comment characters are replaced with a space, newlines are preserved.
    @staticmethod
    def remove_comments(str):
        # Create a copy of the string with comments removed
        str_no_comments = ''
        str += ' ' # Add a character because only previous_c is added.
        previous_c = ''
        state_normal              = 0
        state_single_line_comment = 1
        state_multi_line_comment  = 2
        state_string_quote        = 3
        state_string              = 4
        state_character           = 5
        state = state_normal
        for c in str:
            str2 = previous_c + c
            if state == state_normal:
                if str2 == '//':
                    state = state_single_line_comment
                    previous_c = ' '
                elif str2 == '/*':
                    state = state_multi_line_comment
                    previous_c = ' '
                elif c == '"':
                    state = state_string
                elif c == "'":
                    state = state_character
            elif state == state_single_line_comment:
                if c == '\n':
                    state = state_normal
                    previous_c = ' '
            elif state == state_multi_line_comment:
                if str2 == '*/':
                    state = state_normal
                    previous_c = ' '
                    c = ' '
            elif state == state_string:
                if c == '\\':
                    state = state_string_quote
                elif c == '"':
                    state = state_normal
            elif state == state_character:
                if c == '\\':
                    state = state_string_quote
                elif c == "'":
                    state = state_normal
            elif state == state_string_quote:
                state = state_string

            if state == state_single_line_comment:  # if not 'elif'
                str_no_comments += ' '
            elif state == state_multi_line_comment:
                if c != '\n':
                    str_no_comments += ' '
                else:
                    str_no_comments += '\n'
            else:
                str_no_comments += previous_c
            previous_c = c
        return str_no_comments


    # Return a copy of the C source with pre-processor directives removed.
    # Characters are replaced with a space, newlines are preserved.
    # NOTE: This function should be used AFTER comments have been removed.
    @staticmethod
    def remove_preprocessor(str):
        # Create a copy of the string with comments removed
        str_no_directives = ''
        state_normal                   = 0
        state_whitespace_after_newline = 1
        state_directive_found          = 2
        state = state_whitespace_after_newline
        for c in str:
            if state == state_whitespace_after_newline:
                if c == ' ' or c == '\t':
                    str_no_directives += c
                elif c == '#':
                    str_no_directives += ' '
                    state = state_directive_found
                elif c == '\n':
                    str_no_directives += c
                else:
                    str_no_directives += c
                    state = state_normal
            elif state == state_normal:
                if c == '\n':
                    str_no_directives += '\n'
                    state = state_whitespace_after_newline
                else:
                    str_no_directives += c
            elif state == state_directive_found:
                if c == '\n':
                    str_no_directives += '\n'
                    state = state_whitespace_after_newline
                else:
                    str_no_directives += ' '
        return str_no_directives

    # Return a copy of the C source with attributes removed.
    # Characters are replaced with a space, newlines are preserved.
    # e.g.    hello__attribute__ ((used))END
    #         hello                      END
    # NOTE: The first bracket is matched to the last bracket.
    # NOTE: This function should be used AFTER comments have been removed.
    @staticmethod
    def remove_attributes(str):
        result = ''
        start = 0
        while True:
            p = str.find('__attribute__', start)
            # Is there a __attribute__ in the source?
            if p != -1:
                try:
                    # Yes there is - we need to eliminate it
                    q = p + 13 # 13 is the length of '__attribute__'
                    while str[q] == ' ':
                        q += 1
                    # Assume we have hit a (
                    count = 1
                    q += 1
                    # Find matching )
                    while count > 0:
                        if str[q] == '(': count += 1
                        if str[q] == ')': count -= 1
                        q += 1
                    # Replace __attribute__(...) with spaces
                    result += str[start:p] + ((q - p) * ' ')
                    start = q
                except:
                    return result + str[start:]
            else:
                # No __attribute__ so return the string so far
                return result + str[start:]


    # This function returns the value of the specifed enum.
    # If the same query had been made before, the cache value is returned.
    # The search can be narrowed down by specifying the file and/or function and/or enum typename for the enum.
    # If no enum matches, an exception is generated.
    # If more than one enum matches, an exception is generated.
    def enum(self, name, filename='*', function='*', typename='*'):
        query = 'enum:' + filename + ':' + function + ':' + typename + ':' + name
        # Have we asked for this before?
        try:
            return self.previous_queries[query] 
        except:
            pass        
        
        # Search all enums
        match = None
        for index in range(len(self.enums)):
            matched = True
            if matched and function != '*' and function != self.enums[index]['function']:
                matched = False
            if matched and filename != '*' and filename != self.simple_filename(self.enums[index]['filename']):
                matched = False
            if matched and typename != '*' and typename != self.enums[index]['name']:
                matched = False
            if matched and not name in self.enums[index]['values']:
                matched = False
            if matched and match != None:
                raise Exception("Duplicate enum '%s'  %s:%d and %s:%d" % (query, 
                           self.enums[index]['filename'], self.enums[index]['line_number'],  
                           self.enums[match]['filename'], self.enums[match]['line_number']))
            # If we have a match, remember the index
            if matched:
                match = index
        if match == None:
            raise Exception("Missing enum '%s'" % query)
        
        value = self.enums[match]['values'][name]['value']
        self.previous_queries[query] = value
        return value


    # This function returns a dict() of all the enums matching the query. The key for the
    # dict is the enum name. Each element is itself a dict with the following values
    #       'value'      - Value of enum
    #       'line'       - Source line the value was defined on
    #       'line_number'- Line number for the value
    # Usage:
    #   cards_list = obj.enums(typename='Cards_t')
    #   for key in cards_list:
    #      print("Card %s value is %d" % (key, cards_list[key][value]))
    #   
    def enum_type(self, filename='*', function='*', typename='*'):
        query = 'enum_type:' + filename + ':' + function + ':' + typename
        # Have we asked for this before?
        try:
            return self.previous_queries[query] 
        except:
            pass        
        
        # Search all enums
        match = None
        for index in range(len(self.enums)):
            matched = True
            if matched and function != '*' and function != self.enums[index]['function']:
                matched = False
            if matched and filename != '*' and filename != self.simple_filename(self.enums[index]['filename']):
                matched = False
            if matched and typename != '*' and typename != self.enums[index]['name']:
                matched = False
            if matched and match != None:
                raise Exception("Duplicate enum '%s'  %s:%d and %s:%d" % (query, 
                           self.enums[index]['filename'], self.enums[index]['line_number'],  
                           self.enums[match]['filename'], self.enums[match]['line_number']))
            if matched:
                match = index
        if match == None:
            raise Exception("Missing enum '%s'" % query)
                    
        value = self.enums[match]['values']
        self.previous_queries[query] = value
        return value


    # This function will return details of the specifed variable as a dict(). The dict has the
    # following elements
    #   'name'          - Name of variable
    #   'filename'      - Filename the variable was declared in
    #   'line_number'   - Line number the variable was declared on
    #   'line'          - C Source line containing the declaration
    #   'type'          - Name of type e.g. 'int'
    #   'array'         - Array of sizes. e.g. 'int x[5][6];' would be [5, 6]
    #   'ptr'           - Number of ptr specifiers. E.g. 'int**' would be 2.
    #   'size'          - Size of the variable in bits.
    #   'function'      - The function the variable is defined in (or None if defined in module scope).
    #   'exception'     - Either None or an expection object explaining the problem with the declaration.
    #   'addr'          - Address of the variable according to the map file (or None if data is not present)
    def var(self, name, filename='*', function='*', typename='*'):
        query = 'var:' + filename + ':' + function + ':' + typename + ':' + name
        # Have we asked for this before?
        try:
            return self.previous_queries[query] 
        except:
            pass        
        
        # Search all variables
        match = None
        for index in range(len(self.variables)):
            matched = True
            if matched and name     != '*' and name     != self.variables[index]['name']:
                matched = False
            if matched and function != '*' and function != self.variables[index]['function']:
                matched = False
            if matched and filename != '*' and filename != self.simple_filename(self.variables[index]['filename']):
                matched = False
            if matched and typename != '*' and typename != self.variables[index]['type']:
                matched = False
            if matched and match != None:
                raise Exception("Duplicate variables '%s'  %s:%d and %s:%d" % (query, 
                           self.variables[index]['filename'], self.variables[index]['line_number'],  
                           self.variables[match]['filename'], self.variables[match]['line_number']))
            if matched:
                match = index
        if match == None:
            raise Exception("Missing variable '%s'" % query)
        value = self.variables[match]

        # Incorporate the address of the variable from the map data
        match = None
        for index in range(len(self.map_var_data)):
            matched = True
            if matched and value['name'] != self.map_var_data[index]['name']:
                matched = False
            if matched and self.map_var_data[index]['func'] != None and value['function'] != self.map_var_data[index]['func']:
                matched = False
            if matched and self.simple_filename(self.map_var_data[index]['file']) != None and self.simple_filename(value['filename']) != self.simple_filename(self.map_var_data[index]['file']):
                matched = False
            if matched and match != None:
                raise Exception("Duplicate variable in map '%s'  %s:%d and %s:%d" % (query, 
                           value['filename'], value['line_number'],  
                           value['filename'], value['line_number']))
            if matched:
                match = index
        if match != None:
            value['addr'] = self.map_var_data[match]['addr']
        else:
            value['addr'] = None

                    
        self.previous_queries[query] = value
        return value


