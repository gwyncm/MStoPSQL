#! /usr/bin/python
#
# sqlgen.py Copyright (2008) Gwyneth Morrison
# updates for python 3.0 Jan 2009
# Generate sql files from .db mstopsql files
#

import os, re, sys, string


# You can set these as you like

countsize = 'N'                   # count field sizes
output_file   = "result2.sql"
POSTGRES = None


# These are set by the program

out_file  = None
dirsep    = '/'
field_table = {}                  # field count list
infile = None

proc_table = {}		          # proc table
procref_table = {}		  # proc reference table

#
# Read the function database
#
def readFuncDB() :
  global proc_table
  directory = "."
  filepath = os.path.join(directory , "funclist.db")
  if os.path.exists(filepath) :
    file = open(filepath,'rU')
  else :
    file = open(filepath,'w')
  for line in file :
    line = line.rstrip("\n")
    i = line.find("(")
    proc_table[line[0:i]] = line[i:]
#
# Read the procref database
#
def readProcrefDB() :
  global procref_table
  directory = "."
  filepath = os.path.join(directory , "procref.db")
  if os.path.exists(filepath) :
    file = open(filepath,'rU')
  else :
    file = open(filepath,'w')
  for line in file :
    line = line.rstrip("\n")
    i = line.find("|")
    procref_table[line[0:i]] = line[i+1:]

#
# Collect the field names and sizes
#
def fieldsize(field,size) :
  global field_table
  if field in field_table:
    if size > field_table[field] :
      field_table[field] = size
  else :
    field_table[field] = size

#
#  Write out the call list
#
def writecalllist(call_list) : 
  global countsize
  global out_file
  
  for func in call_list :
    caller = func
    called = call_list[func]

    if countsize == 'Y' :
      fieldsize("reference.caller",len(called))
      fieldsize("reference.called",len(caller))

    out_file.write("insert into sql2ref (caller,called) values (\'")
    out_file.write(called)
    out_file.write("\',\'")
    out_file.write(caller)
    out_file.write("\');")
    out_file.write("\r")
    out_file.write("\n")
   
#
#  Write out the proc list
#
def writeproclist(proc_list) : 
  global countsize
  global out_file
  
  for func in proc_list :

    if countsize == 'Y' :
      fieldsize("proclist.name",len(func))

    out_file.write("insert into proclist (name) values (\'")
    out_file.write(func)
    out_file.write("\');")
    out_file.write("\r")
    out_file.write("\n")

#
# Main program
#
def main() :
  global out_file
  global dirsep
  global file_pattern
  global search_path
  global field_table
  global procref_table
  global proc_table

  readProcrefDB()
  readFuncDB()
  out_file = open(output_file,'w')
  if  os.name == "nt" : dirsep = '\\' 
  writeproclist(proc_table)
  writecalllist(procref_table)
  if not POSTGRES :
    out_file.write("exit\r\n")
  out_file.close()
  for field in sorted(field_table) : 
    print (field,field_table[field])
main()
