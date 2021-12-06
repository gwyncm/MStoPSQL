#! /usr/bin/python
#
# MSREP.py Copyright (2008) Gwyneth Morrison
# Version 1.9.5 - May 09
# Build test report for sql test scripts
#

import  os, re, sys, string


error_table = {}        # Error table

#
# Main program
#
def main() :

  in_file  = open("testlog.log",'r')
  out_file = open("testrep.log",'w')
  
  for line in in_file :
    if 'ERROR' in line :
      if 'violates foreign key' in line :
        line = format('ERROR:\t(compressed)Violates Foreign Key\n') 
      if line in error_table :
        error_table[line] = error_table[line] + 1
      else :
        error_table[line] = 1 
        
  savenum = 1
  while savenum > 0 :      
    saveline = ""
    savenum = 0
    for line in error_table :
      if error_table[line] > savenum :
        savenum = error_table[line]
        saveline = line
    if savenum > 0 :
      print(format(savenum,"6"),saveline,file=out_file)
      error_table[saveline] = 0
      
  out_file.close()
  in_file.close()
  
main()

