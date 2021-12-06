#! /usr/bin/python
#
# MSTEST.py Copyright (2008) Gwyneth Morrison
# Version 1.9.5 - May 09
# Build test functions for sql scripts
#

import  os, re, sys, string

default_int       = '10'
default_float     = '10.0'
default_bigint    = '10'
default_bitvar    = "b'10101010'"
default_uuid      = "'00000000-0000-0000-0000-000000000000'"
default_varchar   = "'Test'"
default_timestamp = 'getdate()'
default_boolean   = 'true'

proc_table = {}         # Proc table
proc_return = {}        # Return table
trig_table = {}         # Trig table
tab_table = {}          # Table table
col_table = {}          # Column table
procref_table = {}      # Procref table


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
      proc_return[line[0:i].lower()] = line[i+1:].lower()
      #print(line[0:i]," = ",line[i+1:])
#
# Main program
#
def main() :
 
  readFuncDB()
  readTrigDB()
  readTabDB()
  readColDB()
  readProcrefDB()
  readProcretDB()

  out_file = open("mstest.sql",'w')
  
  for func in proc_table :
    argstr = proc_table[func].lower()
    argstr = re.sub(r'\( *\)','NOARGUMENTS',argstr)
    argstr = re.sub(r'\( *[0-9]* *\)','',argstr)
    argstr = re.sub('NOARGUMENTS',r'( )',argstr)
    argstr = re.sub(r', *out *int','',argstr)
    argstr = re.sub(r', *out *uuid','',argstr)
    argstr = re.sub(r', *out *bigint','',argstr)
    argstr = re.sub(r' *out *int *,','',argstr)
    argstr = re.sub(r' *out *uuid *,','',argstr)
    argstr = re.sub(r' *out *bigint *,','',argstr)
    argstr = re.sub(r' *out *int','',argstr)
    argstr = re.sub(r' *out *uuid','',argstr)
    argstr = re.sub(r' *out *bigint','',argstr)
    argstr = re.sub(r'bit *varying',default_bitvar,argstr)
    argstr = re.sub(r'bigint',default_bigint,argstr)
    argstr = re.sub(r'int',default_int,argstr)
    argstr = re.sub(r'float',default_float,argstr)
    argstr = re.sub(r'uuid',default_uuid,argstr)
    argstr = re.sub(r'boolean',default_boolean,argstr)
    argstr = re.sub(r'timestamp',default_timestamp,argstr)
    argstr = re.sub(r'varchar',default_varchar,argstr)
    print("select 'Testing: ",func,proc_table[func],"' as TestID;",file=out_file)
    if func in proc_return :
      if 'setof ' in proc_return[func] :
        print("select * from ","%s%s" % (func,argstr),";",file=out_file)
      else :
        print("select ","%s%s" % (func,argstr),";",file=out_file)
    else :
      print("select ","%s%s" % (func,argstr),";",file=out_file)
      
  out_file.close()
  
main()

