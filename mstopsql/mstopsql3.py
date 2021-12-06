#! /usr/bin/python
#
# MSTOPSQL.py Copyright (2008) Gwyneth Morrison
# Version 3.9.4 - April 09
# Convert mssql to postgres
#

import  os, re, sys, string


# Symbols for identified source issues

MSNG  = 10              # Missing token
UNSP  = 20              # Unsupported token
SERR  = 30              # Syntax error
INFO  = 40              # Information
CMPX  = 45              # Complexity

MSGLIST = {}

MSGLIST [10] = 'MSNG'
MSGLIST [20] = 'UNSP'
MSGLIST [30] = 'SERR'
MSGLIST [40] = 'INFO'
MSGLIST [45] = 'CMPX'

TRAC  = 50              # Trace
TOTL  = 51              # Total
FREQ  = 52              # Frequency
WARN  = 53              # Frequency

LDMT  = 60	        # Load stack empty
UNRC  = 62	        # Unrecognized Token

trap_stack = []         # Trap stack 
level_stack = []        # Level stack
save_tokens = []        # Saved tokens
into_tokens = []        # Saved into tokens

debug = 0               # Debug switch
trace = 0               # Trace switch

ansi_warnings = 0       # ansi_warnings 
current_limit = []      # Current limit 

current_level = 0       # Current level
current_altstr = ""     # Current altstr
skip_errors = 0         # Skip errors
total_errors = 0        # Total errors
frame_counter = 0       # frame counter
in_subselect = 0	# in subselct

statement_table = {}    # Statement table
state_errors = {}       # State error table
proc_table = {}         # Proc table
proc_return = {}        # Return table
trig_table = {}         # Trig table
tab_table = {}          # Table table
col_table = {}          # Column table
intret_table = {}       # Int Return table
warning_table = {}      # Warning table
warning_line = {}       # Warning line
procref_table = {}      # Procref table

trig_proc = ""          # Trigger procedure
trig_tabname = ""       # Trigger name
trig_when = ""          # Trigger when
trig_event = ""         # Trigger operation

current_statement = ""  # Current statement
current_column = ""     # Current column
current_table = ""      # Current table
last_token = None       # Last printed token 
join_token = None       # Last joined token 
copy_token = ''         # Saved copy token
copy_count = 0          # Token copy count
current_line = 1        # Current line number
current_sourceline = "" # Current source line 

error_log = None        # Error log file
output_file = None      # Secondary file

# prcedure variables
current_proc = ""       # Current procedure
defined_proc = ""       # Current defined proc
save_procname = ""      # Save Procname
return_type = None      # Return type
return_temp = None      # Return temp table
return_default = "void" # Proc return type

# begin variables
current_begin = None	# current begin object

# parameter variables
parmlist = []		# Parameter list
current_parm = None     # Current paramater 

#
# Parameter list class
#
class parmclass :
  def __init__(self, pname) :
    self.pname = pname
    self.ptype = None
    self.output = None 
    self.default = None
    self.size = None
  def setType(self, ptype) :
    self.ptype = ptype
  def setOutput(self) :
    self.output = "out"
  def setDefault(self, default) :
    self.default = default
  def setSize(self, size) :
    if size == 'MAX' : 
      printMessage(size,"SETSIZE",UNSP)
      self.size = 0
    else :
      self.size = size
  def printParm(self) :
    if  self.output :
      print("out",self.pname,self.ptype, end=' ')
    else :
      print("_p%s %s" % (self.pname,self.ptype), end=' ')
    if self.size : print("(",self.size,")", end=' ')
  def printDecl(self) :
    if  not self.output :
      print("declare",self.pname,self.ptype, end=' ')
      if self.size : print("(",self.size,")", end=' ')
      print("= _p%s" % self.pname,";")
  def listParm(self) :
    if self.ptype == None :
          self.ptype = "ERROR in TYPE"
    if  self.output :
      outlist = [ "OUT " ] + [ self.ptype ]
    else :
      outlist = [ self.ptype ]
    if self.size : 
      outlist = outlist +  [ "(" ] + [ self.size ] + [ ")" ] 
    return " ".join(outlist)
#
#  Print a warning message
#
def printMessage(token,message,rc) :
  global current_statement
  global error_log
  global warning_table
  global trace
  if rc == TRAC and not trace : return
  if not token : token = "None"	  
  reason = ' MESSAGE '
  if rc == SERR : reason = ' SYNTAX      '
  if rc == MSNG : reason = ' MISSING     '
  if rc == CMPX : reason = ' COMPLEXITY  '
  if rc == UNSP : reason = ' UNSUPPORTED ' 
  if rc == INFO : reason = ' INFORMATION '
  if rc == TRAC : reason = ' TRACE       '
  if rc == TOTL : reason = ' TOTAL       '
  if rc == FREQ : reason = ' FREQUENCY   '
  if rc == WARN : reason = ' WARNSUMMARY '
  if rc == TRAC :
    print("TRACE   {0:12s}".format(reason), end=' ' ,file=error_log)
  else :
    if rc == TOTL or rc == FREQ :
      print("REPORT  {0:12s}".format(reason), end=' ' ,file=error_log)
    else :
      print("WARNING {0:12s}".format(reason), end=' ' ,file=error_log)
      if rc != WARN :
        key = "{0}-{1}-{2}".format(reason,current_level,token)
        warning_table[ key ] = current_line
        warning_line["{0}".format(current_line) ] = current_sourceline
  print("state: {0:6d}".format(current_level), end=' ', file=error_log)
  print("line: {0:6d}".format(current_line), end=' ', file=error_log)
  print("token: {0:40s}".format(token), end=' ' ,file=error_log)
  print("stmt: {0:10s}".format(current_statement), end=' ', file=error_log)
  print(message, file=error_log)
#
#  Print an error message
#
def printError(token,message,state,rc) :
  global current_statement
  global error_log
  global state_errors
  if not token : token = "None"	  
  reason = ' ERROR       '
  if rc == LDMT : reason = ' LOADMT      '
  if rc == UNRC : reason = ' UNREC       '
  print("ERROR   {0:12s}".format(reason), end=' ' ,file=error_log)
  print("state: {0:6d}".format(state), end=' ', file=error_log)
  print("line: {0:6d}".format(current_line), end=' ', file=error_log)
  print("token: {0:40s}".format(token), end=' ' ,file=error_log)
  print("stmt: {0:10s}".format(current_statement), end=' ', file=error_log)
  print(message,file=error_log)
  key = current_statement + ':' + token
  if key in state_errors :
    state_errors[key] = state_errors[key] + 1
  else :
    state_errors[key] = 1
#
#
#  Print the token
#  Messy business with double operators
#
def printToken(token) :
  global last_token
  global join_token
# print join token
  if join_token :
    #print("<",last_token,">")
    if last_token == ',' :
      print(",",join_token,end=' ')
      last_token = None
    else :
      print(join_token,end=' ')
    join_token = None
# Remove ,) errors
  if last_token :
    if last_token == ',' :
      if token == ')' :
        print(token)
      else : 
        print(last_token,token, end=' ')
      last_token = None
      return
# Remove ; ; errors
#  if last_token :
#    if last_token == ';' :
#      if token == ';' :
#        print(token)	
#      else : 
#        print(last_token,token, end=' ')
#      last_token = None 
#      return
# Fix <> <= >= 
  if last_token :
    if last_token == '<' and token == '>' :
      print("!=", end=' ')
    else :
      print(last_token+token, end=' ')
    last_token = None
    return
# Save last token
#  if token == '<' or token == '>' or token == ',' or token == ';' :
  if token == '<' or token == '>' or token == ',' :
    last_token = token
  if last_token == None : print(token, end=' ')
#
#  Print the stack if debug
#
def printStack(type) :
  global debug
  global current_level
  global level_stack
  if debug :
    print("DEBUG    CALLSTACK ",type,":", end=' ', file=error_log) 
    for l in level_stack :
      print(l, end=' ', file=error_log)
    print(" ~ ",current_level, file=error_log)
#=====================================================
# State token processing routines
#=====================================================
#
#  Return to last state  
#  Preserve the token
#
def skip(token,move,alter) :
  printMessage(token,"skip",TRAC)
  dortn(token,move,alter)
  printStack("skip")
  if current_level == 70 :
    prtlim(token,70,1)
  traptest(token,move,alter)
  return 2
#
#  Return to last state  
#  Drop token if "OUT"
#  Alter = 1 on keyword
#
def prmtest(token,move,alter) :
  global current_level
  global copy_count
  printMessage(token,"prmtest",TRAC)
  if alter == 1 :
    if return_default == "int" :
      printToken("0 /* inserted */")
    skip(token,move,alter)
    return 2
  if copy_count > 0 :
    dortn(token,move,alter)
    printStack("prmtest")
    traptest(token,move,alter)
    return 0
  else :
    printToken(token)
    current_level = move
    return 0
#
#  Jump to new state
#  set subselect flag to alter
#  keep the token
#
def subsel(token,move,alter) :
  global current_level
  global in_subselect
  printMessage(token,"subsel",TRAC)
  current_level = move
  in_subselect = alter 
  return 2
#
#  Jump to new state
#  Preserve the token
#
def jump(token,move,alter) :
  global current_level
  printMessage(token,"jump",TRAC)
  current_level = move
  return 2
#
#  Call a new state  
#  Preserve the token
#  Trap the return
#
def trap(token,move,alter) :
  global debug
  global trap_stack
  printMessage(token,"trap",TRAC)
  docall(token,move,alter,"trap")
  trap_stack = trap_stack + [ len(level_stack) ]
  if debug :
    print("DEBUG    TRAPSTACK ","trap",":", end=' ', file=error_log) 
    for l in trap_stack :
      print(l, end=' ', file=error_log)
    print(file=error_log)
  return 2
#
#  Dump the token
#
def dump(token,move,alter) :
  global current_level
  global output_file
  printMessage('dump',"dump",TRAC)
  printMessage('dump',"EXEC procedure dumped",UNSP)
  current_level = move
  if output_file == None :
    output_file = open('output.sql','w')
  output_file.write(token[1:-1])
  output_file.write("go\n")
  return 0
#
#  Drop the token
#
def drop(token,move,alter) :
  global current_level
  printMessage(token,"drop",TRAC)
  current_level = move
  if alter > 0 : printMessage(token,"dropped",alter)
  return 0
#
#  Set output parameter
#  Drop current token
#
def parmout(token,move,alter) :
  global current_level
  global current_parm
  global copy_token
  global copy_count
  printMessage(token,"parmout",TRAC)
  current_parm.setOutput()
  copy_count = copy_count + 1
  copy_token =  current_parm.ptype
  current_level = move
  return 0
#
#  Create paramater
#  Drop current token
#
def parmnew(token,move,alter) :
  global current_level
  global current_parm
  printMessage(token,"parmnew",TRAC)
  current_parm=parmclass(token)
  current_level = move
  return 0
#
#  Set parameter type
#  Drop current token
#
def prmtype(token,move,alter) :
  global current_level
  global current_parm
  printMessage(token,"prmtype",TRAC)
  current_parm.setType(token)
  current_level = move
  return 0
#
#  Log return type
#  Drop current token
#
def procret(token,move,alter) :
  global current_level
  global return_type
  global proc_return
  printMessage(token,"procret",TRAC)
  return_type = token
  proc_return[current_proc] = return_type
  current_level = move
#
#  Set parameter size
#  Drop current token
#
def prmsize(token,move,alter) :
  global current_level
  global current_parm
  printMessage(token,"prmsize",TRAC)
  current_parm.setSize(token)
  current_level = move
#
#  Set the stack frame 
#  Keep the token
#
def frame(token,move,alter) :
  global current_level
  global frame_counter
  global save_tokens
  printMessage(token,"frame",TRAC)
  save_tokens = save_tokens + [ "<stack_frame>" ]
  frame_counter = frame_counter + 1
  if frame_counter > 2 :
    printMessage(token,"frame",CMPX)
  current_level = move
  return 2
#
#  Save the token 
#
def save(token,move,alter) :
  global current_level
  global current_parm
  global save_tokens
  printMessage(token,"save",TRAC)
  save_tokens = save_tokens + [ token ]
  current_level = move
  return 0
#
#  Push alternate token
#  Only used for paramaters
#
def pushalt(token,move,alter) :
  global current_level
  global current_parm
  global current_altstr
  global save_tokens
  printMessage(token,"pushalt",TRAC)
  save_tokens = save_tokens + [ current_altstr ]
  if alter > 0 : printMessage(token,"replaced",alter) 
  current_level = move
  return 0
#
#  Load first saved token 
#  Preserve current token
#
def load(token,move,alter) :
  global current_level
  global save_tokens
  if len(save_tokens) > 0 :
    printMessage(save_tokens[0],"load",TRAC)
    token = save_tokens[0]
    printToken(token)
    del save_tokens[0]
  else :
    printError(None,"stack",current_level,LDMT)
  current_level = move
  return 2
#
#  Load saved temp table name
#  Preserve current token
#
def loadtemp(token,move,alter) :
  global current_level
  global return_temp
  printMessage(return_temp,"loadtemp",TRAC)
  printToken(return_temp)
  current_level = move
  return 2
#
#  Pop all saved tokens 
#  Stop at stack_frame
#  Preserve current token
#
def popall(token,move,alter) :
  global current_level
  global save_tokens
  global frame_counter
  new_stack = []
  printMessage(token,"popall",TRAC)
  while len(save_tokens) > 0 :
    loadlen = len(save_tokens) - 1
    stack_token = save_tokens[loadlen]
    #printMessage(stack_token,"popall-t",TRAC)
    if stack_token != "<stack_frame>" :
      new_stack = new_stack + [ stack_token ]
    del save_tokens[loadlen]
    if stack_token == "<stack_frame>" : 
      frame_counter = frame_counter - 1
      break
  while len(new_stack) > 0 :
    loadlen = len(new_stack) - 1
    printToken(new_stack[loadlen])
    del new_stack[loadlen]
  current_level = move
  return 2
#
#  Clear the token stack 
#  Preserve current token
#
def clear(token,move,alter) :
  global current_level
  global save_tokens
  printMessage(token,"clear",TRAC)
  save_tokens = []
  current_level = move
  return 2
#
#  Save into token 
#
def savinto(token,move,alter) :
  global current_level
  global into_tokens
  printMessage(token,"savinto",TRAC)
  into_tokens = into_tokens + [ token ]
  current_level = move
  return 0
#
#  Load first saved into token 
#  Preserve current token
#
def lodinto(token,move,alter) :
  global current_level
  global into_tokens
  if len(into_tokens) > 0 :
    printMessage(into_tokens[0],"lodinto",TRAC)
    token = into_tokens[0]
    printToken(token)
    del into_tokens[0]
  else :
    printError(None,"stack",current_level,LDMT)
  current_level = move
  return 2
#
#  Print an into list
#  Preserve the token
#
def prtinto(token,move,alter) :
  global current_level
  global into_tokens
  printMessage(token,"prtinto",TRAC)
  prcomma = ''
  if len(into_tokens) > 0 :
    printToken("into")
    for stok in into_tokens :
      printToken(prcomma)
      printToken(stok)
      prcomma = ','
    into_tokens = []
  current_level = move
  return 2
#
#  Save/print the limit 
#  Keep current token
#
def prtlim(token,move,alter) :
  global current_level
  global current_limit
  printMessage(token,"prtlim",TRAC)
  current_level = move
  # Trying to set/reset the limit - give message
  if alter == 0 :
    if len(current_limit) > 0 : printMessage("limit","reset",INFO)
    current_limit = current_limit + [ token ]
    return 0
  # Normal limit print
  if alter == 1 :
    if len(current_limit) > 0 :
      last = len(current_limit) -1
      printToken("limit")
      printToken(current_limit[last])
      del current_limit[last]
      #printToken(";")
    return 2
  # Subselect limit print
  if alter == 2 :
    if len(current_limit) > 0 :
      last = len(current_limit) -1
      printToken("limit")
      printToken(current_limit[last])
      del current_limit[last]
    rtnem(token,move,alter)
    return 0
  # Keyword limit print
  if alter == 3 :
    if len(current_limit) > 0 :
      last = len(current_limit) -1
      printToken("limit")
      printToken(current_limit[last])
      del current_limit[last]
    skip(token,move,alter)
    return 2
#
#  Emit the token unchanged
#
def emit(token,move,alter) :
  global current_level
  printMessage(token,"emit",TRAC)
  printToken(token)
  if alter > 0 : printMessage(token,"MESSAGE",alter)
  current_level = move
  return 0
#
#  Emit the token unchanged
#  Record a proc reference
#
def procref(token,move,alter) :
  global current_level
  global defined_proc
  global save_procname
  global procref_table
  printMessage(token,"procref",TRAC)
  current_level = move
  if alter == 0 :
    printToken(token)
    save_procname = token.lower()
    return 0
  else :
    printToken("(")	# always a bracket
    procref_table[save_procname] = defined_proc
    return 2
#
#  Emit the token with _ removed 
#  Error if symbol used for column
#
def colsym(token,move,alter) :
  global current_level
  printMessage(token,"colsym",UNSP)
  printToken(re.sub("_","",token))
  current_level = move
  return 0
#
#  Set ansi_warnings
#
def prtansi(token,move,alter) :
  global current_level
  global ansi_warnings
  printMessage(token,"prtansi",TRAC)
  current_level = move
  printToken("set escape_string_warning")
  if alter == 0 :
    printToken("= 1")
    ansi_warnings = 1
  else :
    printToken("= 0")
    ansi_warnings = 0
  return 0
#
#  Emit the logged procname 
#  Keep the token
#
def procget(token,move,alter) :
  global current_level
  printMessage(token,"procget",TRAC)
  printToken(current_proc)
  current_level = move
  return 2
#
#  Emit the trigger header
#
def trighed(token,move,alter) :
  global current_proc
  global current_level
  global trig_when
  printMessage(token,"trighed",TRAC)
  printToken(current_proc)
  printToken("() returns")
  if trig_when == "instead" :
      printToken("int") 
  else:
   printToken("trigger") 
  printToken("as $$ begin")     
  current_level = move
  return 2
#
#  Emit the logged colname 
#
def colget(token,move,alter) :
  global current_level
  printMessage(token,"colget",TRAC)
  printToken(current_column)
  current_level = move
  return 2
#
#  Emit the token unchanged
#  Log the procedure name
#
def procset(token,move,alter) :
  global current_level
  global current_proc
  printMessage(token,"procset",TRAC)
  printToken(token)
  current_level = move
  current_proc = token
  return 0
#
#  Emit the token unchanged
#  Log the column name
#
def colset(token,move,alter) :
  global current_level
  global current_column
  printMessage(token,"colset",TRAC)
  printToken(token)
  current_level = move
  current_column = token
  return 0
#
#  Emit the token unchanged
#  Test for existing table name
#
def tabtest(token,move,alter) :
  global current_level
  global tab_table
  printMessage(token,"tabtest",TRAC)
  printToken(token)
  current_level = move
  if token.lower() in tab_table :
    if tab_table[token.lower()] == "CREATE" : return 0
    if tab_table[token.lower()] == "DECLARE" : return 0
  printMessage(token,"undefined table",UNSP)
  return 0
