#! /usr/bin/python
#
# Convert xml to postgres copy
# Copyright (2008) Gwyneth Morrison   
#
import os, sys, xml.sax

def normalizeWhitespace(text) :
  return ' '.join(text.split())

class docHandler(xml.sax.ContentHandler) :
  def __init__(self) :
    self.header = None		# Main header
    self.table = None		# Table name
    self.field = None		# Field name
    self.data = ""		# Data value
    self.data_stack = []	# Data stack
    self.comma = None 		# Insert comma
  def startElement(self, name, attrs) :
    if self.header == None :
      self.header = name
      return
    if self.table == None :
      self.table = name
      print "COPY",self.table,"(",
      self.comma = None
      return
    if self.field == None :
      self.field = name
      return
  def endElement(self, name) :
    if self.field : 
        if self.comma : print ",",
	print self.field,
        self.data_stack = self.data_stack + [ self.data ]
        self.field = None
        self.data = ""
        self.comma = ','
        return
    if self.table : 
      self.table = None
      print ") FROM stdin;"
      line = ""
      for value in self.data_stack :
        value = normalizeWhitespace(value)
        if line : line = line + "\t"
        if value == 'false' : value = '0'
        if value == 'true' : value = '1'
        line = line + value
      print line 
      self.data_stack = []
      print "\."
      return
    if self.header : 
      self.header = None
      return
  def characters(self, ch) :
    self.data += ch
#
# Main program
#
def main() :
  try :
    inFile = sys.argv[1]
  except IndexError :
    print "Usage: %s <FILENAME>" % sys.argv[0]
    sys.exit(0)
  parser = xml.sax.make_parser()
  parser.setContentHandler(docHandler())
  parser.parse(file(inFile))

main()

