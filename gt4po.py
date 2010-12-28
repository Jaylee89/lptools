#!/usr/bin/python
#
# automated translation of a .PO file with the Google Ajax Lanague API
#
import json
import optparse
import os
import polib
import re
import sys
import urllib
import urllib2

parser = optparse.OptionParser(usage="usage: %prog [options] pofile...")
parser.add_option("--destlang", dest="destlang", help="destination language")
parser.add_option("--fuzzy", action="store_true", default=True, dest="fuzzy", help="flag translations as fuzzy (default)")
parser.add_option("--no-fuzzy", action="store_false", dest="fuzzy", help="do NOT flag translations as fuzzy")
parser.add_option("--srclang", default="en", dest="srclang", help="source language (default=last 2 chars of base filename)")
parser.add_option("--quiet", action="store_false", default=True, dest="verbose", help="don't print status messages to stdout")

(options, args) = parser.parse_args()

if args == None or len(args) == 0:
	print("ERROR: you must specify at least one po file to translate");
	sys.exit(1)

paramFix = re.compile("(\\(([0-9])\\))")

for srcfile in args:
	
	print("INFO: processing %s" % srcfile)
	
	if options.srclang == None:
		basename = os.path.splitext(srcfile)[0]
		options.srclang = basename[-2:]
		
	src_phrase = []

	po = polib.pofile(srcfile, autodetect_encoding=False, encoding="utf-8", wrapwidth=-1)
	for entry in po:
		if entry.obsolete or entry.msgstr != '':
			continue
			
		#print("entry=%s: %s (%s, %s)" % (entry.msgid, entry.msgstr, entry.obsolete, entry.flags))
			
		src_phrase.append(entry.msgid)
		
	print("INFO: %d phrases to translate from %s" % (len(src_phrase), options.srclang))
	
	destlangs = options.destlang.split(",")
	
	for destlang in destlangs:
		
		dest_xlate = {}
		for phrase in src_phrase:
			dest_xlate[phrase] = ""
	
		targetfile = os.path.splitext(srcfile)[0][:-2] + destlang + ".po"
		if os.path.exists(targetfile):
			count = 0
			print("INFO: loading existing %s translations from %s" % (destlang, targetfile))
			po = polib.pofile(targetfile, autodetect_encoding=False, encoding="utf-8", wrapwidth=-1)
			for entry in po:
				
				if entry.obsolete or entry.msgstr == '':
					continue
				
				#LATER: option to purge unused
					
				dest_xlate[entry.msgid] = entry.msgstr
				count = count + 1
				
			print("INFO: %d existing translations loaded" % (count))
			
		all_translate = []
		for phrase in dest_xlate.keys():
			if len(dest_xlate[phrase]) == 0:
				all_translate.append( ('q', phrase) )
		
		print("INFO: %d phrases to translate from %s to %s" % (len(all_translate), options.srclang, destlang))
		
		if len(all_translate) == 0:
			continue
			
		for xlate_loop in xrange(0, len(all_translate), 5):

			to_translate = all_translate[ xlate_loop : xlate_loop + 5]
			
			url = u"http://ajax.googleapis.com/ajax/services/language/translate"
			query_string = [ ("v", "1.0") ]
			query_string.extend(to_translate)
			query_string.append( (u"langpair", options.srclang + u"|" + destlang) )
			
			req_xlate = urllib2.Request(url + u"?" + urllib.urlencode(query_string, True))
			req_xlate.add_header("Referer", "http://www.localeplanet.com/support/contact.html")
			#print("DEBUG: url=%s" % req_xlate.get_full_url())
			f = urllib2.urlopen(req_xlate)
			str_xlate = f.read()
			f.close()
			
			xlate_data = json.loads(str_xlate)
			if xlate_data["responseStatus"] != 200:
				print("ERROR: %d when translating to %s" % ( xlate_data["responseStatus"], destlang))
				continue
			
			if len(to_translate) == 1:
				xlates = [ xlate_data ]
			else:
				xlates = xlate_data["responseData"]
				
			for loop in range(0, len(to_translate) - 1):
				xlate = xlates[loop]
				if "responseStatus" in xlate and xlate["responseStatus"] == 200:
					
					text = xlate["responseData"]["translatedText"]
					text = paramFix.sub("{\\2}", text)
					
					entry = po.find(to_translate[loop][1])
					if entry:
						entry.msgstr = text
					else:
						entry = polib.POEntry(msgid=to_translate[loop][1], msgstr=text)
						po.append(entry)
					
					if options.fuzzy:
						entry.flags.append("fuzzy")
				else:
					print("WARNING: unable to translate %s to %s (%s)" % (to_translate[loop][1], destlang, repr(xlate)))
	
		print("INFO: saving to %s" % (targetfile))
		po.save(targetfile)
	