#
#  Emit the token unchanged
#  Log the table name
#
def tabdcl(token,move,alter) :
  global current_level
  global tab_table
  printMessage(token,"tabdcl",TRAC)
  if len(save_tokens) > 0 :
    tab_table[save_tokens[0].lower()] = "DECLARE"
  load(token,move,alter)
  return 2
#
#  Emit the token unchanged
#  Log the table name
#
def tabname(token,move,alter) :
  global current_level
  global tab_table
  global current_table
  printMessage(token,"tabname",TRAC)
  printToken(token)
  current_level = move
  current_table = token
  tab_table[token.lower()] = "CREATE"
  return 0
#
#  Emit the token unchanged
#  Log the column name
#
def tabcol(token,move,alter) :
  global current_level
  global col_table
  global current_table
  printMessage(token,"tabcol",TRAC)
  printToken(token)
  current_level = move
  col_table[current_table.lower() +  "." +  token.lower()] = "CREATE"
  return 0
#
#  Emit the token unchanged
#  Log the table drop
#
def tabdrop(token,move,alter) :
  global current_level
  global tab_table
  printMessage(token,"tabdrop",TRAC)
  printToken(token)
  current_level = move
  tab_table[token.lower()] = "DROP"
  return 0
#
#  Log trigger parameters
#
def triglog(token,move,alter) :
  global current_level
  global current_proc
  global trig_tabname
  global trig_proc
  global trig_table
  global trig_when
  global trig_event
  printMessage(token,"triglog",TRAC)
  if alter == 0 :
    current_proc = token
  if alter == 1 :
    trig_table[current_proc.lower()] = token
    trig_tabname = token
    trig_proc = current_proc
  if alter == 2 :
    trig_when = token.lower()
    if trig_when == "for" :
      trig_when = "before"
  if alter == 3 :
    trig_event = token
  current_level = move
  return 0
#
#  Print the trigger table entry
#
def trigprt(token,move,alter) :
  global current_level
  global current_proc
  global trig_table
  printMessage(token,"trigprt",TRAC)
  current_level = move
  if current_proc.lower() in trig_table :
    printToken(trig_table[current_proc.lower()])
  else :
    printToken("sysobjects")
    printMessage(current_proc,"trigger proc",MSNG)
  return 2
#
#  Print an as if not in subselect
#  Keep the token
#
def prtas(token,move,alter) :
  global current_level
  printMessage(token,"prtas",TRAC)
  if in_subselect : 
    printMessage(token,"INSUBSELECT",UNSP)
    return
  printToken("as")
  current_level = move
  return 2
#
#  Strip and Join token 
#
def join(token,move,alter) :
  global current_level
  global join_token
  printMessage(token,"join",TRAC)
  current_level = move
  if in_subselect : 
    printMessage(token,"INSUBSELECT",UNSP)
    return
  newtoken=re.sub(r'\'','"',token)
  if join_token :
    join_token = join_token + '_' + newtoken
  else :
    join_token = newtoken
  return 0
#
#  Lower and emit the token 
#
def lower(token,move,alter) :
  global current_level
  printMessage(token,"lower",TRAC)
  printToken(token.lower())
  current_level = move
  return 0
#
#  Escape quote emit the token 
#
def escape(token,move,alter) :
  global current_level
  printMessage(token,"escape",TRAC)
  if token [ 0 ] == 'b' and token [ 1 ] == '\'' :
    printToken(token)
    return 0
  char_range = list(range(len(token)))
  newtoken = ""
  for i in char_range :
    newtoken = newtoken + token [ i ]  
    if token [ i ] == '\'' and i > 0 and i < len(token) - 1 :
      newtoken = newtoken + '\''
  printToken(newtoken)
  current_level = move
  return 0

####### start of class begin
class begin :
#
#  Constructor
#
  def __init__(self) :
    printMessage("begin","begin.init",TRAC)
    self.begin_stack = []	# Begin stack
    self.begin_count = 0        # Generated begin count
    self.in_declare = 0         # In declare begin
#
#  Reset begin block values
#
  def reset(self,token,move,alter) :
    printMessage(token,"begrst",TRAC)
    self.end(token,move,alter)	# End begin blocks
    self.begin_count = 0
    self.in_declare = 0
    self.begin_stack =[] 
#
#  Test for declare
#  Insert begin if required
#
  def test(self) :
    if self.in_declare :
      printToken("begin")
      self.in_declare = 0 
      self.begin_count = self.begin_count + 1
      printMessage("begin","inserted",TRAC)
#
#  Start a source begin block
#  Stack the current begin count
#  Preserve token and call
#
  def start(self,token,move,alter) :
    printMessage(token,"begsta",TRAC)
    self.begin_stack = self.begin_stack + [ self.begin_count ]
    self.begin_count = 0
    docall(token,move,alter,"begin.start")
    return 2
#
#  Create begin block for declare table
#  Preserve the current token
#
  def table(self,token,move,alter) :
    global current_level
    printMessage(token,"begtbl",TRAC)
    self.in_declare = 0
    self.begin_count = self.begin_count + 1
    current_level = move
    return 2
#
#  Create begin block for declare 
#
  def declare(self,token,move,alter) :
    printMessage(token,"begdcl",TRAC)
    printToken(token)
    docall(token,move,alter,"begin.declare")
    self.in_declare = 1
    return 0
#
#  Preserve token and move
#  Dump ends to close begins
#
  def end(self,token,move,alter) :
    global current_level
    printMessage(token,"begend",TRAC)
    current_level = move
    printToken(";")
    for i in range(self.begin_count) :
      printToken("end;")
      printMessage("end inserted","begend",TRAC)
    last = len(self.begin_stack) - 1
    if last >= 0:
      self.begin_count = self.begin_stack[last]
      del self.begin_stack[last]
    else : 
      self.begin_count = 0
    return 2

def begend(token,move,alter) : return(current_begin.end(token,move,alter))
def begtbl(token,move,alter) : return(current_begin.table(token,move,alter))
def begsta(token,move,alter) : return(current_begin.start(token,move,alter))
def begdcl(token,move,alter) : return(current_begin.declare(token,move,alter))

####### end of class begin
#
#  Add a paramater to the list
#  Preserve the current token
#
def parmadd(token,move,alter) :
  global current_level
  global current_parm
  global parmlist
  printMessage(token,"parmadd",TRAC)
  parmlist = parmlist + [ current_parm ]
  current_parm = None   
  current_level = move
  return 2
#
#  Insert parameter list
#  Preserve the current token
#
def prmisrt(token,move,alter) :
  global intret_table
  global current_level
  global copy_count
  global current_parm
  global return_default
  global current_proc
  global defined_proc
  global return_type
  global parmlist
  printMessage(token,"prmisrt",TRAC)
  if current_parm :
    parmadd(token,move,alter)
  print("(")
  comma = ""
  parm_list = [ "(" ]
  for parm in parmlist :
    print(comma)
    parm.printParm() 
    parm_list = parm_list + [ comma ]
    parm_list = parm_list + [ parm.listParm() ]
    comma = ","
  print(")")
  parm_list = parm_list + [ ")" ]
  proc_table[current_proc.lower()] = " ".join(parm_list)
  defined_proc = current_proc.lower()
  if current_proc.lower() in intret_table :
    return_default = "int"
  else :
    return_default = "void"
  print("returns", end=' ')
  if return_type : 
    printToken(return_type)
    return_type = None
  else :
    if copy_count == 0 : printToken(return_default)
    if copy_count > 1 : printToken("record")
    if copy_count == 1 : printToken(copy_token)
  print("as $$")
  for parm in parmlist :
    parm.printDecl()
  print("begin")
  parmlist = []
  current_level = move
  return 2
#
#  Insert current_proc signature
#  Preserve token
#  Clear current proc if alter
#
def procsig(token,move,alter) :
  global current_level
  global current_proc
  printMessage(token,"procsig",TRAC)
  if current_proc.lower() in proc_table :
    printToken(proc_table[current_proc.lower()])
  else:
    print("()")
  current_level = move
  if alter > 0 : current_proc = ""
  return 2
#
#  Insert the new token 
#  Preserve the current token
#
def isrt(token,move,alter) :
  global current_level
  printMessage(token,"isrt",TRAC)
  if alter > 0 : printMessage(token,"inserted",alter)
  printToken(token)
  current_level = move
  return 2
#
#  Execute a return only
#
def dortn(token,move,alter) :
  global level_stack
  global current_level
  last = len(level_stack) - 1
  if last >= 0:
    current_level = level_stack[last]
    del level_stack[last]
  else : current_level = 0
  if current_level == 0 : printToken(";")
#
#  Attempt to execute trap
#
def traptest(token,move,alter) :
  global level_stack
  global current_level
  global trap_stack
  printMessage(token,"traptest",TRAC)
  last = len(trap_stack) -1
  if last >= 0 and len(level_stack) == trap_stack[last] :
    del trap_stack[last]
    last = len(level_stack) - 1
    if last >= 0:
      current_level = level_stack[last]
      del level_stack[last]
    else : current_level = 0
    if current_level == 0 : printToken(";")
    printStack("traptest")
#
#  Process convert bracket
#  Emit token and return
#  eat bracket in state 95
#
def convbr(token,move,alter) :
  printMessage(token,"convbr",TRAC)
  dortn(token,move,alter)
  printStack("convbr")
  traptest(token,move,alter)
  if current_level != 95 :
    printToken(token)
  return 0
#
#  Emit token and return
#
def rtnem(token,move,alter) :
  printMessage(token,"rtnem",TRAC)
  printToken(token)
  dortn(token,move,alter)
  printStack("rtnem")
  traptest(token,move,alter)
  return 0
#
#  Preserve token and return
#  Closes a procedure
#  Flushes the stack
#
def procend(token,move,alter) :
  global level_stack
  global current_level
  global copy_count
  global proc_type
  global current_proc
  global current_begin
  printMessage(token,"procend",TRAC)
  printToken("null")
  current_begin.reset(token,move,alter)
  proc_type = None
  copy_count = 0
  if current_proc == "" : return
  dortn(token,move,alter)
  while current_level != 80 and current_level != 90 and len(level_stack) > 0:
    dortn(token,move,alter)
    printStack("procend")
    traptest(token,move,alter)
  current_proc = ""
  for tab in tab_table :
    if tab_table[tab] == "DECLARE" :
      tab_table[tab] = "DROP"
      #printMessage(tab,"DROPPED",INFO) 
  return 2
#
#  Preserve token and move
#  Generates a trigger
#
def triggen(token,move,alter) :
  global current_level
  global trig_proc
  printMessage(token,"triggen",TRAC)
  dortn(token,move,alter)
  if trig_proc != "" :
    if trig_when == "instead":
      printToken("create rule")
      printToken(trig_proc)
      printToken("as on")
      printToken(trig_event)
      printToken("to")
      printToken(trig_tabname)
      printToken("do instead")
      printToken("select")
      printToken(trig_proc)
      printToken("();")
    else:
      printToken("create trigger")
      printToken(trig_proc)
      printToken(trig_when)
      printToken(trig_event)
      printToken("on")
      printToken(trig_tabname)
      printToken("execute procedure")
      printToken(trig_proc)
      printToken("();")
    trig_proc = ""
  return 2
#
#  Execute a call only
#  Proc is calling proc
#
def docall(token,move,alter,proc) :
  global level_stack
  global current_level
  if alter > 0 :
    level_stack = level_stack + [ alter ]
  else :
    level_stack = level_stack + [ current_level ]
  current_level = move
  printStack(proc)
#
#  Emit token and call
#
def callem(token,move,alter) :
  printMessage(token,"callem",TRAC)
  printToken(token)
  docall(token,move,alter,"callem")
  return 0
#
#  Preserve token and call
#
def call(token,move,alter) :
  printMessage(token,"call",TRAC)
  docall(token,move,alter,"call")
  return 2
#
# Execute a replace only
#
def dorepl(token,move,alter) :
  global current_level
  global current_altstr
  printToken(current_altstr)
  if alter > 0 : printMessage(token,"replaced",alter) 
#
#  Replace token and move
#
def repl(token,move,alter) :
  global current_level
  printMessage(token,"repl",TRAC)
  dorepl(token,move,alter)
  current_level = move
  return 0

#
#  Replace token set type
#  Only used for paramaters
#
def parmrep(token,move,alter) :
  global current_level
  global current_parm
  global current_altstr
  printMessage(token,"parmrep",TRAC)
  current_parm.setType(current_altstr)
  if alter > 0 : printMessage(token,"replaced",alter) 
  current_level = move
  return 0
#
#  Replace token and set return type
#  Only used for return types
#
def procrep(token,move,alter) :
  global current_level
  global return_type
  global proc_return
  global current_altstr
  printMessage(token,"procrep",TRAC)
  return_type = current_altstr
  proc_return[current_proc] = return_type
  if alter > 0 : printMessage(token,"replaced",alter) 
  current_level = move
  return 0
#
#  Replace token and set return type
#  Only used for return types
#  Same as procrep but saves temp table name
#
def proctemp(token,move,alter) :
  global current_level
  global return_type
  global return_temp
  global current_altstr
  printMessage(token,"procrep",TRAC)
  return_temp = return_type
  return_type = current_altstr
  if alter > 0 : printMessage(token,"replaced",alter) 
  current_level = move
  return 0

#
# Parse case table for SQL              
#
class parsecase :
  def __init__(self, level, action, move, alter, token, altstr) :
    self.level = level
    self.action = action
    self.move = move
    self.alter = alter
    self.token = token
    self.altstr = altstr

cases = []
casedir = {}

#
#  Add a case to the case table
#
def addCase(level, action, move, alter, token, altstr) :
  global cases
  global casedir
  case =  parsecase(level, action, move, alter, token, altstr) 
  cases = cases + [ case ]
  if level in casedir :
    casedir[level] = casedir[level] + [ case ]
  else :
    casedir[level] = [ case ]
    #print("+++>",case.level)

#
#  Print the rule set level
#
def printRule(level,depth) :
  global cases
  if depth > 4 : return
  for case in cases :
    if level > 0 and level == case.level :
      indent = 0
      while indent <= depth :
        print ("    ",end=' ')
        indent = indent + 1
      action = getattr(case.action,"__name__")
      print(case.level,action,case.token)
      if case.move == case.level :
        print("===========================================loop")
        return
      if case.move > 0 :
        printRule(case.move,depth+1)
#
#  Print the rule set
#
def printRules() :
  global cases
  for case in cases :
    if case.level == 0 :
      action = getattr(case.action,"__name__")
      print(case.level,action,case.token)
      printRule(case.move,0)
#
#  Print the case table
#
def printCases() :
  global cases
  global MSGLIST
  top_level = {}		# list of top level states
  used_level = []		# list of used level states
  print_level = []		# list of printed level states
  state_number = {}		# new state number dictionary
  newlevel = 1000		# new state number
  toplevel = 1000		# new top level number
  state_number[0] = 0
  for case in cases :
    if case.level == 0 and case.move != 0 :
      top_level[ case.move ] = case.token
    if case.level < 100 :
      state_number[case.level] = case.level
    if case.level > 99  and case.level not in used_level :
      if case.level in top_level :
        while newlevel > toplevel : 
          toplevel = toplevel + 100
        newlevel = toplevel
      state_number[case.level] = newlevel
      used_level = used_level + [case.level]
      newlevel = newlevel + 5
      lastlevel = 0
  print("\ndef addAllCases() :\n")
  for case in cases :
    if case.alter > 99 : case.alter = state_number[case.alter]
    if case.level in top_level and case.level not in print_level: 
      print("\n# {0}\n".format(top_level[case.level]))
      print_level = print_level + [case.level]
      lastlevel = case.level
    if lastlevel != case.level : print()
    lastlevel = case.level
    action = getattr(case.action,"__name__")
    print("  addCase({0:<4d},{1:8s},".format(state_number[case.level],action), end=' ')
    print("{0:<4d}, ".format(state_number[case.move]), end=' ')
    if case.alter in MSGLIST :
      alt = MSGLIST[case.alter]
    else :
      alt = "{0:<4d}".format(case.alter)
    print("{0},".format(alt), end=' ')
    print("{0:20s}".format("\"{0}\",".format(case.token)), end=' ')
    alter = re.sub(r'\"',r'\\"',case.altstr)
    print("\"{0:s}\")".format(alter))

#===============================================================
# Token scanner 
# Character class table 
#==============================================================

is_table = [
#        0 ^a ^b ^c ^d ^e ^f ^g ^h ^i ^j ^k ^l ^m ^n ^o         
         9, 0, 0, 0, 0, 0, 0, 0, 0, 3, 3, 0, 0, 3, 0, 0,

#       ^p ^q ^r ^s ^t ^u ^v ^w ^x ^y ^z ^[ ^\ ^] ^^ ^-         
         0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,

#       sp  !  "  #  $  %  &  '  (  )  *  +  ,  -  .  /         
         3, 1, 6, 1, 1, 1, 2, 7, 1, 1, 2, 9, 1, 9, 1, 2,

#        0  1  2  3  4  5  6  7  8  9  :  ;  <  =  >  ?         
         8, 8, 8, 8, 8, 8, 8, 8, 8, 8, 1, 1, 2, 2, 2, 1,

#        @  A  B  C  D  E  F  G  H  I  J  K  L  M  N  O         
         5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,

#        P  Q  R  S  T  U  V  W  X  Y  Z  [  \  ]  ^  _         
         5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 1, 1, 1, 2, 5,

#        `  a  b  c  d  e  f  g  h  i  j  k  l  m  n  o         
         0, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,

#        p  q  r  s  t  u  v  w  x  y  z  {  |  }  -  .         
         4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 1, 2, 1, 2, 0 ]

in_comment = 0          # Processing commnet
is_quoted = 0           # Token is quoted
current_token = ''      # Current token 

#
#  Tokenize input line
#
def tokenize(line) :
  global in_comment
  global is_quoted
  global current_token
  doprint = 0
  tokens = []
# Remove unprintable characters
  newline = ""
  for c in line :
    if ord(c) > 127 : c = ' '
    newline = newline + c 
  line = newline
# Remove dbo
  if re.compile(r'dbo.*?\.').search(line) :
    line=re.sub(r'dbo.*?\.','',line)
# Remove != (replaced later)
  if re.compile(r'!=').search(line) :
    line=re.sub(r'!=','<>',line)
# Remove comments
  if re.compile(r'/\*.*\*/').search(line) :
    line=re.sub(r'/\*.*\*/','',line)
  if not re.compile(r'\'.*/\*').search(line) and  is_quoted == 0 :
    if re.compile(r'--').search(line) :
        if not re.compile(r'\'--\'').search(line) :
          m = re.compile(r'--').split(line)
          print("--",m[1])
          line = m[0]
    if re.compile(r'/\*').search(line) :
        in_comment = in_comment + 1
        doprint = 1
    if re.compile(r'\*/').search(line) :
        in_comment = in_comment - 1
        doprint = 1
    if in_comment or doprint :
        print(line)
        return None
# Loop thru line
  i = 0
  while i < len(line) :
        c = line[i]             # process double quotes
        i = i + 1
        if is_quoted == 7 and c == "'" and line[i] == "'" :
            # extra + c added for non dumped strings
            current_token = current_token + c + c
            i = i + 1   
            continue 
        if c == '!' : c = '_'  # replace bangs
        if c == '[' : c = ' '  # replace square brackets
        if c == ']' : c = ' '  # replace square brackets
        if c == '#' : continue # remove number signs
        if c == '@' : c = '_'  # replace at signs
        if c == '/' and ansi_warnings : c = '?'  # replace / zero divide
        if ord(c) > 127 :
          t = 5                # funny character
        else :
          t = is_table[ord(c)]
# Quote 
        if t == 7 : 
          # Remove n' construct - not used by psql
          if current_token.lower() == 'n' : current_token = ''
          if is_quoted == t :
            current_token = current_token + c
            tokens = tokens +  [ current_token ] 
            current_token = ''
            is_quoted = 0
          else :
          # Fix b' construct - must not be seperated
            if current_token.lower() == 'b' :
              current_token = current_token + c
              is_quoted = t
              continue
            if current_token != ''  :
              tokens = tokens +  [ current_token ] 
            current_token = c
            is_quoted = t
          continue
# Test quoted
        if is_quoted > 0 :
          current_token = current_token + c
          continue 
# Imbedded dot
        if c == '.' and re.compile(r'[0-9][0-9]*').match(current_token) :
          current_token = current_token + c
          continue
# Delimiting token
        if t == 1 or t == 2 or t == 9: 
          if current_token != '' :
            tokens = tokens +  [ current_token ] 
          tokens = tokens +  [ c ]
          current_token = '' 
          continue
# Delimiter 
        if t == 3 : 
          if current_token != '' :
            tokens = tokens +  [ current_token ] 
            current_token = ''
          continue
# Upper or Lower 
        if t == 4 or t == 5 : 
          current_token = current_token + c
          continue
# Number 
        if t == 8 : 
          current_token = current_token + c
          continue
# Return tokens
  if current_token  and is_quoted == 0 :
    tokens = tokens +  [ current_token ] 
    current_token = ''
  return tokens

#=====================================================
#  Process states on a level
#  Return code is as follows:
#  0 = success, 1 = no case found, 2 = retain token  
#=====================================================

def processLevel(token) :
  global current_level
  global current_altstr
  global level_stack
  global statement_table
  global current_statement
# Process declare block
  if current_level == 0 and token != "declare" :
    current_begin.test()
  #for case in cases :                   # check the table
  for case in casedir[current_level] :
     current_altstr = case.altstr	# FIX this 
     if case.level == current_level :   # for this level
       if case.action == isrt :  
         rc=case.action(case.token,case.move,case.alter)
         return rc
       if case.token == "<key>" :               # keyword search
           if token.lower() in statement_table :
             rc = case.action(token,case.move,case.alter)
             return rc
       if case.token == "<any>" :               # token not found
         rc = case.action(token,case.move,case.alter)
         return rc
       if case.token == "<symbol>" and token[0] == '_' :# symbol found
         rc = case.action(token,case.move,case.alter)
         return rc
       if case.token == token.lower() or case.token == "<value>" :
         if current_level == 0 :                # token match
           if token.lower() in statement_table :
                statement_table[token.lower()] = statement_table[token.lower()] + 1
           current_statement = token
         rc = case.action(token,case.move,case.alter)
         return rc
  return 1
#
#  Process a token on a level
#
def processToken(token) :
  global current_level
  global level_stack
  global skip_errors
  global total_errors
  global trap_stack
  while 1 :
    last_state = current_level
    ret = processLevel(token) 
    if ret and ret > 0 :        # no matching case found
      if ret == 1 :             # no skip
        level_stack = []        # reset stack
        current_level = 0       # level 0
        trap_stack = []         # Reset trap stack 
        if skip_errors == 0 :
          printError(token,"token",last_state,UNRC)
          total_errors = total_errors + 1
          skip_errors = 1
        else :
          printToken(token)
        return
    else :
      skip_errors = 0
      return
#
#  Preprocess line before tokenization
#  you can add to this list if you like
#
def preprocessLine(line) :
  line = re.sub(r'\[PK_\[',r'[PK_',line) # replace [PK_[ 
  line = re.sub(r'CCMData]*\.','',line) # replace CCMData 
  line = re.sub(r'CCMStatisticalData]*\.','',line) # replace CCMData 
  line = re.sub(r'(datetime.*)DEFAULT.*0.*,','\\1,',line) # replace default datetime 0
  line = re.sub(r'\\',r'\\\\',line) # replace \ with \\
  line = re.sub(r'(..:..:..) ([0-9]*\/[0-9]*\/[0-9]*)','\\2 \\1',line) # Date
  return line
#
#  Process input file
#
def processFile(filename) :
  global current_line
  global current_sourceline
  directory = "."
  filepath = os.path.join(directory , filename)
  file = open(filepath, 'rU') 
  for line in file :
    line = preprocessLine(line)
    current_sourceline = line
# Print origional line numbers 
    print("--",current_line,"]")
    current_line = current_line + 1
    tokens = tokenize(line)
    if tokens :
      for token in  tokens :
        processToken(token)
# Print newline at end of line 
    if is_quoted == 0 : print()
  return
#
# Read the int return list
#
def readIntRets() :
  global intret_table
  directory = "."
  filepath = os.path.join(directory , "retlist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
        intret_table[line.rstrip("\n")] = 0
         #print(line.rstrip("\n"))
#
# Read the function database
#
def readFuncDB() :
  global proc_table
  directory = "."
  filepath = os.path.join(directory , "funclist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("(")
      proc_table[line[0:i]] = line[i:]
#      print "/*",line[0:i],":",line[i:],"*/"
#
# Read the trigger database
#
def readTrigDB() :
  global trig_table
  directory = "."
  filepath = os.path.join(directory , "triglist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("|")
      trig_table[line[0:i]] = line[i+1:]
#      print "/*",line[0:i],":",line[i+1:],"*/"
#
# Read the table database
#
def readTabDB() :
  global tab_table
  directory = "."
  filepath = os.path.join(directory , "tablist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("|")
      tab_table[line[0:i]] = line[i+1:]
#      print "/*",line[0:i],":",line[i+1:],"*/"
#
# Read the column database
#
def readColDB() :
  global col_table
  directory = "."
  filepath = os.path.join(directory , "collist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("|")
      col_table[line[0:i]] = line[i+1:]
#
# Read the procref database
#
def readProcrefDB() :
  global procref_table
  directory = "."
  filepath = os.path.join(directory , "procref.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("|")
      procref_table[line[0:i]] = line[i+1:]
      #print(line[0:i]," = ",line[i+1:])
#
# Read the procret database
#
def readProcretDB() :
  global proc_return
  directory = "."
  filepath = os.path.join(directory , "procret.db")
  if os.path.exists(filepath) :
    file = open(filepath,'r')
    for line in file :
      line = line.rstrip("\n")
      i = line.find("|")
      proc_return[line[0:i]] = line[i+1:]
      #print(line[0:i]," = ",line[i+1:])
#########################################################################################

def addAllCases() :

  addCase(0   ,drop    , 2700,  0   , "identity_insert",   "# delete? ")
  addCase(0   ,drop    , 2900,  INFO, "ansi_padding",      "# delete? ")
  addCase(0   ,drop    , 0   ,  0   , "textimage_on",      "# delete? ")
  addCase(0   ,drop    , 0   ,  0   , "on",                "# delete? ")
  addCase(0   ,drop    , 0   ,  0   , "primary",           "# delete? ")
  addCase(0   ,call    , 9999,  0   , "create",            "# create ")
  addCase(0   ,call    , 1400,  0   , "select",            "# select")
  addCase(0   ,call    , 1700,  0   , "raiserror",         "# raise exception")
  addCase(0   ,call    , 1790,  0   , "drop",              "# drop")
  addCase(0   ,call    , 1890,  0   , "truncate",          "# truncate")
  addCase(0   ,call    , 2000,  0   , "print",             "# raise info")
  addCase(0   ,call    , 2050,  0   , "if",                "# if")
  addCase(0   ,emit    , 0   ,  0   , "else",              "# else")
  addCase(0   ,repl    , 0   ,  0   , "break",             "exit;")
  addCase(0   ,jump    , 3600,  0   , "begin",             "# begin")
  addCase(0   ,jump    , 3700,  0   , "end",               "# end")
  addCase(0   ,drop    , 0   ,  UNSP, "commit",            "# commit")
  addCase(0   ,repl    , 0   ,  0   , "rollback",          "raise exception 'ROLLBACK';")
  addCase(0   ,drop    , 0   ,  0   , "transaction",       "# transaction")
  addCase(0   ,drop    , 0   ,  0   , "tran",              "# tran")
  addCase(0   ,procend , 0   ,  0   , "go",                "# go")
  addCase(0   ,drop    , 0   ,  0   , ";",                 "# ;")
  addCase(0   ,begdcl  , 2200,  0   , "declare",           "# declare")
  addCase(0   ,call    , 2290,  0   , "open",              "# open")
  addCase(0   ,call    , 2290,  0   , "close",             "# close")
  addCase(0   ,call    , 2400,  0   , "deallocate",        "# deallocate")
  addCase(0   ,call    , 2490,  0   , "fetch",             "# fetch")
  addCase(0   ,call    , 2600,  0   , "set",               "# set")
  addCase(0   ,call    , 2990,  0   , "while",             "# while")
  addCase(0   ,call    , 3100,  0   , "exec",              "# exec")
  addCase(0   ,call    , 3100,  0   , "execute",           "# exeutec")
  addCase(0   ,call    , 3190,  0   , "insert",            "# insert")
  addCase(0   ,call    , 3290,  0   , "return",            "# return")
  addCase(0   ,call    , 3390,  0   , "update",            "# update")
  addCase(0   ,call    , 3500,  0   , "use",               "# use")
  addCase(0   ,call    , 3800,  0   , "alter",             "# alter")
  addCase(0   ,call    , 4090,  0   , "delete",            "# delete")

  addCase(70  ,prtlim  , 71  ,  1   , "<any>",             "# end of select list")

  addCase(71  ,skip    , 0   ,  0   , "<any>",             "# end of select list")

  addCase(80  ,isrt    , 81  ,  0   , "end; $$ language plpgsql", "# end of proc")

  addCase(81  ,triggen , 0   ,  0   , "<any>",             "# end of trigger")

  addCase(90  ,isrt    , 91  ,  0   , "return null; end; $$ language plpgsql", "# end of proc")

  addCase(91  ,triggen , 0   ,  0   , "<any>",             "# end of trigger")

  addCase(95  ,isrt    , 96  ,  0   , "as",                "# replace convert type ")

  addCase(96  ,popall  , 97  ,  0   , "<any>",             "# ")

  addCase(97  ,isrt    , 98  ,  0   , ")",                 "# ")

  addCase(98  ,skip    , 0   ,  0   , "<any>",             "# ")

# create

  addCase(9999,emit    , 1000,  0   , "create",             "############ create")

  addCase(1000,emit    , 1005,  0   , "table",             "# create table")
  addCase(1000,emit    , 1050,  0   , "view",              "# create view")
  addCase(1000,repl    , 1210,  0   , "procedure",         "function")
  addCase(1000,emit    , 1210,  0   , "function",          "# function")
  addCase(1000,drop    , 1305,  0   , "trigger",           "# trigger")
  addCase(1000,drop    , 1000,  INFO, "clustered",         "# ")
  addCase(1000,drop    , 1000,  0   , "nonclustered",      "# ")
  addCase(1000,emit    , 1000,  0   , "unique",            "# ")
  addCase(1000,emit    , 1000,  0   , "or",                "# ")
  addCase(1000,emit    , 1000,  0   , "replace",           "# ")
  addCase(1000,emit    , 1190,  0   , "index",             "# create index")

  addCase(1005,emit    , 1015,  0   , "(",                 "# missing name")
  addCase(1005,tabname , 1010,  0   , "<value>",           "# table name ")

  addCase(1010,emit    , 1015,  0   , "(",                 "# ")
  addCase(1010,emit    , 1005,  0   , ".",                 "# schema.table")

  addCase(1015,emit    , 1175,  0   , ")",                 "# ")
  addCase(1015,emit    , 1165,  0   , "constraint",        "# ")
  addCase(1015,emit    , 1175,  0   , "primary",           "# ")
  addCase(1015,drop    , 1015,  0   , "asc",               "# ")
  addCase(1015,repl    , 1020,  0   , "user",              "\"user\"")
  addCase(1015,repl    , 1020,  0   , "offset",            "\"offset\"")
  addCase(1015,tabcol  , 1020,  0   , "<value>",           "# column name")

  addCase(1020,repl    , 1025,  0   , "tinyint",           "smallint")
  addCase(1020,repl    , 1025,  0   , "datetime",          "timestamp")
  addCase(1020,repl    , 1025,  0   , "nvarchar",          "varchar")
  addCase(1020,repl    , 1025,  0   , "varbinary",         "bit varying")
  addCase(1020,repl    , 1025,  0   , "money",             "numeric(19,4)")
  addCase(1020,repl    , 1025,  0   , "bit",               "boolean")
  addCase(1020,repl    , 1025,  0   , "ntext",             "text")
  addCase(1020,repl    , 1025,  0   , "uniqueidentifier",  "uuid")
  addCase(1020,emit    , 1025,  0   , "<value>",           "# column type")

  addCase(1025,emit    , 1015,  0   , ",",                 "# ")
  addCase(1025,callem  , 1035,  0   , "(",                 "# ")
  addCase(1025,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1025,emit    , 1025,  0   , "not",               "# ")
  addCase(1025,emit    , 1025,  0   , "null",              "# ")
  addCase(1025,drop    , 1025,  INFO, "rowguidcol",        "# ")
  addCase(1025,repl    , 1026,  0   , "identity",          "default identity")
  addCase(1025,drop    , 1045,  0   , "collate",           "# ")
  addCase(1025,call    , 1075,  0   , "constraint",        "# ")
  addCase(1025,drop    , 1030,  0   , "on",                "# ")
  addCase(1025,emit    , 1175,  0   , "primary",           "# ")
  addCase(1025,call    , 1088,  0   , "default",           "# ")
  addCase(1025,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1026,callem  , 1035,  1025, "(",                 "# ")
  addCase(1026,isrt    , 1025,  UNSP, "(0,0)",             "# ")

  addCase(1030,drop    , 1025,  0   , "primary",           "# ")

  addCase(1035,call    , 1400,  1040, "select",            "# ")
  addCase(1035,emit    , 1040,  0   , "<value>",           "# column size")

  addCase(1040,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1040,callem  , 1040,  0   , "(",                 "# function")
  addCase(1040,emit    , 1035,  0   , ",",                 "# ")
  addCase(1040,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1045,drop    , 1025,  0   , "<value>",           "# collate")

  addCase(1050,emit    , 1055,  0   , "<value>",           "# view name ")

  addCase(1055,drop    , 1055,  0   , "with",              "# ")
  addCase(1055,drop    , 1055,  0   , "schemabinding",     "# ")
  addCase(1055,emit    , 1060,  0   , "as",                "# ")
  addCase(1055,emit    , 1065,  0   , "(",                 "# ")
  addCase(1055,emit    , 1050,  0   , ".",                 "# ")
  addCase(1055,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1060,call    , 1400,  0   , "select",            "# ")
  addCase(1060,emit    , 1060,  0   , "union",             "# ")
  addCase(1060,emit    , 1050,  0   , "as",                "# ")
  addCase(1060,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1065,emit    , 1070,  0   , "<value>",           "# view colname ")

  addCase(1070,emit    , 1065,  0   , ",",                 "# ")
  addCase(1070,emit    , 1060,  0   , ")",                 "# ")

  addCase(1075,drop    , 1080,  0   , "constraint",        "# ")

  addCase(1080,save    , 1085,  0   , "<value>",           "# constraint name")

  addCase(1085,emit    , 1095,  0   , "default",           "# ")
  addCase(1085,save    , 1115,  0   , "check",             "# ")
  addCase(1085,save    , 1130,  0   , "primary",           "# ")
  addCase(1085,save    , 1130,  0   , "unique",            "# ")
  addCase(1085,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1088,emit    , 1090,  0   , "default",           "############ default ")

  addCase(1090,callem  , 1090,  0   , "(",                 "# ")
  addCase(1090,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1090,emit    , 1090,  0   , "-",                 "# ")
  addCase(1090,skip    , 0   ,  0   , ",",                 "# ")
  addCase(1090,drop    , 1080,  0   , "constraint",        "# ")
  addCase(1090,repl    , 1100,  INFO, "'8.0.7'",           "0")
  addCase(1090,emit    , 1100,  0   , "<value>",           "# ")

  addCase(1095,clear   , 1090,  0   , "<any>",             "# ")

  addCase(1100,callem  , 1105,  0   , "(",                 "# function")
  addCase(1100,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1100,emit    , 1090,  0   , ".",                 "# ")
  addCase(1100,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1105,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1105,emit    , 1110,  0   , "<value>",           "# ")

  addCase(1110,emit    , 1105,  0   , ",",                 "# ")
  addCase(1110,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(1115,isrt    , 1120,  0   , "constraint",        "# ")

  addCase(1120,popall  , 1125,  0   , "<any>",             "# ")

  addCase(1125,callem  , 1125,  1025, "(",                 "# check")
  addCase(1125,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1125,emit    , 1125,  0   , "<value>",           "# ")

  addCase(1130,save    , 1135,  0   , "key",               "# ")
  addCase(1130,drop    , 1130,  0   , "nonclustered",      "# ")
  addCase(1130,drop    , 1130,  0   , "clustered",         "# ")

  addCase(1135,drop    , 1135,  0   , "nonclustered",      "# ")
  addCase(1135,drop    , 1135,  0   , "clustered",         "# ")
  addCase(1135,drop    , 1145,  0   , "(",                 "# table constraint")
  addCase(1135,isrt    , 1140,  0   , "constraint",        "# ")

  addCase(1140,popall  , 1175,  0   , "<any>",             "# ")

  addCase(1145,isrt    , 1150,  0   , ", constraint",      "# ")

  addCase(1150,popall  , 1155,  0   , "<any>",             "# ")

  addCase(1155,isrt    , 1160,  0   , "(",                 "# ")

  addCase(1160,emit  , 1162,  0, "<value>",           "# ")

  addCase(1162,call    , 1015,  1175, "<any>",           "# ")

  addCase(1165,emit    , 1170,  0   , "<value>",           "# constraint name")

  addCase(1170,emit    , 1125,  0   , "check",             "# ")
  addCase(1170,emit    , 1175,  0   , "primary",           "# ")
  addCase(1170,emit    , 1175,  0   , "unique",            "# ")
  addCase(1170,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1175,emit    , 1175,  0   , "key",               "# primary key")
  addCase(1175,drop    , 1175,  0   , "clustered",         "# ")
  addCase(1175,drop    , 1175,  0   , "nonclustered",      "# ")
  addCase(1175,emit    , 1175,  0   , "unique",            "# ")
  addCase(1175,callem  , 1180,  0   , "(",                 "# ")
  addCase(1175,drop    , 1175,  0   , "on",                "# ")
  addCase(1175,drop    , 1175,  0   , "textimage_on",      "# ")
  addCase(1175,drop    , 1175,  0   , "primary",           "# ")
  addCase(1175,emit    , 1015,  0   , ",",                 "# ")
  addCase(1175,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1175,call    , 1335,  0   , "with",              "# unsupported ")
  addCase(1175,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1180,emit    , 1185,  0   , "<value>",           "# ")

  addCase(1185,drop    , 1185,  0   , "asc",               "# ")
  addCase(1185,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1185,emit    , 1180,  0   , ",",                 "# ")

  addCase(1190,emit    , 1195,  0   , "on",                "# index")
  addCase(1190,emit    , 1190,  0   , "<value>",           "# ")

  addCase(1195,emit    , 1200,  0   , "(",                 "# ")
  addCase(1195,emit    , 1195,  0   , ".",                 "# ")
  addCase(1195,emit    , 1195,  0   , "<value>",           "# ")

  addCase(1200,emit    , 1200,  0   , ",",                 "# ")
  addCase(1200,emit    , 1205,  0   , ")",                 "# ")
  addCase(1200,emit    , 1200,  0   , "<value>",           "# ")

  addCase(1205,call    , 1335,  0   , "with",              "# unsupported ")
  addCase(1205,drop    , 1205,  0   , "on",                "# ")
  addCase(1205,drop    , 1205,  0   , "primary",           "# ")
  addCase(1205,call    , 1335,  0   , "include",           "# unsupported")
  addCase(1205,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1210,procset , 1215,  0   , "<value>",           "# procedure name")

  addCase(1215,drop    , 1250,  0   , "as",                "# no parameters")
  addCase(1215,drop    , 1215,  0   , "(",                 "# ")
  addCase(1215,drop    , 1250,  0   , ")",                 "# ")
  addCase(1215,parmnew , 1220,  0   , "<value>",           "# parameter name")

  addCase(1220,parmrep , 1230,  0   , "nvarchar",          "varchar")
  addCase(1220,parmrep , 1230,  0   , "nchar",             "char")
  addCase(1220,parmrep , 1230,  0   , "uniqueidentifier",  "uuid")
  addCase(1220,parmrep , 1230,  0   , "datetime",          "timestamp")
  addCase(1220,parmrep , 1230,  0   , "sql_variant",       "varchar")
  addCase(1220,parmrep , 1230,  0   , "varbinary",         "bit varying")
  addCase(1220,parmrep , 1230,  0   , "ntext",             "text")
  addCase(1220,parmrep , 1230,  0   , "tinyint",           "smallint")
  addCase(1220,parmrep , 1230,  0   , "bit",               "boolean")
  addCase(1220,parmrep , 1230,  UNSP, "sysname",           "varchar(128)")
  addCase(1220,drop    , 1220,  0   , "as",                "# is valid in MS")
  addCase(1220,drop    , 1225,  0   , "returns",           "# ")
  addCase(1220,prmtype , 1230,  0   , "<value>",           "# type")

  addCase(1225,emit  , 1227,  0   , "table",             "# ")
  addCase(1225,drop    , 1250,  0   , "as",                "# ")
  addCase(1225,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1225,procret , 1225,  0   , "<value>",           "# return type")

  addCase(1227,call    , 1005,  1225   , "<any>",             "############ returns table ")

  addCase(1230,drop    , 1260,  0   , "(",                 "# size")
  addCase(1230,drop    , 1235,  0   , "=",                 "# default")
  addCase(1230,parmout , 1230,  0   , "output",            "# output parameter      ")
  addCase(1230,drop    , 1250,  0   , "as",                "# ")
  addCase(1230,drop    , 1245,  0   , ")",                 "# ")
  addCase(1230,parmadd , 1240,  0   , "<any>",             "# ")

  addCase(1235,drop    , 1235,  0   , "-",                 "# ")
  addCase(1235,drop    , 1230,  0   , "<value>",           "# ")

  addCase(1240,drop    , 1215,  0   , ",",                 "# ")
  addCase(1240,emit    , 1225,  0   , "returns",           "# ")
  addCase(1240,emit    , 1245,  0   , ")",                 "# ")

  addCase(1245,drop    , 1275,  0   , "returns",           "# ")
  addCase(1245,drop    , 1250,  0   , "as",                "# ")

  addCase(1250,drop    , 1250,  0   , "as",                "# ")
  addCase(1250,drop    , 1275,  0   , "returns",           "# returns given")
  addCase(1250,prmisrt , 1255,  0   , "<any>",             "# insert parameter list")

  addCase(1255,call    , 0   ,  80  , "<any>",             "# procedure definition")

  addCase(1260,prmsize , 1265,  UNSP, "max",               "# size given")
  addCase(1260,prmsize , 1265,  0   , "<value>",           "# size given")

  addCase(1265,parmout , 1265,  0   , "output",            "# ")
  addCase(1265,drop    , 1270,  0   , "=",                 "# ")
  addCase(1265,drop    , 1265,  0   , ")",                 "# ")
  addCase(1265,drop    , 1250,  0   , "as",                "# ")
  addCase(1265,drop    , 1275,  0   , "returns",           "# ")
  addCase(1265,parmadd , 1240,  0   , "<any>",             "# add paramater ")

  addCase(1270,drop    , 1265,  0   , "<value>",           "# ")

  addCase(1275,procrep , 1280,  0   , "table",             "setof record")
  addCase(1275,procret , 1280,  0   , "int",               "# ")
  addCase(1275,procrep , 1280,  0   , "bit",               "boolean")
  addCase(1275,procrep , 1280,  0   , "datetime",          "timestamp")
  addCase(1275,procret , 1280,  0   , "float",             "# ")
  addCase(1275,procrep , 1280,  0   , "nvarchar",          "varchar")
  addCase(1275,procret , 1280,  0   , "varchar",           "# ")
  addCase(1275,procret , 1280,  0   , "bigint",            "# ")
  addCase(1275,procrep , 1280,  0   , "uniqueidentifier",  "uuid")
  addCase(1275,drop    , 1250,  0   , "as",                "# ")
  addCase(1275,procret , 1285,  0   , "<value>",           "# table name?")

  addCase(1280,drop    , 1280,  0   , "(",                 "# ")
  addCase(1280,drop    , 1280,  0   , ")",                 "# ")
  addCase(1280,drop    , 1280,  0   , "with",              "# ")
  addCase(1280,drop    , 1280,  0   , "schemabinding",     "# ")
  addCase(1280,drop    , 1250,  0   , "as",                "# ")
  addCase(1280,drop    , 1280,  0   , "<value>",           "# ")

  addCase(1285,proctemp, 1290,  0   , "table",             "setof record")
  addCase(1285,repl    , 1285,  0   , "as",                ";")
  addCase(1285,drop    , 1285,  0   , "with",              "# ")
  addCase(1285,drop    , 1285,  0   , "schemabinding",     "# ")
  addCase(1285,call    , 0   ,  80  , "<any>",             "# ")

  addCase(1290,prmisrt , 1295,  0   , "<any>",             "# ")

  addCase(1295,isrt    , 1296,  0   , "create temp table ", "# ")
  addCase(1296,loadtemp, 1300,  0   , "<any>",             "# ")

  addCase(1300,callem  , 1015,  0   , "(",                 "# ")
  addCase(1300,drop    , 1300,  0   , "with",              "# ")
  addCase(1300,drop    , 1300,  0   , "schemabinding",     "# ")
  addCase(1300,drop    , 1300,  0   , "as",                "# ")
  addCase(1300,isrt    , 1285,  0   , ";",                 "# ")

  addCase(1305,drop    , 1310,  0   , "on",                "# ")
  addCase(1305,triglog , 1305,  0   , "<value>",           "# trigger name")

  addCase(1310,triglog , 1315,  1   , "<value>",           "# table name")

  addCase(1315,drop    , 1320,  0   , "as",                "# on ")
  addCase(1315,triglog , 1315,  2   , "for",               "# ")
  addCase(1315,drop    , 1315,  0   , "of",                "# ")
  addCase(1315,triglog , 1315,  2   , "instead",           "# ")
  addCase(1315,triglog , 1315,  2   , "after",             "# ")
  addCase(1315,triglog , 1315,  2   , "before",            "# ")
  addCase(1315,triglog , 1315,  3   , "delete",            "# ")
  addCase(1315,triglog , 1315,  3   , "insert",            "# ")
  addCase(1315,triglog , 1315,  3   , "update",            "# ")
  addCase(1315,drop    , 1315,  0   , ",",                 "# ")
  addCase(1315,drop    , 1315,  0   , "<value>",           "# ")

  addCase(1320,isrt    , 1325,  0   , "function",          "# ")

  addCase(1325,trighed , 1330,  0   , "<any>",             "# ")

  addCase(1330,call    , 0   ,  90  , "<any>",             "# ")

  addCase(1335,drop    , 1340,  UNSP, "with",              "# UNSUPPORTED")
  addCase(1335,drop    , 1340,  UNSP, "include",           "# UNSUPPORTED")

  addCase(1340,call    , 1345,  0   , "(",                 "# delete with")
  addCase(1340,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1345,drop    , 1350,  0   , "(",                 "# ")

  addCase(1350,drop    , 1355,  0   , ")",                 "# ")
  addCase(1350,call    , 1345,  0   , "(",                 "# ")
  addCase(1350,drop    , 1350,  0   , "<any>",             "# ")

  addCase(1355,skip    , 0   ,  0   , "<any>",             "# ")

# select

  addCase(1400,emit    ,1402,  0  , "select",            "############ select")
  addCase(1402,call    , 1405,  70, "<any>",              "# ")

  addCase(1405,emit    , 1455,  0   , "*",                 "############ select list")
  addCase(1405,emit    , 1410,  0   , "into",              "# ")
  addCase(1405,drop    , 1455,  0   , "as",                "# as ? ")
  addCase(1405,prtinto , 1485,  0   , "from",              "# from ?")
  addCase(1405,repl    , 1455,  0   , "db_name",           "current_database")
  addCase(1405,drop    , 1445,  0   , "top",               "# ")
  addCase(1405,callem  , 1415,  1455, "(",                 "# ")
  addCase(1405,call    , 1605,  1455, "case",              "# ")
  addCase(1405,emit    , 1405,  0   , "-",                 "# ")
  addCase(1405,call    , 1640,  1455, "replace",           "# ")
  addCase(1405,emit    , 1405,  0   , "distinct",          "# ")
  addCase(1405,call    , 1430,  1455, "dateadd",           "# ")
  addCase(1405,call    , 1430,  1455, "datepart",          "# ")
  addCase(1405,call    , 1430,  1455, "datediff",          "# ")
  addCase(1405,call    , 2740,  1455, "convert",           "# ")
  addCase(1405,call    , 2015,  1455, "cast",              "# ")
  addCase(1405,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1405,savinto , 1425,  0   , "<symbol>",          "# symbol ")
  addCase(1405,repl    , 1455,  0   , "user",              "\"user\"")
  addCase(1405,repl    , 1455,  0   , "offset",            "\"offset\"")
  addCase(1405,repl    , 1455,  UNSP, "'00000000-0000-0000-0000-000000000000'", "cast ('00000000-0000-0000-0000-000000000000' as uuid )")
  addCase(1405,emit    , 1455,  UNSP, "null",              "# uncast null")
  addCase(1405,procref , 1455,  0   , "<value>",           "# colname ")

  addCase(1410,emit    , 1405,  0   , "<value>",           "############ into variable ")

  addCase(1415,subsel  , 1420,  1   , "select",            "# ")
  addCase(1415,jump    , 1405,  0   , "<any>",             "# ")

  addCase(1420,call    , 1400,  0   , "select",            "# ")
  addCase(1420,subsel  , 1405,  0   , "<any>",             "# ")

  addCase(1425,drop    , 1405,  0   , "=",                 "############ col assign")
  addCase(1425,lodinto , 1455,  0   , "<any>",             "# ")

  addCase(1430,emit    , 1435,  0   , "dateadd",           "# ")
  addCase(1430,emit    , 1435,  0   , "datediff",          "# ")
  addCase(1430,emit    , 1435,  0   , "datepart",          "# ")

  addCase(1435,emit    , 1440,  0   , "(",                 "# ")

  addCase(1440,repl    , 1480,  0   , "s",                 "'ss'")
  addCase(1440,repl    , 1480,  0   , "ss",                "'ss'")
  addCase(1440,repl    , 1480,  0   , "mi",                "'minute'")
  addCase(1440,repl    , 1480,  0   , "minute",            "'minute'")
  addCase(1440,repl    , 1480,  0   , "hh",                "'hour'")
  addCase(1440,repl    , 1480,  0   , "hour",              "'hour'")
  addCase(1440,repl    , 1480,  0   , "year",              "'year'")
  addCase(1440,repl    , 1480,  0   , "d",                 "'day'")
  addCase(1440,repl    , 1480,  0   , "dd",                "'day'")
  addCase(1440,repl    , 1480,  0   , "dw",                "'day'")
  addCase(1440,repl    , 1480,  0   , "day",               "'day'")
  addCase(1440,emit    , 1480,  0   , "<any>",             "# ")

  addCase(1445,drop    , 1445,  0   , "(",                 "########### top limit")
  addCase(1445,prtlim  , 1450,  0   , "<value>",           "# set limit ")

  addCase(1450,drop    , 1405,  UNSP, "percent",           "########### top percent")
  addCase(1450,drop    , 1405,  0   , ")",                 "# ")
  addCase(1450,jump    , 1405,  0   , "<any>",             "# ")

  addCase(1455,emit    , 1405,  0   , "+",                 "########### select list operator")
  addCase(1455,emit    , 1405,  0   , "-",                 "# ")
  addCase(1455,emit    , 1405,  0   , "/",                 "# ")
  addCase(1455,emit    , 1405,  0   , "?",                 "# ")
  addCase(1455,emit    , 1405,  0   , "*",                 "# ")
  addCase(1455,emit    , 1405,  0   , "=",                 "# assignment")
  addCase(1455,emit    , 1405,  0   , ".",                 "# ")
  addCase(1455,emit    , 1405,  0   , ",",                 "# ")
  addCase(1455,procref , 1456,  1   , "(",                 "# function reference")
  addCase(1455,rtnem   , 0   ,  0   , ")",                 "# end expr")
  addCase(1455,emit    , 1405,  0   , "into",              "# columns")
  addCase(1455,prtinto , 1485,  0   , "from",              "# ")
  addCase(1455,drop    , 1455,  UNSP, "collate",           "# ")
  addCase(1455,drop    , 1455,  0   , "as",                "# ")
  addCase(1455,prtinto , 1465,  0   , "<key>",             "# ")
  addCase(1455,prtas   , 1460,  0   , "<any>",             "# ")

  addCase(1456,drop    , 1457,  0, "(",                 "# function")
  addCase(1457,call    , 1475,  1455, "<any>",                 "# function")

  addCase(1460,join    , 1470,  0   , "<value>",           "############ as name")

  addCase(1465,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1470,emit    , 1405,  0   , ",",                 "############ select list continued")
  addCase(1470,prtinto , 1485,  0   , "from",              "# ")
  addCase(1470,emit    , 1405,  0   , "into",              "# columns")
  addCase(1470,callem  , 1475,  0   , "(",                 "# function")
  addCase(1470,rtnem   , 0   ,  0   , ")",                 "# end expr")
  addCase(1470,emit    , 1405,  0   , "+",                 "# ")
  addCase(1470,emit    , 1405,  0   , "-",                 "# ")
  addCase(1470,emit    , 1405,  0   , "/",                 "# ")
  addCase(1470,emit    , 1405,  0   , "?",                 "# ")
  addCase(1470,emit    , 1405,  0   , "*",                 "# ")
  addCase(1470,emit    , 1405,  0   , "=",                 "# assignment")
  addCase(1470,emit    , 1405,  0   , ".",                 "# ")
  addCase(1470,call    , 1605,  0   , "case",              "# ")
  addCase(1470,drop    , 1455,  UNSP, "collate",           "# ")
  addCase(1470,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1470,join    , 1470,  UNSP, "<value>",           "# ")

  addCase(1475,emit    , 1475,  0   , "-",                 "############ function parm value")
  addCase(1475,callem  , 1475,  1480, "(",                 "# ")
  addCase(1475,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1475,call    , 1400,  1480, "select",            "# ")
  addCase(1475,call    , 2740,  1480, "convert",           "# ")
  addCase(1475,call    , 2015,  1480, "cast",              "# ")
  addCase(1475,call    , 1430,  1480, "datepart",          "# ")
  addCase(1475,call    , 1430,  1480, "dateadd",           "# ")
  addCase(1475,call    , 1430,  1480, "datediff",          "# ")
  addCase(1475,emit    , 1475,  0   , "distinct",          "# ")
  addCase(1475,repl    , 1480,  INFO, "to",                "tot")
  addCase(1475,emit    , 1480,  0   , "<value>",           "# ")

  addCase(1480,emit    , 1475,  0   , ",",                 "############ function parm operator")
  addCase(1480,emit    , 1475,  0   , ".",                 "# ")
  addCase(1480,callem  , 1475,  0   , "(",                 "# ")
  addCase(1480,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1480,emit    , 1475,  0   , "/",                 "# ")
  addCase(1480,emit    , 1475,  0   , "?",                 "# ")
  addCase(1480,emit    , 1475,  0   , "*",                 "# ")
  addCase(1480,emit    , 1475,  0   , "-",                 "# ")
  addCase(1480,emit    , 1475,  0   , "+",                 "# ")
  addCase(1480,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1485,emit    , 1485,  0   , "from",              "############ from clause ")
  addCase(1485,callem  , 1490,  1535, "(",                 "# ")
  addCase(1485,drop    , 1485,  SERR, ".",                 "# ")
  addCase(1485,emit    , 1495,  0   , "sysobjects",        "# ")
  addCase(1485,emit    , 1495,  0   , "sysindexes",        "# ")
  addCase(1485,emit    , 4325,  0   , "information_schema", "# ")
  addCase(1485,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1485,procref , 1535,  0   , "<value>",           "# from name")

  addCase(1490,emit    , 1405,  0   , "select",            "# ")

  addCase(1495,emit    , 1500,  0   , "where",             "# sysobjects")
  addCase(1495,jump    , 1535,  0   , "<any>",             "# ")

  addCase(1500,emit    , 1525,  0   , "type",              "# sysobjects")
  addCase(1500,repl    , 1505,  0   , "name",              "id")
  addCase(1500,emit    , 1525,  0   , "xtype",             "# ")
  addCase(1500,jump    , 1570,  0   , "<any>",             "# ")

  addCase(1505,emit    , 1510,  0   , "=",                 "# ")

  addCase(1510,isrt    , 1515,  0   , "object_id(",        "# ")

  addCase(1515,emit    , 1520,  0   , "<value>",           "# ")

  addCase(1520,isrt    , 1595,  0   , ")",                 "# ")

  addCase(1525,emit    , 1530,  0   , "=",                 "# ")
  addCase(1525,emit    , 1500,  0   , "and",               "# ")

  addCase(1530,emit    , 1525,  0   , "<value>",           "# ")

  addCase(1535,emit    , 1485,  0   , ",",                 "############ from operator")
  addCase(1535,emit    , 1485,  0   , ".",                 "# schema")
  addCase(1535,emit    , 1535,  0   , "as",                "# ")
  addCase(1535,emit    , 1535,  0   , "inner",             "# ")
  addCase(1535,emit    , 1535,  0   , "outer",             "# ")
  addCase(1535,emit    , 1550,  0   , "join",              "# ")
  addCase(1535,emit    , 1535,  0   , "left",              "# ")
  addCase(1535,repl    , 1535,  INFO, "to",                "tot")
  addCase(1535,emit    , 1570,  0   , "where",             "# ")
  addCase(1535,emit    , 1540,  0   , "union",             "# ")
  addCase(1535,call    , 1335,  0   , "with",              "# UNSUPPORTED")
  addCase(1535,emit    , 1580,  0   , "group",             "# ")
  addCase(1535,emit    , 1560,  0   , "order",             "# ")
  addCase(1535,procref , 1536,  1   , "(",                 "# ")
  addCase(1535,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1535,prtlim  , 0   ,  3   , "<key>",             "# ")
  addCase(1535,emit    , 1535,  0   , "<value>",           "# table alias")

  addCase(1536,drop    , 1537,  0, "(",                 "# function")
  addCase(1537,call    , 1545,  1535, "<any>",                 "# ")

  addCase(1540,emit    , 1540,  0   , "all",               "# ")
  addCase(1540,emit    , 1405,  0   , "select",            "# ")

  addCase(1545,rtnem   , 0   ,  0   , ")",                 "############ from function")
  addCase(1545,emit    , 1545,  0   , ",",                 "# list")
  addCase(1545,skip    , 0   ,  SERR, "<key>",             "# ")
  addCase(1545,emit    , 1545,  UNSP, "null",              "# uncast null")
  addCase(1545,call    , 2015,  1545, "cast",              "# ")
  addCase(1545,emit    , 1545,  0   , "<value>",           "# parameter")

  addCase(1550,emit    , 1555,  0   , "<value>",           "############ join table ")

  addCase(1555,emit    , 1570,  0   , "on",                "############ join condition")
  addCase(1555,repl    , 1555,  INFO, "to",                "tot")
  addCase(1555,emit    , 1555,  0   , "<value>",           "# table alias ")

  addCase(1560,emit    , 1565,  0   , "by",                "############ order by")
  addCase(1560,emit    , 1560,  0   , "desc",              "# ")
  addCase(1560,emit    , 1560,  0   , "asc",               "# ")
  addCase(1560,emit    , 1565,  0   , ",",                 "# ")
  addCase(1560,emit    , 1565,  0   , ".",                 "# ")
  addCase(1560,emit    , 1565,  0   , "+",                 "# ")
  addCase(1560,drop    , 1560,  0   , "for",               "# ")
  addCase(1560,drop    , 1560,  UNSP, "xml",               "# ")
  addCase(1560,drop    , 1560,  0   , "explicit",          "# ")
  addCase(1560,callem  , 1565,  0   , "(",                 "# ")
  addCase(1560,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1560,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1560,emit    , 1560,  UNSP, "<value>",           "# ")

  addCase(1565,call    , 2015,  1560, "cast",              "# ")
  addCase(1565,call    , 2740,  1560, "convert",           "# ")
  addCase(1565,emit    , 1560,  0   , "<value>",           "# ")

  addCase(1570,emit    , 1570,  0   , "not",               "############ where value ")
  addCase(1570,emit    , 1570,  0   , "!",                 "# ")
  addCase(1570,emit    , 1570,  0   , ">",                 "# <>")
  addCase(1570,emit    , 1570,  0   , "-",                 "# ")
  addCase(1570,emit    , 1570,  0   , "=",                 "# >=")
  addCase(1570,callem  , 1575,  1595, "(",                 "# ")
  addCase(1570,emit    , 1570,  0   , "exists",            "# ")
  addCase(1570,emit    , 1600,  0   , "union",             "# ")
  addCase(1570,call    , 2015,  1595, "cast",              "# ")
  addCase(1570,call    , 1605,  1595, "case",              "# ")
  addCase(1570,call    , 2740,  1595, "convert",           "# ")
  addCase(1570,call    , 1430,  1595, "datepart",          "# ")
  addCase(1570,call    , 1430,  1595, "dateadd",           "# ")
  addCase(1570,call    , 1430,  1595, "datediff",          "# ")
  addCase(1570,emit    , 1572,  0,    "in",                "#")
  addCase(1570,emit    , 1576,  0,    "isnull",            "# ")
  addCase(1570,repl    , 1595,  INFO, "to",                "tot")
  addCase(1570,repl    , 1595,  0   , "0x0",               "null")
  addCase(1570,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1570,emit    , 1595,  0   , "<value>",           "# where column")

  addCase(1572,callem  , 1573,  1595, "(",                 "############# in list ")

  addCase(1573,call    , 1400,  1595, "select",            "#")
  addCase(1573,emit    , 1573,  0,    "-",                 "#")
  addCase(1573,emit    , 1574,  0   , "<value>",           "# ")

  addCase(1574,rtnem   , 0,     0   , ")",                 "# ")
  addCase(1574,emit    , 1573,  0   , ",",                 "# ")

  addCase(1575,call    , 1400,  1595, "select",            "############ sub select?")
  addCase(1575,callem  , 1575,  1595, "(",                 "# ")
  addCase(1575,emit    , 1595,  0   , "<value>",           "# plist value")

  addCase(1576,callem  , 1577,  1595, "(",                 "############# insnull list ")

  addCase(1577,call    , 1430,  1578, "datepart",          "# ")
  addCase(1577,call    , 1430,  1578, "dateadd",           "# ")
  addCase(1577,call    , 1430,  1578, "datediff",          "# ")
  addCase(1577,emit    , 1578,  0,    "<value>",           "# ")

  addCase(1578,emit    , 1579,  0,    ",",                 "# ")
  addCase(1578,rtnem   , 0,     0,    ")",                 "# ")

  addCase(1579,emit    , 1578,  0,    "<value>",           "# ")

  addCase(1580,emit    , 1585,  0   , "by",                "############ group by")

  addCase(1585,callem  , 1585,  1590, "(",                 "# ")
  addCase(1585,call    , 2740,  1590, "convert",           "# ")
  addCase(1585,call    , 1605,  1590, "case",              "# ")
  addCase(1585,repl    , 1590,  0   , "offset",            "\"offset\"")
  addCase(1585,repl    , 1590,  0   , "user",              "\"user\"")
  addCase(1585,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1585,emit    , 1590,  0   , "<value>",           "# ")

  addCase(1590,emit    , 1585,  0   , "/",                 "############ group operator ")
  addCase(1590,emit    , 1585,  0   , "?",                 "# ")
  addCase(1590,emit    , 1585,  0   , "*",                 "# ")
  addCase(1590,emit    , 1585,  0   , "+",                 "# ")
  addCase(1590,emit    , 1585,  0   , "-",                 "# ")
  addCase(1590,emit    , 1585,  0   , ",",                 "# ")
  addCase(1590,emit    , 1585,  0   , ".",                 "# ")
  addCase(1590,callem  , 1585,  1590, "(",                 "# ")
  addCase(1590,drop    , 1590,  0   , "with",              "# ")
  addCase(1590,drop    , 1590,  UNSP, "rollup",            "# ")
  addCase(1590,emit    , 1570,  0   , "having",            "# ")
  addCase(1590,emit    , 1560,  0   , "order",             "# ")
  addCase(1590,emit    , 1600,  0   , "union",             "# ")
  addCase(1590,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1590,skip    , 0   ,  0   , "<key>",             "# ")

  addCase(1595,emit    , 1570,  0   , "=",                 "############ where operator")
  addCase(1595,emit    , 1570,  0   , "<",                 "# ")
  addCase(1595,emit    , 1570,  0   , ">",                 "# ")
  addCase(1595,emit    , 1570,  0   , ".",                 "# ")
  addCase(1595,emit    , 1570,  0   , ",",                 "# ")
  addCase(1595,emit    , 1570,  0   , "like",              "# ")
  addCase(1595,emit    , 1595,  0   , "not",               "# ")
  addCase(1595,emit    , 1595,  0   , "with",              "# ")
  addCase(1595,emit    , 1595,  0   , "rollup",            "# ")
  addCase(1595,emit    , 1570,  0   , "exists",            "# ")
  addCase(1595,emit    , 1595,  0   , "!",                 "# ")
  addCase(1595,emit    , 1570,  0   , "where",             "# ")
  addCase(1595,emit    , 1570,  0   , "on",                "# ")
  addCase(1595,emit    , 1572,  0   , "in",                "# ")
  addCase(1595,emit    , 1595,  0   , "is",                "# ")
  addCase(1595,emit    , 1570,  0   , "null",              "# ")
  addCase(1595,emit    , 1572,  0   , "isnull",            "# ")
  addCase(1595,emit    , 1570,  0   , "between",           "# ")
  addCase(1595,emit    , 1570,  0   , "/",                 "# ")
  addCase(1595,emit    , 1570,  0   , "?",                 "# ")
  addCase(1595,emit    , 1570,  0   , "*",                 "# ")
  addCase(1595,emit    , 1570,  0   , "-",                 "# ")
  addCase(1595,emit    , 1570,  0   , "+",                 "# ")
  addCase(1595,callem  , 1570,  0   , "(",                 "# function")
  addCase(1595,prtlim  , 0   ,  2   , ")",                 "# ")
  addCase(1595,emit    , 1570,  0   , "or",                "# ")
  addCase(1595,emit    , 1570,  0   , "and",               "# ")
  addCase(1595,emit    , 1595,  0   , "inner",             "# ")
  addCase(1595,emit    , 1595,  0   , "outer",             "# ")
  addCase(1595,callem  , 1550,  0   , "join",              "# ")
  addCase(1595,emit    , 1600,  0   , "union",             "# ")
  addCase(1595,callem  , 1560,  0   , "order",             "# ")
  addCase(1595,emit    , 1580,  0   , "group",             "# ")
  addCase(1595,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(1595,emit    , 1595,  0   , "<value>",           "# table alias? ")

  addCase(1600,emit    , 1600,  0   , "all",               "############ union")
  addCase(1600,callem  , 1600,  0   , "(",                 "# ")
  addCase(1600,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1600,call    , 1400,  1595, "select",            "# ")
  addCase(1600,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1605,emit    , 1615,  0   , "case",              "############ case ")

  addCase(1615,emit    , 1615,  0   , "when",              "# ")
  addCase(1615,call    , 1400,  0   , "select",            "# ")
  addCase(1615,call    , 2740,  1620, "convert",           "# ")
  addCase(1615,callem  , 1625,  1620, "(",                 "# ")
  addCase(1615,emit    , 1615,  0   , "-",                 "# ")
  addCase(1615,emit    , 1615,  0   , "=",                 "# ")
  addCase(1615,emit    , 1615,  0   , ">",                 "# ")
  addCase(1615,call    , 1605,  1620, "case",              "# ")
  addCase(1615,emit    , 1620,  0   , "<value>",           "# ")

  addCase(1620,emit    , 1615,  0   , ".",                 "# ")
  addCase(1620,emit    , 1615,  0   , ",",                 "# ")
  addCase(1620,emit    , 1615,  0   , "-",                 "# ")
  addCase(1620,emit    , 1615,  0   , "+",                 "# ")
  addCase(1620,emit    , 1615,  0   , "/",                 "# ")
  addCase(1620,emit    , 1615,  0   , "?",                 "# ")
  addCase(1620,emit    , 1615,  0   , "*",                 "# ")
  addCase(1620,emit    , 1615,  0   , "=",                 "# ")
  addCase(1620,emit    , 1615,  0   , "<",                 "# ")
  addCase(1620,emit    , 1615,  0   , ">",                 "# ")
  addCase(1620,emit    , 1620,  0   , "is",                "# ")
  addCase(1620,emit    , 1615,  0   , "or",                "# ")
  addCase(1620,emit    , 1620,  0   , "not",               "# ")
  addCase(1620,emit    , 1620,  0   , "null",              "# ")
  addCase(1620,emit    , 1615,  0   , "then",              "# ")
  addCase(1620,emit    , 1615,  0   , "else",              "# ")
  addCase(1620,emit    , 1615,  0   , "when",              "# ")
  addCase(1620,call    , 1605,  0   , "case",              "# ")
  addCase(1620,callem  , 1625,  0   , "(",                 "# ")
  addCase(1620,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1620,emit    , 1635,  0   , "end",               "# ")
  addCase(1620,emit    , 1620,  0   , "in",                "# ")
  addCase(1620,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1625,call    , 1400,  1620, "select",            "# ")
  addCase(1625,call    , 2740,  1620, "convert",           "# ")
  addCase(1625,callem  , 1625,  1630, "(",                 "# ")
  addCase(1625,emit    , 1630,  0   , "<value>",           "# plist value")

  addCase(1630,emit    , 1625,  0   , ".",                 "# ")
  addCase(1630,emit    , 1625,  0   , ",",                 "# ")
  addCase(1630,emit    , 1625,  0   , "/",                 "# ")
  addCase(1630,emit    , 1625,  0   , "?",                 "# ")
  addCase(1630,emit    , 1625,  0   , "*",                 "# ")
  addCase(1630,emit    , 1625,  0   , "+",                 "# ")
  addCase(1630,emit    , 1625,  0   , "=",                 "# ")
  addCase(1630,emit    , 1625,  0   , "&",                 "# ")
  addCase(1630,emit    , 1625,  0   , "as",                "# ")
  addCase(1630,emit    , 1625,  0   , "-",                 "# ")
  addCase(1630,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1630,callem  , 1625,  0   , "(",                 "# ")
  addCase(1630,emit    , 1635,  0   , "end",               "# ")

  addCase(1635,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1640,emit    , 1645,  0   , "replace",           "############# replace function ")

  addCase(1645,emit    , 1650,  0   , "(",                 "# ")

  addCase(1650,call    , 1640,  1655, "replace",           "# ")
  addCase(1650,emit    , 1655,  0   , "<value>",           "# ")

  addCase(1655,callem  , 1660,  0   , "(",                 "# ")
  addCase(1655,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(1655,emit    , 1665,  0   , ",",                 "# ")

  addCase(1660,emit    , 1655,  0   , "<value>",           "# ")

  addCase(1665,repl    , 1670,  0   , "char",              "'char")
  addCase(1665,emit    , 1680,  0   , "<value>",           "# ")

  addCase(1670,emit    , 1670,  0   , "(",                 "# ")
  addCase(1670,emit    , 1675,  0   , "<value>",           "# ")

  addCase(1675,emit    , 1675,  0   , ")",                 "# ")
  addCase(1675,isrt    , 1680,  0   , "'",                 "# ")

  addCase(1680,emit    , 1685,  0   , ",",                 "# ")

  addCase(1685,emit    , 1690,  0   , "<value>",           "# ")

  addCase(1690,emit    , 1695,  0   , ")",                 "# ")

  addCase(1695,skip    , 0   ,  0   , "<any>",             "# ")

# raiserror

  addCase(1700,repl    , 1705,  0   , "raiserror",         "raise exception '%s %d %d',")

  addCase(1705,call    , 1710,  0   , "(",                 "# ")
  addCase(1705,drop    , 1705,  0   , "with",              "# ")
  addCase(1705,drop    , 1725,  0   , "log",               "# ")
  addCase(1705,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1710,drop    , 1715,  0   , "(",                 "# ")

  addCase(1715,emit    , 1720,  0   , "<value>",           "# ")

  addCase(1720,emit    , 1720,  0   , ",",                 "# ")
  addCase(1720,drop    , 1725,  0   , ")",                 "# ")
  addCase(1720,emit    , 1720,  0   , "<value>",           "# ")

  addCase(1725,skip    , 0   ,  0   , "<any>",             "# ")

# drop

  addCase(1790,emit    , 1800,  0   , "drop",              "############ drop ")

  addCase(1800,emit    , 1805,  0   , "table",             "# ")
  addCase(1800,emit    , 1815,  0   , "view",              "# ")
  addCase(1800,emit    , 1805,  0   , "constraint",        "# ")
  addCase(1800,emit    , 1825,  0   , "function",          "# ")
  addCase(1800,repl    , 1825,  0   , "procedure",         "function")
  addCase(1800,repl    , 1835,  0   , "trigger",           "trigger if exists")

  addCase(1805,tabdrop , 1810,  0   , "<value>",           "# Table name")

  addCase(1810,emit    , 1810,  0   , "cascade",           "# ")
  addCase(1810,emit    , 1805,  0   , ".",                 "# ")
  addCase(1810,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(1815,emit    , 1820,  0   , "if",                "# ")
  addCase(1815,emit    , 1810,  0   , "<value>",           "# View name")

  addCase(1820,emit    , 1815,  0   , "exists",            "# ")

  addCase(1825,procset , 1830,  0   , "<value>",           "# Function/Proc")

  addCase(1830,procsig , 1810,  1   , "<any>",             "# ")

  addCase(1835,procset , 1840,  0   , "<value>",           "# Trigger")

  addCase(1840,isrt    , 1845,  0   , "on",                "# ")

  addCase(1845,trigprt , 1850,  0   , "<any>",             "# ")

  addCase(1850,isrt    , 1855,  0   , "; drop rule if exists", "# ")

  addCase(1855,procget , 1860,  0   , "<any>",             "# ")

  addCase(1860,isrt    , 1865,  0   , "on",                "# ")

  addCase(1865,trigprt , 1870,  0   , "<any>",             "# ")

  addCase(1870,isrt    , 1875,  0   , "; drop function",   "# ")

  addCase(1875,procget , 1830,  0   , "<any>",             "# ")

# truncate

  addCase(1890,emit    , 1900,  0   , "truncate",             "############ truncate ")

  addCase(1900,emit    , 1905,  0   , "table",             "# ")

  addCase(1905,emit    , 1910,  0   , "<value>",           "# ")

  addCase(1910,skip    , 0   ,  0   , "<any>",             "# ")

# print

  addCase(2000,repl    , 2005,  0   , "print",             "raise info '%s',")

  addCase(2005,call    , 2015,  0   , "cast",              "# ")
  addCase(2005,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2005,emit    , 2010,  0   , "<value>",           "# ")

  addCase(2010,callem  , 2005,  2010, "(",                 "# ")
  addCase(2010,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2010,emit    , 2005,  0   , ",",                 "# ")
  addCase(2010,emit    , 2005,  0   , "+",                 "# ")
  addCase(2010,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2015,emit    , 2020,  0   , "cast",              "############ cast ")

  addCase(2020,emit    , 2025,  0   , "(",                 "# ")

  addCase(2025,call    , 2015,  2030, "cast",              "# ")
  addCase(2025,call    , 2740,  2030, "convert",           "# ")
  addCase(2025,call    , 1430,  2030, "datepart",          "# ")
  addCase(2025,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2025,callem  , 2025,  2030, "(",                 "# ")
  addCase(2025,emit    , 2025,  0   , "+",                 "# ")
  addCase(2025,repl    , 2025,  2030, "bit",               "boolean")
  addCase(2025,repl    , 2025,  2030, "nvarchar",          "varchar")
  addCase(2025,repl    , 2025,  2030, "datetime",          "date")
  addCase(2025,emit    , 2030,  0   , "<value>",           "# ")

  addCase(2030,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2030,callem  , 2025,  0   , "(",                 "# ")
  addCase(2030,emit    , 2025,  0   , "*",                 "# ")
  addCase(2030,emit    , 2025,  0   , "+",                 "# ")
  addCase(2030,emit    , 2025,  0   , "+",                 "# ")
  addCase(2030,emit    , 2025,  0   , "-",                 "# ")
  addCase(2030,emit    , 2025,  0   , "as",                "# ")
  addCase(2030,emit    , 2025,  0   , ",",                 "# ")
  addCase(2030,emit    , 2025,  0   , ".",                 "# ")

# if

  addCase(2050,emit    , 2100,  0   , "if",              "############ if ")

  addCase(2100,call    , 2125,  2105, "<any>",             "# ")

  addCase(2105,isrt    , 2110,  0   , "then",              "# ")

  addCase(2110,trap    , 0   ,  2115, "<any>",             "# ")

  addCase(2115,trap    , 0   ,  2115, "else",              "# ")
  addCase(2115,isrt    , 2120,  0   , "end if",            "# ")

  addCase(2120,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2125,callem  , 2125,  2130, "(",                 "# ")
  addCase(2125,emit    , 2125,  0   , "not",               "# ")
  addCase(2125,emit    , 2125,  0   , "or",                "# ")
  addCase(2125,emit    , 2125,  0   , ">",                 "# ")
  addCase(2125,emit    , 2125,  0   , "=",                 "# ")
  addCase(2125,emit    , 2125,  0   , "exists",            "# ")
  addCase(2125,call    , 1430,  0   , "datepart",          "# ")
  addCase(2125,call    , 1400,  0   , "select",            "# ")
  addCase(2125,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2125,emit    , 2130,  0   , "<value>",           "# value")

  addCase(2130,emit    , 2125,  0   , ".",                 "# ")
  addCase(2130,emit    , 2135,  0   , "<",                 "# operator")
  addCase(2130,emit    , 2135,  0   , ">",                 "# ")
  addCase(2130,emit    , 2135,  0   , "=",                 "# ")
  addCase(2130,emit    , 2135,  0   , "-",                 "# ")
  addCase(2130,emit    , 2135,  0   , "+",                 "# ")
  addCase(2130,emit    , 2150,  0   , "%",                 "# ")
  addCase(2130,emit    , 2140,  0   , "in",                "# ")
  addCase(2130,emit    , 2130,  0   , "!",                 "# ")
  addCase(2130,emit    , 2130,  0   , "is",                "# ")
  addCase(2130,emit    , 2130,  0   , "not",               "# ")
  addCase(2130,emit    , 2125,  0   , "or",                "# ")
  addCase(2130,emit    , 2125,  0   , "and",               "# ")
  addCase(2130,emit    , 2160,  0   , "null",              "# ")
  addCase(2130,callem  , 2135,  0   , "(",                 "# function")
  addCase(2130,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2130,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2135,emit    , 2135,  0   , ">",                 "# <>")
  addCase(2135,emit    , 2135,  0   , "-",                 "# ")
  addCase(2135,emit    , 2135,  0   , "=",                 "# <=")
  addCase(2135,emit    , 2160,  0   , "<value>",           "# value")

  addCase(2140,emit    , 2145,  0   , "(",                 "# list")
  addCase(2140,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(2145,emit    , 2155,  0   , "<value>",           "# ")

  addCase(2150,emit    , 2130,  0   , "<value>",           "# ")

  addCase(2155,emit    , 2145,  0   , ",",                 "# ")
  addCase(2155,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2155,emit    , 2155,  0   , "<value>",           "# <value> <value>")

  addCase(2160,emit    , 2125,  0   , "and",               "# joiner")
  addCase(2160,emit    , 2125,  0   , "or",                "# joiner")
  addCase(2160,emit    , 2135,  0   , ",",                 "# ")
  addCase(2160,emit    , 2135,  0   , "+",                 "# ")
  addCase(2160,emit    , 2135,  0   , "-",                 "# ")
  addCase(2160,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2160,callem  , 2135,  0   , "(",                 "# function")
  addCase(2160,skip    , 0   ,  0   , "<any>",             "# ")

# declare

  addCase(2200,save    , 2205,  0   , "<value>",           "# varname")

  addCase(2205,drop    , 2240,  0   , "cursor",            "# ")
  addCase(2205,drop    , 2210,  0   , "table",             "# ")
  addCase(2205,jump    , 2225,  0   , "<any>",             "# ")

  addCase(2210,begtbl  , 2215,  0   , "<any>",             "# ")

  addCase(2215,isrt    , 2220,  0   , "bogus int; begin create temp table", "# ")

  addCase(2220,tabdcl  , 1010,  0   , "<any>",             "# ")

  addCase(2225,load    , 2230,  0   , "<any>",             "# ")

  addCase(2230,emit    , 2235,  0   , "sysname",           "# ")
  addCase(2230,emit    , 2250,  0   , "cursor",            "# ")
  addCase(2230,repl    , 2260,  0   , "nvarchar",          "varchar")
  addCase(2230,emit    , 2260,  0   , "varchar",           "# ")
  addCase(2230,emit    , 2230,  0   , "int",               "# ")
  addCase(2230,emit    , 2230,  0   , "bigint",            "# ")
  addCase(2230,emit    , 2230,  0   , "smallint",          "# ")
  addCase(2230,emit    , 2230,  0   , "real",              "# ")
  addCase(2230,emit    , 2230,  0   , "float",             "# ")
  addCase(2230,emit    , 2230,  0   , "char",              "# ")
  addCase(2230,emit    , 2230,  0   , "nchar",             "# ")
  addCase(2230,repl    , 2230,  0   , "tinyint",           "smallint")
  addCase(2230,repl    , 2230,  0   , "money",             "numeric(19,4)")
  addCase(2230,repl    , 2230,  0   , "bit",               "boolean")
  addCase(2230,callem  , 2200,  0   , "(",                 "# ")
  addCase(2230,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2230,drop    , 2230,  0   , "as",                "# ")
  addCase(2230,repl    , 2230,  0   , "datetime",          "timestamp")
  addCase(2230,repl    , 2230,  0   , "uniqueidentifier",  "uuid")
  addCase(2230,repl    , 2200,  0   , ",",                 "; declare")
  addCase(2230,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2235,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2240,load    , 2245,  0   , "<any>",             "# ")

  addCase(2245,isrt    , 2250,  0   , "cursor",            "# ")

  addCase(2250,drop    , 2250,  0   , "local",             "# no hold ")
  addCase(2250,drop    , 2250,  0   , "forward_only",      "# no scoll      ")
  addCase(2250,drop    , 2250,  0   , "fast_forward",      "# ")
  addCase(2250,drop    , 2250,  0   , "static",            "# ")
  addCase(2250,drop    , 2250,  0   , "read_only",         "# ")
  addCase(2250,emit    , 2255,  0   , "for",               "# ")

  addCase(2255,drop    , 2255,  0   , "begin",             "# ")
  addCase(2255,emit    , 1405,  0   , "select",            "# ")

  addCase(2260,callem  , 2265,  2230, "(",                 "# varchar")
  addCase(2260,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(2265,emit    , 2260,  0   , "<value>",           "# ")

# close

  addCase(2290,emit    , 2300,  0   , "open",           "############ open ")
  addCase(2290,emit    , 2300,  0   , "close",           "############ close ")

  addCase(2300,emit    , 2305,  0   , "<value>",           "# ")

  addCase(2305,skip    , 0   ,  0   , "<any>",             "# ")

# deallocate

  addCase(2400,repl    , 2405,  0   , "deallocate",        "null")

  addCase(2405,drop    , 2410,  0   , "<value>",           "# ")

  addCase(2410,skip    , 0   ,  0   , "<any>",             "# ")

# fetch

  addCase(2490,emit    , 2500,  0   , "fetch",              "############ fetch ")

  addCase(2500,emit    , 2500,  0   , "next",              "# ")
  addCase(2500,emit    , 2505,  0   , "from",              "# ")
  addCase(2500,emit    , 2505,  0   , "into",              "# ")
  addCase(2500,emit    , 2505,  0   , ",",                 "# ")
  addCase(2500,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2505,emit    , 2500,  0   , "<value>",           "# ")

# set

  addCase(2600,drop    , 2700,  0   , "set",               "# ")

# identity_insert

  addCase(2700,drop    , 2810,  UNSP, "transaction",       "# ")
  addCase(2700,drop    , 2905,  0   , "ansi_nulls",        "# ")
  addCase(2700,drop    , 2905,  INFO, "ansi_padding",      "# ")
  addCase(2700,drop    , 2900,  INFO, "quoted_identifier", "# ")
  addCase(2700,drop    , 2915,  0   , "dateformat",        "# ")
  addCase(2700,drop    , 2900,  0   , "nocount",           "# ")
  addCase(2700,drop    , 2910,  0   , "identity_insert",   "# ")
  addCase(2700,drop    , 2900,  INFO, "xact_abort",        "# ")
  addCase(2700,drop    , 2925,  UNSP, "ansi_warnings",     "# ")
  addCase(2700,drop    , 2900,  UNSP, "rowcount",          "# ")
  addCase(2700,drop    , 2900,  INFO, "ansi_null_default", "# ")
  addCase(2700,drop    , 2900,  INFO, "page_verify",       "# ")
  addCase(2700,drop    , 2900,  INFO, "concat_null_yields_null", "# ")
  addCase(2700,drop    , 2900,  INFO, "numeric_roundabort", "# ")
  addCase(2700,drop    , 2900,  INFO, "recursive_triggers", "# ")
  addCase(2700,drop    , 2900,  INFO, "auto_close",        "# ")
  addCase(2700,drop    , 2900,  INFO, "auto_shrink",       "# ")
  addCase(2700,drop    , 2900,  INFO, "auto_create_statistics", "# ")
  addCase(2700,drop    , 2900,  INFO, "auto_update_statistics", "# ")
  addCase(2700,drop    , 2900,  INFO, "cursor_close_on_commit", "# ")
  addCase(2700,drop    , 2900,  INFO, "cursor_default",    "# ")
  addCase(2700,drop    , 2900,  INFO, "arithignore",       "# ")
  addCase(2700,drop    , 2900,  INFO, "arithabort",        "# ")
  addCase(2700,drop    , 2900,  INFO, "recovery",          "# ")
  addCase(2700,repl    , 2705,  INFO, "read_write",        "owner to postgres")
  addCase(2700,repl    , 2705,  INFO, "multi_user",        "set owner to postgres")
  addCase(2700,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2700,emit    , 2710,  0   , "<value>",           "# ")

  addCase(2705,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2710,emit    , 2700,  0   , ".",                 "# ")
  addCase(2710,repl    , 2715,  0   , "=",                 ":=")
  addCase(2710,emit    , 2705,  0   , "off",               "# ")
  addCase(2710,emit    , 2705,  0   , "on",                "# ")
  addCase(2710,emit    , 2705,  0   , "checksum",          "# ")

  addCase(2715,callem  , 2720,  2725, "(",                 "# ")
  addCase(2715,call    , 1605,  0   , "case",              "# ")
  addCase(2715,call    , 1430,  0   , "dateadd",           "# ")
  addCase(2715,call    , 1430,  0   , "datediff",          "# ")
  addCase(2715,call    , 1430,  0   , "datepart",          "# ")
  addCase(2715,call    , 2740,  0   , "convert",           "# ")
  addCase(2715,call    , 2015,  0   , "cast",              "# ")
  addCase(2715,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2715,emit    , 2725,  0   , "<value>",           "# ")

  addCase(2720,call    , 1400,  2725, "select",            "# ")
  addCase(2720,call    , 2740,  2725, "convert",           "# ")
  addCase(2720,callem  , 2720,  2725, "(",                 "# ")
  addCase(2720,call    , 1605,  0   , "case",              "# ")
  addCase(2720,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2720,emit    , 2725,  0   , "<value>",           "# ")

  addCase(2725,callem  , 2715,  0   , "(",                 "# ")
  addCase(2725,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2725,emit    , 2715,  0   , ",",                 "# ")
  addCase(2725,emit    , 2715,  0   , ".",                 "# ")
  addCase(2725,emit    , 2715,  0   , "+",                 "# ")
  addCase(2725,emit    , 2715,  0   , "-",                 "# ")
  addCase(2725,emit    , 2715,  0   , "/",                 "# ")
  addCase(2725,emit    , 2715,  0   , "?",                 "# ")
  addCase(2725,emit    , 2715,  0   , "*",                 "# ")
  addCase(2725,emit    , 2715,  0   , "as",                "# ")
  addCase(2725,emit    , 2730,  0   , "from",              "# ")
  addCase(2725,emit    , 2715,  0   , "=",                 "# ")
  addCase(2725,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2725,emit    , 2725,  0   , "<value>",           "# ")

  addCase(2730,callem  , 2730,  0   , "(",                 "# ")
  addCase(2730,call    , 1400,  0   , "select",            "# ")
  addCase(2730,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2730,emit    , 2735,  0   , "<value>",           "# from table ")

  addCase(2735,emit    , 2730,  0   , ",",                 "# ")
  addCase(2735,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2735,emit    , 2735,  0   , "<value>",           "# table alias ")

  addCase(2740,repl    , 2745,  0   , "convert",           "cast")

  addCase(2745,frame   , 2750,  0   , "<any>",             "# stack frame")

  addCase(2750,callem  , 2755,  95  , "(",                 "# start bracket")

  addCase(2755,pushalt , 2760,  0   , "nvarchar",          "varchar")
  addCase(2755,pushalt , 2760,  0   , "uniqueidentifier",  "uuid")
  addCase(2755,pushalt , 2760,  0   , "bit",               "boolean")
  addCase(2755,pushalt , 2760,  0   , "datetime",          "date")
  addCase(2755,save    , 2760,  0   , "<value>",           "# ")

  addCase(2760,save    , 2765,  0   , "(",                 "# ")
  addCase(2760,drop    , 2780,  0   , ",",                 "# ")

  addCase(2765,save    , 2770,  0   , "<value>",           "# ")

  addCase(2770,save    , 2775,  0   , ")",                 "# ")

  addCase(2775,drop    , 2780,  0   , ",",                 "# ")

  addCase(2780,call    , 1400,  2795, "select",            "# value or function ")
  addCase(2780,call    , 2740,  2785, "convert",           "# ")
  addCase(2780,call    , 2015,  2785, "cast",              "# ")
  addCase(2780,callem  , 2780,  2785, "(",                 "# ")
  addCase(2780,emit    , 2785,  0   , "<value>",           "# ")

  addCase(2785,emit    , 2780,  0   , ".",                 "# inline arguments ")
  addCase(2785,callem  , 2800,  0   , "(",                 "# function ")
  addCase(2785,convbr  , 0   ,  0   , ")",                 "# closing bracket")
  addCase(2785,drop    , 2790,  0   , ",",                 "# extra parameter")
  addCase(2785,emit    , 2780,  0   , "?",                 "# ")
  addCase(2785,emit    , 2780,  0   , "/",                 "# ")
  addCase(2785,emit    , 2780,  0   , "*",                 "# ")
  addCase(2785,emit    , 2780,  0   , "%",                 "# ")
  addCase(2785,emit    , 2780,  0   , "+",                 "# ")
  addCase(2785,emit    , 2780,  0   , "-",                 "# ")

  addCase(2790,drop    , 2785,  UNSP, "<value>",           "# date format number")

  addCase(2795,skip    , 0   ,  0   , "<any>",             "# extra bracket for select")

  addCase(2800,call    , 1400,  2805, "select",            "# actual function ")
  addCase(2800,call    , 2740,  2805, "convert",           "# ")
  addCase(2800,call    , 1430,  2805, "dateadd",           "# ")
  addCase(2800,call    , 1430,  2805, "datepart",          "# ")
  addCase(2800,call    , 1430,  2805, "datediff",          "# ")
  addCase(2800,call    , 2015,  2805, "cast",              "# ")
  addCase(2800,callem  , 2800,  2805, "(",                 "# ")
  addCase(2800,emit    , 2805,  0   , "<value>",           "# ")

  addCase(2805,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(2805,callem  , 2800,  0   , "(",                 "# ")
  addCase(2805,emit    , 2800,  0   , ",",                 "# ")
  addCase(2805,emit    , 2800,  0   , ".",                 "# ")
  addCase(2805,emit    , 2800,  0   , "?",                 "# ")
  addCase(2805,emit    , 2800,  0   , "/",                 "# ")
  addCase(2805,emit    , 2800,  0   , "*",                 "# ")
  addCase(2805,emit    , 2800,  0   , "+",                 "# ")

  addCase(2810,isrt    , 2815,  0   , "set escape_string_warning = 0",   "############ set tran ")

  addCase(2815,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2815,drop    , 2815,  0   , "<value>",           "# ")

# ansi_padding

  addCase(2900,isrt    , 2930,  0   , "set escape_string_warning", "# catch all")

  addCase(2905,isrt    , 2930,  0   , "set transform_null_equals", "# ")

  addCase(2910,isrt    , 2945,  0   , "set escape_string_warning", "# ")

  addCase(2915,isrt    , 2930,  0   , "set datestyle",     "# ")

  addCase(2920,isrt    , 2925,  0   , "set escape_string_warning", "# ")

  addCase(2925,prtansi , 2930,  1   , "on",                "# ")
  addCase(2925,prtansi , 2930,  0   , "off",               "# ")

  addCase(2930,repl    , 2940,  0   , "on",                "= 1")
  addCase(2930,repl    , 2940,  0   , "off",               "= 0")
  addCase(2930,repl    , 2940,  0   , "mdy",               "to iso,mdy")
  addCase(2930,repl    , 2940,  0   , "global",            "= 0")
  addCase(2930,repl    , 2940,  0   , "simple",            "= 0")
  addCase(2930,repl    , 2940,  0   , "1",                 "=1")
  addCase(2930,repl    , 2940,  0   , "0",                 "=0")
  addCase(2930,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(2930,drop    , 2935,  0   , "<value>",           "# ")

  addCase(2935,isrt    , 2940,  0   , "=0",                "# ")

  addCase(2940,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(2945,drop    , 2930,  0   , "<value>",           "# ")

# while

  addCase(2990,emit    , 3000,  0   , "while",              "############ while ")

  addCase(3000,call    , 3025,  3005, "<any>",             "# ")

  addCase(3005,isrt    , 3010,  0   , "loop",              "# ")

  addCase(3010,trap    , 0   ,  3015, "<any>",             "# ")

  addCase(3015,isrt    , 3020,  0   , "end loop",          "# ")

  addCase(3020,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3025,callem  , 3025,  0   , "(",                 "# ")
  addCase(3025,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3025,drop    , 3030,  UNSP, "__fetch_status",    "# ")
  addCase(3025,emit    , 3040,  0   , "<value>",           "# ")

  addCase(3030,repl    , 3035,  0   , "=",                 "found ")
  addCase(3030,repl    , 3035,  0   , "<",                 "not found")

  addCase(3035,drop    , 3035,  0   , ">",                 "# <> ")
  addCase(3035,drop    , 3040,  0   , "0",                 "# ")
  addCase(3035,drop    , 3035,  0   , "-",                 "# ")
  addCase(3035,drop    , 3040,  0   , "1",                 "# ")

  addCase(3040,emit    , 3045,  0   , "=",                 "# ")
  addCase(3040,emit    , 3025,  0   , ",",                 "# ")
  addCase(3040,callem  , 3025,  0   , "(",                 "# ")
  addCase(3040,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3040,emit    , 3045,  0   , "<",                 "# ")
  addCase(3040,emit    , 3045,  0   , ">",                 "# ")
  addCase(3040,emit    , 3040,  0   , "is",                "# ")
  addCase(3040,emit    , 3040,  0   , "not",               "# ")
  addCase(3040,emit    , 3040,  0   , "null",              "# ")
  addCase(3040,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3045,emit    , 3045,  0   , "=",                 "# ")
  addCase(3045,emit    , 3045,  0   , ">",                 "# ")
  addCase(3045,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3045,emit    , 3040,  0   , "<value>",           "# ")

# execute

  addCase(3100,repl    , 3105,  0   , "exec",              "perform")
  addCase(3100,repl    , 3105,  0   , "execute",           "perform")

  addCase(3105,emit    , 3110,  0   , "(",                 "# ")
  addCase(3105,emit    , 3120,  0   , "sp_executesql",     "# ")
  addCase(3105,drop    , 3105,  UNSP, "sys",               "# ")
  addCase(3105,drop    , 3105,  0   , ".",                 "# ")
  addCase(3105,repl    , 3165,  UNSP, "sp_addextendedproperty", "0")
  addCase(3105,procref , 3140,  0   , "<value>",           "# function exec")

  addCase(3110,emit    , 3115,  0   , "<value>",           "# string exec")

  addCase(3115,emit    , 3110,  0   , "+",                 "# ")
  addCase(3115,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(3120,isrt    , 3125,  0   , "(",                 "# ")

  addCase(3125,drop    , 3125,  0   , "_statement",        "# ")
  addCase(3125,emit    , 3130,  0   , "_sql",              "# ")
  addCase(3125,drop    , 3125,  0   , "=",                 "# ")
  addCase(3125,dump    , 3130,  0   , "<value>",           "# string exec")

  addCase(3130,isrt    , 3135,  0   , ")",                 "# ")

  addCase(3135,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3140,emit    , 3105,  0   , "=",                 "# ")
  addCase(3140,emit    , 3105,  0   , ".",                 "# ")
  addCase(3140,procref , 3142,  1   , "<any>",             "# ")

  addCase(3142,repl    , 3145,  0   , "go",                ")")
  addCase(3142,drop    , 3150,  0   , "(",                 "# ")
  addCase(3142,jump    , 3150,  0   , "<any>",             "# ")

  addCase(3145,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3150,emit    , 3155,  0   , "<value>",           "# ")

  addCase(3155,drop    , 3155,  UNSP, "output",            "# ")
  addCase(3155,emit    , 3150,  0   , ",",                 "# ")
  addCase(3155,emit    , 3150,  0   , "=",                 "# ")
  addCase(3155,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3155,isrt    , 3160,  0   , ")",                 "# ")

  addCase(3160,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3165,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3165,drop    , 3165,  0   , "<value>",           "# ")

# insert

  addCase(3190,emit    , 3200,  0   , "insert",              "############ insert")

  addCase(3200,emit    , 3205,  0   , "into",              "############ insert into ")
  addCase(3200,call    , 3255,  0   , "top",               "# unsupported")
  addCase(3200,isrt    , 3205,  MSNG, "into",              "# missing into")

  addCase(3205,drop    , 3205,  SERR, ".",                 "############ insert table")
  addCase(3205,tabtest , 3210,  0   , "<value>",           "# table name ")

  addCase(3210,emit    , 3225,  0   , "values",            "############ values ")
  addCase(3210,emit    , 3205,  0   , ".",                 "# schema.table")
  addCase(3210,call    , 1400,  3230, "select",            "# insert select")
  addCase(3210,callem  , 3215,  3225, "(",                 "# column list")
  addCase(3210,repl    , 3235,  0   , "exec",              "select")

  addCase(3215,drop    , 3215,  SERR, ".",                 "############ column list")
  addCase(3215,repl    , 3220,  0   , "user",              "\"user\"")
  addCase(3215,repl    , 3220,  0   , "offset",            "\"offset\"")
  addCase(3215,emit    , 3220,  0   , "<value>",           "# col name")

  addCase(3220,emit    , 3215,  0   , ",",                 "# list")
  addCase(3220,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(3225,emit    , 3225,  0   , "-",                 "############ value list")
  addCase(3225,call    , 1400,  3230, "select",            "# ")
  addCase(3225,drop    , 3225,  SERR, ".",                 "# ")
  addCase(3225,callem  , 3225,  3230, "(",                 "# ")
  addCase(3225,emit    , 3225,  0   , "=",                 "# >= ")
  addCase(3225,repl    , 3235,  0   , "exec",              "select")
  addCase(3225,call    , 1605,  3230, "case",              "# ")
  addCase(3225,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3225,escape  , 3230,  0   , "<value>",           "# ")

  addCase(3230,emit    , 3225,  0   , ",",                 "############ value operator")
  addCase(3230,emit    , 3225,  0   , "*",                 "# ")
  addCase(3230,emit    , 3225,  0   , "/",                 "# ")
  addCase(3230,emit    , 3225,  0   , "?",                 "# ")
  addCase(3230,emit    , 3225,  0   , "+",                 "# ")
  addCase(3230,emit    , 3225,  0   , "-",                 "# ")
  addCase(3230,emit    , 3225,  0   , ".",                 "# ")
  addCase(3230,emit    , 3225,  0   , ">",                 "# ")
  addCase(3230,emit    , 3225,  0   , "<",                 "# ")
  addCase(3230,emit    , 3225,  0   , "=",                 "# ")
  addCase(3230,emit    , 3225,  0   , "and",               "# ")
  addCase(3230,emit    , 3225,  0   , "as",                "# ")
  addCase(3230,emit    , 3225,  0   , "in",                "# ")
  addCase(3230,callem  , 3225,  0   , "(",                 "# function call")
  addCase(3230,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3230,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3235,emit    , 3240,  0   , "<value>",           "############ exec function")

  addCase(3240,emit    , 3235,  0   , ".",                 "############ exec parms ")
  addCase(3240,emit    , 3245,  0   , "(",                 "# ")
  addCase(3240,isrt    , 3245,  MSNG, "(",                 "# ")

  addCase(3245,emit    , 3250,  0   , "<value>",           "# ")

  addCase(3250,emit    , 3245,  0   , ",",                 "############ exec list")
  addCase(3250,emit    , 3270,  0   , ")",                 "# ")
  addCase(3250,isrt    , 3270,  MSNG, ")",                 "############ missing ")

  addCase(3255,drop    , 3260,  0   , "top",               "############ top list ")

  addCase(3260,drop    , 3265,  0   , "(",                 "# ")

  addCase(3265,drop    , 3270,  0   , ")",                 "# ")
  addCase(3265,drop    , 3265,  0   , "<value>",           "# ")

  addCase(3270,skip    , 0   ,  0   , "<any>",             "# ")

# return

  addCase(3290,emit    , 3300,  0   , "return",            "############ return ")

  addCase(3300,drop    , 3315,  0   , "select",            "# ")
  addCase(3300,call    , 2740,  3325, "convert",           "# ")
  addCase(3300,call    , 1430,  3325, "datepart",          "# ")
  addCase(3300,call    , 3305,  3325, "(",                 "# ")
  addCase(3300,emit    , 3300,  0   , "-",                 "# ")
  addCase(3300,prmtest , 0   ,  1   , "<key>",             "# ")
  addCase(3300,prmtest , 3325,  0   , "<value>",           "# ")

  addCase(3305,drop    , 3310,  0   , "(",                 "# ")

  addCase(3310,repl    , 1405,  UNSP, "select",            "query select (select ")
  addCase(3310,isrt    , 3300,  0   , "(",                 "# ")

  addCase(3315,isrt    , 3320,  0   , "query select",      "# ")

  addCase(3320,call    , 1405,  3325, "<any>",             "# ")

  addCase(3325,rtnem   , 0   ,  0   , ")",                 "# return expression")
  addCase(3325,callem  , 3300,  0   , "(",                 "# ")
  addCase(3325,emit    , 3300,  0   , ",",                 "# ")
  addCase(3325,emit    , 3300,  0   , ".",                 "# ")
  addCase(3325,emit    , 3300,  0   , "/",                 "# ")
  addCase(3325,emit    , 3300,  0   , "?",                 "# ")
  addCase(3325,emit    , 3300,  0   , "+",                 "# ")
  addCase(3325,emit    , 3300,  0   , "-",                 "# ")
  addCase(3325,emit    , 3300,  0   , "*",                 "# ")
  addCase(3325,emit    , 3300,  0   , "%",                 "# ")
  addCase(3325,emit    , 3300,  0   , "=",                 "# ")
  addCase(3325,emit    , 3300,  0   , "or",                "# ")
  addCase(3325,emit    , 3300,  0   , "and",               "# ")
  addCase(3325,emit    , 3325,  0   , "is",                "# ")
  addCase(3325,emit    , 3325,  0   , "not",               "# ")
  addCase(3325,emit    , 3325,  0   , "null",              "# ")
  addCase(3325,skip    , 0   ,  0   , "<any>",             "# ")

# update

  addCase(3390,emit    , 3400,  0   , "update",           "############ update")

  addCase(3400,emit    , 3405,  0   , "<value>",           "# table")

  addCase(3405,emit    , 3400,  0   , ".",                 "# ")
  addCase(3405,emit    , 3410,  0   , "set",               "# ")

  addCase(3410,repl    , 3415,  0   , "user",              "\"user\"")
  addCase(3410,repl    , 3415,  0   , "offset",            "\"offset\"")
  addCase(3410,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3410,colsym  , 3415,  0   , "<symbol>",          "# ")
  addCase(3410,emit    , 3415,  0   , "<value>",           "# ")

  addCase(3415,emit    , 3410,  0   , ".",                 "# ")
  addCase(3415,emit    , 3420,  0   , "=",                 "# ")
  addCase(3415,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3415,skip    , 0   ,  0   , "<key>",             "# ")

  addCase(3420,callem  , 3425,  0   , "(",                 "# ")
  addCase(3420,call    , 1605,  3435, "case",              "# ")
  addCase(3420,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3420,emit    , 3435,  0   , "<value>",           "# set value")

  addCase(3425,call    , 1400,  3435, "select",            "# update select ")
  addCase(3425,emit    , 3435,  0   , "<value>",           "# ")

  addCase(3430,emit    , 3450,  0   , "on",                "############ from alias ")
  addCase(3430,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3430,emit    , 3430,  0   , "<value>",           "# alias")

  addCase(3435,emit    , 3410,  0   , ",",                 "############ set value operator ")
  addCase(3435,emit    , 3420,  0   , ".",                 "# ")
  addCase(3435,emit    , 3420,  0   , "+",                 "# ")
  addCase(3435,emit    , 3420,  0   , "-",                 "# ")
  addCase(3435,emit    , 3420,  0   , "/",                 "# ")
  addCase(3435,emit    , 3420,  0   , "?",                 "# ")
  addCase(3435,emit    , 3420,  0   , "*",                 "# ")
  addCase(3435,emit    , 3440,  0   , "from",              "# ")
  addCase(3435,emit    , 3450,  0   , "where",             "# ")
  addCase(3435,callem  , 3440,  0   , "(",                 "# ")
  addCase(3435,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3435,emit    , 3450,  0   , "on",                "# ")
  addCase(3435,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3435,emit    , 3435,  0   , "<value>",           "# ")

  addCase(3440,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3440,callem  , 3440,  3445, "(",                 "# ")
  addCase(3440,call    , 1400,  3435, "select",            "# ")
  addCase(3440,emit    , 3440,  0   , "-",                 "# ")
  addCase(3440,emit    , 3445,  0   , "<value>",           "# function parms")

  addCase(3445,emit    , 3440,  0   , ",",                 "# ")
  addCase(3445,emit    , 3440,  0   , ".",                 "# ")
  addCase(3445,emit    , 3440,  0   , "/",                 "# ")
  addCase(3445,emit    , 3440,  0   , "?",                 "# ")
  addCase(3445,emit    , 3440,  0   , "?",                 "# ")
  addCase(3445,emit    , 3440,  0   , "+",                 "# ")
  addCase(3445,emit    , 3480,  0   , "inner",             "# ")
  addCase(3445,emit    , 3440,  0   , "-",                 "# ")
  addCase(3445,emit    , 3440,  0   , "*",                 "# ")
  addCase(3445,emit    , 3440,  0   , "as",                "# ")
  addCase(3445,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3445,callem  , 3440,  3445, "(",                 "# ")
  addCase(3445,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3445,emit    , 3445,  0   , "<value>",           "# table alias")

  addCase(3450,emit    , 3450,  0   , "current",           "# ")
  addCase(3450,emit    , 3450,  0   , "of",                "# ")
  addCase(3450,emit    , 1405,  0   , "select",            "# ")
  addCase(3450,emit    , 3450,  0   , "not",               "# ")
  addCase(3450,callem  , 3450,  3475, "(",                 "# ")
  addCase(3450,callem  , 1405,  0   , "(",                 "# ")
  addCase(3450,call    , 1605,  0   , "case",              "# ")
  addCase(3450,call    , 2740,  3455, "convert",           "# ")
  addCase(3450,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3450,emit    , 3455,  0   , "<value>",           "# ")

  addCase(3455,emit    , 3450,  0   , ".",                 "# ")
  addCase(3455,emit    , 3450,  0   , ",",                 "# ")
  addCase(3455,emit    , 3450,  0   , "like",              "# ")
  addCase(3455,emit    , 3450,  0   , "as",                "# ")
  addCase(3455,emit    , 3450,  0   , "or",                "# ")
  addCase(3455,emit    , 3465,  0   , "in",                "# ")
  addCase(3455,emit    , 3455,  0   , "is",                "# ")
  addCase(3455,emit    , 3455,  0   , "not",               "# ")
  addCase(3455,emit    , 3450,  0   , "and",               "# ")
  addCase(3455,emit    , 3455,  0   , "exists",            "# ")
  addCase(3455,emit    , 3450,  0   , "between",           "# ")
  addCase(3455,emit    , 3475,  0   , "null",              "# ")
  addCase(3455,emit    , 3460,  0   , "=",                 "# ")
  addCase(3455,emit    , 3450,  0   , "+",                 "# ")
  addCase(3455,callem  , 3450,  0   , "(",                 "# ")
  addCase(3455,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3455,emit    , 3460,  0   , "<",                 "# ")
  addCase(3455,emit    , 3460,  0   , ">",                 "# ")
  addCase(3455,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3460,callem  , 3460,  3475, "(",                 "# ")
  addCase(3460,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3460,emit    , 3450,  0   , "and",               "# ")
  addCase(3460,call    , 2740,  0   , "convert",           "# ")
  addCase(3460,emit    , 3460,  0   , "=",                 "# ")
  addCase(3460,emit    , 3460,  0   , "-",                 "# ")
  addCase(3460,emit    , 3460,  0   , ">",                 "# ")
  addCase(3460,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3460,emit    , 3475,  0   , "<value>",           "# ")

  addCase(3465,callem  , 3465,  3475, "(",                 "# in")
  addCase(3465,call    , 1400,  3475, "select",            "# ")
  addCase(3465,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3465,emit    , 3470,  0   , "<value>",           "# ")

  addCase(3470,emit    , 3465,  0   , ",",                 "# ")
  addCase(3470,rtnem   , 0   ,  0   , ")",                 "# ")

  addCase(3475,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3475,emit    , 3450,  0   , "and",               "# ")
  addCase(3475,emit    , 3450,  0   , "where",             "# ")
  addCase(3475,emit    , 3450,  0   , "or",                "# ")
  addCase(3475,emit    , 3480,  0   , "inner",             "# ")
  addCase(3475,emit    , 3460,  0   , ".",                 "# ")
  addCase(3475,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3480,emit    , 3480,  0   , "join",              "# ")
  addCase(3480,emit    , 3450,  0   , "on",                "# ")
  addCase(3480,emit    , 3480,  0   , "<value>",           "# ")

# use

  addCase(3500,drop    , 3505,  UNSP, "use",               "# ")

  addCase(3505,drop    , 3510,  0   , "<value>",           "# ")

  addCase(3510,isrt    , 3515,  0   , "null",              "# ")

  addCase(3515,skip    , 0   ,  0   , "<any>",             "# ")

# begin

  addCase(3600,drop    , 3605,  0   , "begin",             "# ")

  addCase(3605,repl    , 0   ,  0   , "transaction",       "null;")
  addCase(3605,repl    , 0   ,  0   , "tran",              "null;")
  addCase(3605,isrt    , 3610,  0   , "begin ",            "# ")

  addCase(3610,begsta  , 0   ,  0   , "<any>",             "# ")

# end

  addCase(3700,emit    , 3705,  0   , "end",               "# This will be end ")

  addCase(3705,begend  , 3710,  0   , "<any>",             "# End of begin block")

  addCase(3710,skip    , 0   ,  0   , "<any>",             "")

# alter

  addCase(3800,drop    , 3805,  0   , "alter",             "alter table")

  addCase(3805,repl    , 3810,  0   , "table",             "alter table")
  addCase(3805,repl    , 4185,  0   , "function",          "drop function")
  addCase(3805,repl    , 4185,  0   , "procedure",         "drop function")
  addCase(3805,repl    , 4255,  0   , "trigger",           "drop trigger if exists")
  addCase(3805,repl    , 4315,  0   , "database",          "alter database")

  addCase(3810,emit    , 3815,  0   , "<value>",           "# alter table")

  addCase(3815,emit    , 3810,  0   , ".",                 "# ")
  addCase(3815,drop    , 3830,  0   , "with",              "# ")
  addCase(3815,drop    , 3830,  0   , "check",             "# ")
  addCase(3815,emit    , 3815,  0   , "constraint",        "# ")
  addCase(3815,drop    , 3895,  0   , "add",               "# ")
  addCase(3815,emit    , 3815,  0   , "drop",              "# ")
  addCase(3815,emit    , 3825,  0   , "alter",             "# ")
  addCase(3815,emit    , 3820,  0   , "column",            "# ")
  addCase(3815,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3815,emit    , 3845,  0   , "<value>",           "# ")

  addCase(3820,emit    , 3840,  0   , "<value>",           "# alter column  ")

  addCase(3825,emit    , 4205,  0   , "column",            "# alter column ")

  addCase(3830,drop    , 3815,  0   , "check",             "# ")
  addCase(3830,drop    , 3815,  UNSP, "nocheck",           "# ")
  addCase(3830,repl    , 3835,  0   , "constraint",        "owner to postgres")

  addCase(3835,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3835,drop    , 3840,  0   , "<value>",           "# ")

  addCase(3840,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3845,emit    , 3845,  0   , "with",              "# ")
  addCase(3845,emit    , 3845,  0   , "check",             "# ")
  addCase(3845,emit    , 3845,  0   , "add",               "# ")
  addCase(3845,emit    , 3850,  0   , "constraint",        "# ")
  addCase(3845,emit    , 3945,  0   , "column",            "# ")
  addCase(3845,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3850,emit    , 3855,  0   , "<value>",           "# constraint")

  addCase(3855,emit    , 3855,  0   , "primary",           "# ")
  addCase(3855,emit    , 3855,  0   , "foreign",           "# ")
  addCase(3855,drop    , 3855,  0   , "clustered",         "# ")
  addCase(3855,drop    , 3855,  0   , "nonclustered",      "# ")
  addCase(3855,emit    , 3855,  0   , "unique",            "# ")
  addCase(3855,drop    , 3855,  0   , "asc",               "# ")
  addCase(3855,call    , 1335,  0   , "with",              "# unsupported")
  addCase(3855,emit    , 3860,  0   , "default",           "# ")
  addCase(3855,emit    , 3855,  0   , "key",               "# ")
  addCase(3855,callem  , 3855,  0   , "(",                 "# ")
  addCase(3855,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3855,emit    , 3880,  0   , "references",        "# ")
  addCase(3855,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3855,emit    , 3855,  0   , "<value>",           "# ")

  addCase(3860,emit    , 3865,  0   , "(",                 "# default")
  addCase(3860,emit    , 3860,  0   , ")",                 "# ")
  addCase(3860,emit    , 3865,  0   , "for",               "# ")
  addCase(3860,emit    , 3870,  0   , "1",                 "# ")
  addCase(3860,emit    , 3870,  0   , "0",                 "# ")
  addCase(3860,emit    , 3845,  0   , ",",                 "# ")
  addCase(3860,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3865,emit    , 3865,  0   , "(",                 "# default")
  addCase(3865,emit    , 3865,  0   , "-",                 "# ")
  addCase(3865,emit    , 3870,  0   , "<value>",           "# ")

  addCase(3870,emit    , 3870,  0   , ")",                 "# ")
  addCase(3870,emit    , 3870,  0   , "(",                 "# ")
  addCase(3870,emit    , 3970,  0   , ",",                 "# ")
  addCase(3870,emit    , 3875,  0   , "for",               "# ")
  addCase(3870,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3875,emit    , 3860,  0   , "<value>",           "# ")

  addCase(3880,emit    , 3885,  0   , "<value>",           "# references")

  addCase(3885,emit    , 3890,  0   , ",",                 "# ")
  addCase(3885,emit    , 3880,  0   , ".",                 "# ")
  addCase(3885,callem  , 3890,  0   , "(",                 "# ")
  addCase(3885,emit    , 3885,  0   , "pkey",              "# ")
  addCase(3885,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3885,emit    , 3885,  0   , "on",                "# ")
  addCase(3885,emit    , 3885,  0   , "update",            "# ")
  addCase(3885,emit    , 3885,  0   , "delete",            "# ")
  addCase(3885,emit    , 3885,  0   , "cascade",           "# ")
  addCase(3885,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3890,emit    , 3885,  0   , "<value>",           "# references")

  addCase(3895,drop    , 3900,  0   , "constraint",        "# add constraint")
  addCase(3895,drop    , 4000,  0   , "default",           "# add default")
  addCase(3895,isrt    , 3945,  0   , "add",               "# ")

  addCase(3900,save    , 3905,  0   , "<value>",           "# ")

  addCase(3905,drop    , 3910,  0   , "default",           "# ")
  addCase(3905,jump    , 3975,  0   , "<any>",             "# ")

  addCase(3910,clear   , 3915,  0   , "<any>",             "# ")

  addCase(3915,drop    , 3920,  0   , "for",               "# ")
  addCase(3915,save    , 3915,  0   , "<value>",           "# ")

  addCase(3920,isrt    , 3925,  0   , "alter column",      "# ")

  addCase(3925,emit    , 3930,  0   , "<value>",           "# ")

  addCase(3930,isrt    , 3935,  0   , "set default",       "# ")

  addCase(3935,popall  , 3940,  0   , "<any>",             "# ")

  addCase(3940,emit    , 3895,  0   , ",",                 "# ")
  addCase(3940,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3945,emit    , 3845,  0   , ",",                 "# ")
  addCase(3945,drop    , 4000,  0   , "default",           "# ")
  addCase(3945,repl    , 3950,  0   , "user",              "\"user\"")
  addCase(3945,repl    , 3950,  0   , "offset",            "\"offset\"")
  addCase(3945,emit    , 3985,  0   , "primary",           "# primary key")
  addCase(3945,repl    , 3985,  0   , "foreign",           "foreign")
  addCase(3945,repl    , 1125,  0   , "check",             "check")
  addCase(3945,repl    , 3990,  0   , "unique",            "unique")
  addCase(3945,emit    , 3950,  0   , "<value>",           "# add column")

  addCase(3950,repl    , 3955,  0   , "uniqueidentifier",  "uuid")
  addCase(3950,repl    , 3955,  0   , "nvarchar",          "varchar")
  addCase(3950,repl    , 3955,  0   , "ntext",             "text")
  addCase(3950,repl    , 3955,  0   , "datetime",          "timestamp")
  addCase(3950,repl    , 3955,  0   , "money",             "numeric(19,4)")
  addCase(3950,repl    , 3955,  0   , "bit",               "boolean")
  addCase(3950,emit    , 3955,  0   , "<value>",           "# add type")

  addCase(3955,repl    , 3955,  0   , "bit",               "boolean")
  addCase(3955,emit    , 3955,  0   , "not",               "# ")
  addCase(3955,emit    , 3955,  0   , "null",              "# ")
  addCase(3955,emit    , 3965,  0   , "default",           "# ")
  addCase(3955,repl    , 3965,  0   , "identity",          "default identity")
  addCase(3955,drop    , 3960,  UNSP, "collate",           "# ")
  addCase(3955,callem  , 3965,  0   , "(",                 "# ")
  addCase(3955,emit    , 3965,  0   , "unique",            "# ")
  addCase(3955,emit    , 3850,  0   , "constraint",        "# ")
  addCase(3955,emit    , 3895,  0   , ",",                 "# ")
  addCase(3955,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(3960,drop    , 3955,  0   , "<value>",           "# collate value ")

  addCase(3965,callem  , 3965,  0   , "(",                 "# ")
  addCase(3965,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(3965,emit    , 3955,  0   , "not",               "# ")
  addCase(3965,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(3965,emit    , 3965,  0   , "<value>",           "# ")

  addCase(3970,emit    , 3945,  0   , "add",               "# ")
  addCase(3970,isrt    , 3945,  MSNG, "add",               "# ")

  addCase(3975,isrt    , 3980,  0   , "add constraint",    "# ")

  addCase(3980,load    , 3855,  0   , "<any>",             "# ")

  addCase(3985,emit    , 3995,  0   , "key",               "# primary key")
  addCase(3985,isrt    , 3995,  0   , "key",               "# missing key")

  addCase(3990,drop    , 3995,  0   , "key",               "# unique key")
  addCase(3990,callem  , 3965,  3965, "(",                 "# unique key")

  addCase(3995,drop    , 3965,  UNSP, "nonclustered",      "# ")
  addCase(3995,callem  , 3965,  3965, "(",                 "# ")

  addCase(4000,isrt    , 4005,  0   , "alter column",      "# new default ")

  addCase(4005,drop    , 4010,  0   , "for",               "# ")
  addCase(4005,save    , 4005,  0   , "<value>",           "# ")

  addCase(4010,emit    , 4015,  0   , "<value>",           "# colname ")

  addCase(4015,isrt    , 4020,  0   , "set default",       "# ")

  addCase(4020,popall  , 4025,  0   , "<any>",             "# ")

  addCase(4025,skip    , 0   ,  0   , "<any>",             "# ")

# delete

  addCase(4090,emit    , 4100,  0   , "delete",              "############ delete ")

  addCase(4100,emit    , 4105,  0   , "from",              "# ")
  addCase(4100,drop    , 4100,  UNSP, "<value>",           "# ")

  addCase(4105,emit    , 4110,  0   , "<value>",           "# table")

  addCase(4110,emit    , 4105,  0   , ".",                 "# ")
  addCase(4110,emit    , 4110,  0   , "inner",             "# ")
  addCase(4110,emit    , 4110,  0   , "left",              "# ")
  addCase(4110,emit    , 4110,  0   , "outer",             "# ")
  addCase(4110,emit    , 4105,  0   , "join",              "# ")
  addCase(4110,emit    , 4105,  0   , "on",                "# ")
  addCase(4110,emit    , 4140,  0   , "where",             "# ")
  addCase(4110,emit    , 4105,  0   , "=",                 "# ")
  addCase(4110,repl    , 4115,  0   , "from",              "using")
  addCase(4110,repl    , 4110,  0   , ",",                 "using")
  addCase(4110,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(4110,emit    , 4110,  0   , "<value>",           "# alias")

  addCase(4115,emit    , 4120,  0   , "<value>",           "# ")

  addCase(4120,emit    , 4120,  UNSP, "left",              "# ")
  addCase(4120,emit    , 4125,  0   , "inner",             "# ")
  addCase(4120,emit    , 4125,  UNSP, "outer",             "# ")

  addCase(4125,emit    , 4130,  0   , "join",              "# ")

  addCase(4130,emit    , 4135,  0   , "<value>",           "# using table")

  addCase(4135,emit    , 4140,  0   , "on",                "# ")
  addCase(4135,drop    , 4135,  0   , "as",                "# ")
  addCase(4135,emit    , 4135,  0   , "<value>",           "# alias")

  addCase(4140,emit    , 4140,  0   , "=",                 "# ")
  addCase(4140,callem  , 4140,  4170, "(",                 "# ")
  addCase(4140,call    , 1400,  0   , "select",            "# ")
  addCase(4140,emit    , 4140,  0   , ">",                 "# ")
  addCase(4140,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(4140,emit    , 4145,  0   , "<value>",           "# ")

  addCase(4145,emit    , 4140,  0   , ".",                 "# ")
  addCase(4145,emit    , 4140,  0   , "=",                 "# ")
  addCase(4145,emit    , 4140,  0   , ">",                 "# ")
  addCase(4145,emit    , 4140,  0   , "<",                 "# ")
  addCase(4145,callem  , 4140,  4145, "(",                 "# ")
  addCase(4145,repl    , 4140,  0   , "where",             "and")
  addCase(4145,emit    , 4145,  0   , "not",               "# ")
  addCase(4145,emit    , 4145,  0   , "is",                "# ")
  addCase(4145,emit    , 4145,  0   , "null",              "# ")
  addCase(4145,emit    , 4140,  0   , "like",              "# ")
  addCase(4145,emit    , 4175,  0   , "in",                "# ")
  addCase(4145,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(4145,emit    , 4140,  0   , "and",               "# ")
  addCase(4145,drop    , 4125,  0   , "inner",             "# ")
  addCase(4145,emit    , 4140,  0   , "or",                "# ")
  addCase(4145,drop    , 4145,  UNSP, "on",                "# ")
  addCase(4145,drop    , 4150,  UNSP, "left",              "# ")
  addCase(4145,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(4145,emit    , 4145,  0   , "<value>",           "# ")

  addCase(4150,drop    , 4155,  UNSP, "outer",             "# ")

  addCase(4155,drop    , 4160,  0   , "join",              "# ")

  addCase(4160,drop    , 4165,  0   , "<value>",           "# ")

  addCase(4165,isrt    , 4145,  0   , "and",               "# ")

  addCase(4170,emit    , 4140,  0   , "and",               "# ")
  addCase(4170,emit    , 4170,  0   , "is",                "# ")
  addCase(4170,emit    , 4170,  0   , "null",              "# ")
  addCase(4170,emit    , 4140,  0   , "or",                "# ")
  addCase(4170,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(4170,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(4175,callem  , 4175,  4180, "(",                 "# ")
  addCase(4175,call    , 1400,  4180, "select",            "# ")
  addCase(4175,emit    , 4180,  0   , "<value>",           "# ")

  addCase(4180,emit    , 4140,  0   , "and",               "# ")
  addCase(4180,emit    , 4140,  0   , "or",                "# ")
  addCase(4180,rtnem   , 0   ,  0   , ")",                 "# ")
  addCase(4180,skip    , 0   ,  0   , "<key>",             "# ")
  addCase(4180,emit    , 4180,  0   , "<value>",           "# ")

  addCase(4185,procset , 4190,  0   , "<value>",           "# ")

  addCase(4190,procsig , 4195,  0   , "<any>",             "# ")

  addCase(4195,isrt    , 4200,  0   , "; create function ", "# ")

  addCase(4200,procget , 1215,  0   , "<any>",             "# ")

  addCase(4205,colset  , 4210,  0   , "<value>",           "# ")

  addCase(4210,emit    , 4215,  0   , "type",              "# ")
  addCase(4210,isrt    , 4215,  0   , "type",              "# ")

  addCase(4215,emit    , 4215,  0   , "int",               "# ")
  addCase(4215,repl    , 4215,  0   , "uniqueidentifier",  "uuid")
  addCase(4215,repl    , 4215,  0   , "money",             "numeric(19,4)")
  addCase(4215,repl    , 4215,  0   , "bit",               "boolean")
  addCase(4215,emit    , 4215,  0   , "varchar",           "# ")
  addCase(4215,repl    , 4215,  0   , "nvarchar",          "varchar")
  addCase(4215,repl    , 4215,  0   , "datetime",          "timestamp")
  addCase(4215,callem  , 3965,  0   , "(",                 "# ")
  addCase(4215,drop    , 4220,  0   , "not",               "# not null")
  addCase(4215,drop    , 4240,  0   , "null",              "# null")
  addCase(4215,skip    , 0   ,  0   , "<any>",             "# ")

  addCase(4220,isrt    , 4225,  0   , ",alter column",     "# ")

  addCase(4225,colget  , 4230,  0   , "<any>",             "# ")

  addCase(4230,isrt    , 4235,  0   , "set not",           "# ")

  addCase(4235,emit    , 4215,  0   , "null",              "# ")

  addCase(4240,isrt    , 4245,  0   , ",alter column",     "# ")

  addCase(4245,colget  , 4250,  0   , "<any>",             "# ")

  addCase(4250,isrt    , 4215,  0   , "drop not null",     "# ")

  addCase(4255,procset , 4260,  0   , "<value>",           "# Trigger")

  addCase(4260,isrt    , 4265,  0   , "on",                "# ")

  addCase(4265,trigprt , 4270,  0   , "<any>",             "# ")

  addCase(4270,isrt    , 4275,  0   , ";drop rule if exists", "# ")

  addCase(4275,procget , 4280,  0   , "<any>",             "# ")

  addCase(4280,isrt    , 4285,  0   , "on",                "# ")

  addCase(4285,trigprt , 4290,  0   , "<any>",             "# ")

  addCase(4290,isrt    , 4295,  0   , ";drop function",    "# ")

  addCase(4295,procget , 4300,  0   , "<any>",             "# ")

  addCase(4300,procsig , 4305,  0   , "<any>",             "# ")

  addCase(4305,isrt    , 4310,  0   , ";create",           "# ")

  addCase(4310,jump    , 1305,  0   , "<any>",             "# ")

  addCase(4315,emit    , 4320,  0   , "<value>",           "# Database")

  addCase(4320,drop    , 2700,  0   , "set",               "# ")
  addCase(4320,drop    , 4355,  UNSP, "modify",            "# ")

  addCase(4325,emit    , 4325,  0   , ".",                 "# ")
  addCase(4325,emit    , 4330,  0   , "<value>",           "# ")

  addCase(4330,drop    , 4325,  UNSP, "as",                "# ")
  addCase(4330,emit    , 4335,  0   , "where",             "# ")

  addCase(4335,emit    , 4335,  0   , "(",                 "# ")
  addCase(4335,emit    , 4340,  0   , "<value>",           "# ")

  addCase(4340,emit    , 4335,  0   , ".",                 "# ")
  addCase(4340,emit    , 4345,  0   , "=",                 "# ")
  addCase(4340,emit    , 4345,  0   , "like",              "# ")
  addCase(4340,emit    , 4345,  0   , "<",                 "# ")

  addCase(4345,emit    , 4345,  0   , ">",                 "# ")
  addCase(4345,lower   , 4350,  0   , "<value>",           "# ")

  addCase(4350,emit    , 4335,  0   , "and",               "# ")
  addCase(4350,emit    , 4335,  0   , "or",                "# ")
  addCase(4350,rtnem   , 4335,  0   , ")",                 "# ")

  addCase(4355,drop    , 4360,  0   , "file",              "# Modify file")

  addCase(4360,drop    , 4365,  0   , "(",                 "# ")

  addCase(4365,drop    , 4370,  0   , ")",                 "# drop to bracket")
  addCase(4365,drop    , 4365,  0   , "<any>",             "# ")

  addCase(4370,isrt    , 0   ,  0   , "set owner to postgres;", "# ")

##########################################################################################

#
# Main program
#
def main() :
  global debug
  global trace
  global total_errors
  global statement_table
  global state_errors
  global error_log
  global current_statement
  global current_begin
  global casedir
  filename = None
  current_begin = begin()	
  try :
    filename = sys.argv[1]
  except IndexError :
    print("Usage: %s <FILENAME> | build [ trace | debug ]" % sys.argv[0])
    sys.exit(0)
  try :
    if sys.argv[1] == "build" :
        addAllCases() 
        printCases()
        return
    if sys.argv[1] == "print" :
        addAllCases() 
        printRules()
        return
    if sys.argv[2] == "debug" :
        debug = 1
        trace = 1
    if sys.argv[2] == "trace" :
        trace = 1
  except IndexError :
    debug = 0
    trace = 0
  error_log = open('error.log','w')
  addAllCases() 
  readIntRets()
  readFuncDB()
  readTrigDB()
  readTabDB()
  readColDB()
  readProcrefDB()
  readProcretDB()
  
  for keycase in cases :
    if keycase.level == 0 :
      statement_table[keycase.token] = 0
  print("create or replace function msload ()")
  print("returns void as $main$ begin")
  print()
  processFile(filename)
  print()
  print("end; $main$ language plpgsql;")
#
# Print out a block of stats 
#
  total = 0
  for key in statement_table :
        total = total + statement_table[key]
  printMessage("STATEMENTS",str(total),TOTL)
  printMessage("ERRORS",str(total_errors),TOTL)
  state_sorted = []
  for key in state_errors :
    state_sorted = state_sorted + ["{0:4d}:{1}".format(state_errors[key],key)]
  for key in sorted(state_sorted) :
    current_statement = key.split(':')[1]
    token = key.split(':')[2]
    number = key.split(':')[0]
    number = number.replace(" ","")
    printMessage(token,number,FREQ)
  warn_sorted = []
  for key in warning_table :
    warn_sorted = warn_sorted + ["{0}:{1}".format(key,warning_table[key])]
  for key in sorted(warn_sorted) :
    nkey = key.split(':')[0]
    warn = key.split(':')[1]
    printMessage(nkey,warn,WARN)
    if warn in warning_line :
      print("SOURCELINE",warning_line[warn],end=' ',file=error_log)
  error_log.close()
#
# Do not write the tables if there were errors
#
  if total_errors > 0 :
    sys.exit(total_errors)
#
# Write function database
#
  proc_file = open('funclist.db','w')
  for key in proc_table :
    proc_file.write(key)
    proc_file.write(proc_table[key])
    proc_file.write("\n")
#
# Write trigger database
#
  proc_file = open('triglist.db','w')
  for key in trig_table :
    proc_file.write(key)
    proc_file.write("|")
    proc_file.write(trig_table[key])
    proc_file.write("\n")
#
# Write table database
#
  proc_file = open('tablist.db','w')
  for key in tab_table :
    proc_file.write(key)
    proc_file.write("|")
    proc_file.write(tab_table[key])
    proc_file.write("\n")
#
# Write column database
#
  proc_file = open('collist.db','w')
  for key in col_table :
    proc_file.write(key)
    proc_file.write("|")
    proc_file.write(col_table[key])
    proc_file.write("\n")
#
# Write procref database
#
  proc_file = open('procref.db','w')
  for key in procref_table :
    proc_file.write(key)
    proc_file.write("|")
    proc_file.write(procref_table[key])
    proc_file.write("\n")
#
# Write procref database
#
  proc_file = open('procret.db','w')
  for key in proc_return :
    proc_file.write(key)
    proc_file.write("|")
    proc_file.write(proc_return[key])
    proc_file.write("\n")

  sys.exit(total_errors)

main()

