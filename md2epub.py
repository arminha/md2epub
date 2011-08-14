#!/usr/bin/python
#
# md2epub.py
#
# by Ben Crowder
# http://bencrowder.net/
#
# Based off Matt Turner's GetBook.py
# http://staff.washington.edu/mdturner/personal.htm
#
# SmartyPants license:
#
#	Copyright (c) 2003 John Gruber  
#	(http://daringfireball.net/)  
#	All rights reserved.  
#
#	See below ("Redistribution...")
#
# smartypants.py license:
#
#	smartypants.py is a derivative work of SmartyPants.
# 
#	Redistribution and use in source and binary forms, with or without
#	modification, are permitted provided that the following conditions are
#	met:
#
#	*   Redistributions of source code must retain the above copyright
#			notice, this list of conditions and the following disclaimer.
# 
#	*   Redistributions in binary form must reproduce the above copyright
#			notice, this list of conditions and the following disclaimer in
#			the documentation and/or other materials provided with the
#			distribution.
# 
#	*   Neither the name "SmartyPants" nor the names of its contributors
#			may be used to endorse or promote products derived from this
#			software without specific prior written permission.
# 
#	This software is provided by the copyright holders and contributors "as
#	is" and any express or implied warranties, including, but not limited
#	to, the implied warranties of merchantability and fitness for a
#	particular purpose are disclaimed. In no event shall the copyright
#	owner or contributors be liable for any direct, indirect, incidental,
#	special, exemplary, or consequential damages (including, but not
#	limited to, procurement of substitute goods or services; loss of use,
#	data, or profits; or business interruption) however caused and on any
#	theory of liability, whether in contract, strict liability, or tort
#	(including negligence or otherwise) arising in any way out of the use
#	of this software, even if advised of the possibility of such damage.


import urllib, re, os, zipfile, glob, shutil, sys, markdown2, string, datetime

class Chapter:
	title = ''
	filename = ''
	htmlfile = ''
	id = ''
	children = []

	def __init__(self):
		self.children = []


class EPub:
	title = ''
	author = ''
	lang = 'en-US'
	basename = ''			# base name of ePub (before the extension)
	path = ''				# directory ePub will be stored in
	bookid = ''				# unique identifier
	url = ''				# URL for this book
	css = ''				# CSS file
	cover = ''				# book cover art
	toc = ''				# TOC (relative to the rest of the files)
	images = []				# list of images to be included
	children = []			# list of Chapters

	navpointcount = 1		# used for navpoint counts
	chapterids = []
	maxdepth = 1

	def cleanup(self):
		os.rmdir(self.path)


	# takes a list of chapters and writes the <item> tags for them and their children
	def write_items(self, children, f, pre):
		for chapter in children:
			# For child chapters, prepend the parent id to make this one unique
			if pre:
				id = pre + '_' + chapter.id
			else:
				id = chapter.id

			# Make sure we don't put duplicates in
			if id not in self.chapterids:
				self.chapterids.append(id)
			else:
				print 'Duplicate ID: %s' % (id)
				sys.exit(-1)

			# Write it out
			f.write('''
		<item id="''' + id + '''" href="''' + chapter.htmlfile + '''" media-type="application/xhtml+xml" />''')
			if chapter.children:
				self.write_items(chapter.children, f, id)


	# takes a list of chapters and writes the <itemref> tags for them and their children
	def write_itemrefs(self, children, f, pre):
		for chapter in children:
			if pre:
				id = pre + '_' + chapter.id
			else:
				id = chapter.id
			f.write('''
		<itemref idref="''' + id + '''"/>''')
			if chapter.children:
				self.write_itemrefs(chapter.children, f, id)


	# takes a list of chapters and writes them and their children to a navmap
	def write_chapter_navpoints(self, children, f, pre):
		for chapter in children:
			# For child chapters, prepend the parent id to make this one unique
			if pre:
				id = pre + '_' + chapter.id
			else:
				id = chapter.id

			f.write('''
		<navPoint id="''' + id + '''" playOrder="''' + str(self.navpointcount) + '''">
			<navLabel><text>''' + chapter.title + '''</text></navLabel>
			<content src="''' + chapter.htmlfile + '''" />''')
			self.navpointcount += 1
			if chapter.children:
				self.write_chapter_navpoints(chapter.children, f, id)
			f.write('''
		</navPoint>''')


	# takes a list of chapters and converts them and their children to Markdown
	def convert_chapters_to_markdown(self, children):
		for chapter in children:
			try:
				input = open('../../' + chapter.filename, 'r')
				f = open(chapter.htmlfile, 'w')
			except:
				print 'Error reading file "%s" from table of contents.' % chapter.filename
				sys.exit(-1)
			sourcetext = input.read()
			input.close()

			# write HTML header
			f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>''' + self.title + '''</title>''')
			if self.css:
				f.write('\n\t<link rel="stylesheet" type="text/css" href="' + os.path.basename(self.css) + '" />')
			f.write('''
<meta http-equiv="Content-Type" content="application/xhtml+xml; charset=utf-8" /> 
</head>
<body>''')

			# write the Markdowned text
			curled = curl_quotes(sourcetext)
			htmltext = markdown2.markdown(curled)
			f.write(htmltext.encode('utf-8'))

			# write HTML footer
			f.write('''
</body>
</html>''')

			f.close()

			if chapter.children:
				self.convert_chapters_to_markdown(chapter.children)


	# the main worker
	def save(self):
		# get current working directory
		cwd = os.getcwd()

		# create directory for the ePub
		os.mkdir(self.path)
		os.chdir(self.path)

		try:
			# make mimetype
			f = open('mimetype','w')
			f.write('application/epub+zip')
			f.close()

			# make the META-INF/container.xml
			os.mkdir('META-INF')
			os.chdir('META-INF')
			f = open('container.xml','w')
			f.write('''<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
	<rootfiles>
		<rootfile full-path="OEBPS/metadata.opf" media-type="application/oebps-package+xml" />
	</rootfiles>
</container>''')
			f.close()
			os.chdir('..')

			# make OEBPS/metadata.opf
			os.mkdir('OEBPS')
			os.chdir('OEBPS')
			f = open('metadata.opf','w')
			f.write('''<?xml version="1.0"?>
<package version="2.0" xmlns="http://www.idpf.org/2007/opf"
		 unique-identifier="bookid">
	<metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
		<dc:title>''' + self.title + '''</dc:title>
		<dc:creator opf:role="aut">''' + self.author + '''</dc:creator>
		<dc:language>''' + self.lang + '''</dc:language>
		<dc:identifier id="bookid">''' + self.url + '''</dc:identifier>''')
			if self.cover:
				f.write('\n\t\t<meta name="cover" content="book-cover" />')

			f.write('''
	</metadata>
	<manifest>
		<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml" />
''')

			if self.css:
				f.write('\t\t<item id="style" href="' + os.path.basename(self.css) + '" media-type="application/css" />')

			if self.cover:
				imagefile = os.path.basename(self.cover)
				ext = os.path.splitext(imagefile)[1][1:]	# get the extension
				if ext == 'jpg':
					ext = 'jpeg'
				f.write('\t\t<item id="book-cover" href="' + imagefile + '" media-type="image/' + ext + '" />')

			# write the <item> tags
			self.write_items(self.children, f, '')

			for image in self.images:
				imagefile = os.path.basename(image)
				ext = os.path.splitext(imagefile)[1][1:]	# get the extension
				if ext == 'jpg':
					ext = 'jpeg'
				f.write('''
		<item id="''' + imagefile + '''" href="''' + imagefile + '''" media-type="image/''' + ext + '''" />''')

			f.write('''
	</manifest>
	<spine toc="ncx">''')

			# write the <itemref> tags
			self.write_itemrefs(self.children, f, '')

			f.write('''
	</spine>''')

			if self.toc:
				f.write('''
	<guide>
		<reference type="toc" title="Table of Contents" href="''' + self.toc + '''.html" />
	</guide>''')

			f.write('''
</package>''')

			f.close()

			# make toc.ncx
			f = open('toc.ncx','w')
			f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
	<head>
		<meta name="dtb:uid" content="''' + self.url + '''" />
		<meta name="dtb:depth" content="''' + str(self.maxdepth) + '''" />
		<meta name="dtb:totalPageCount" content="0" />
		<meta name="dtb:maxPageNumber" content="0" />
	</head>
	<docTitle>
		<text>''' + self.title + '''</text>
	</docTitle>
	<navMap>''')

			self.write_chapter_navpoints(self.children, f, '')

			f.write('''
	</navMap>
</ncx>''')
			f.close()

			# convert the texts to Markdown and save in the directory
			self.convert_chapters_to_markdown(self.children)

			# if there's a CSS file, copy it in
			if self.css:
				if not os.path.exists('../../' + self.css):
					print "CSS file doesn't exist."
					sys.exit(-1)
				css = open('../../' + self.css, 'r')
				csstext = css.read()
				css.close()
				f = open(os.path.basename(self.css), 'w')
				f.write(csstext)
				f.close()

			# copy cover art into the directory
			if self.cover:
				if not os.path.exists('../../' + self.cover):
					print "Cover art file doesn't exist."
					sys.exit(-1)
				dest = os.path.basename(self.cover)
				shutil.copyfile('../../' + self.cover, dest)

			# copy images into the directory
			for image in self.images:
				dest = os.path.basename(image)
				shutil.copyfile('../../' + image, dest)

			# now zip the ePub up
			os.chdir('../..')
			file = zipfile.ZipFile(self.basename + '.epub', "w")
			os.chdir(self.path)

			file.write('mimetype','mimetype', zipfile.ZIP_STORED)
			file.write('META-INF/container.xml', 'META-INF/container.xml', zipfile.ZIP_DEFLATED)
			for filename in glob.glob("OEBPS/*"):
				file.write(filename, filename, zipfile.ZIP_DEFLATED)

			# and remove the directory
			os.chdir('..')
			shutil.rmtree(self.path)
		except:
			print "Unexpected error: ", sys.exc_info()[0]

			# if something went wrong, remove the temp directory
			os.chdir(cwd)
			shutil.rmtree(self.path)


def add_chapter(chapter, children, depth):
	# Go recursive
	if depth > 0:
		add_chapter(chapter, children[-1].children, depth - 1)
	else:
		children.append(chapter)


def process_book(filename):
	epub = EPub()

	now = datetime.datetime.now()
	epub.basename = filename.split('.')[0]
	epub.path = '%s_%s-%s-%s_%s-%s-%s' % (epub.basename, now.year, now.month, now.day, now.hour, now.minute, now.second)
	epub.url = 'http://localhost/' + epub.path		# dummy URL, replaced in control file
	epub.maxdepth = 1

	fh = open(filename, 'r')
	for line in fh.readlines():
		if line[0] == '#' or not line.strip():
			pass						# ignore comments and blank lines
		elif ':' in line and '|' not in line:			# keywords
			values = line.split(':', 1)
			keyword = values[0].strip()
			value = values[1].strip()
			if keyword == 'Title':
				epub.title = value
			elif keyword == 'Author':
				epub.author = value
			elif keyword == 'Language':
				epub.lang = value
			elif keyword == 'URL':
				epub.url = value
			elif keyword == 'TOC':
				epub.toc = value
			elif keyword == 'Image' or keyword == 'Images':
				images = value.split(',')
				# split list
				for image in images:
					epub.images.append(image.strip())
			elif keyword == 'CSS':
				epub.css = value
			elif keyword == 'Cover':
				epub.cover = value
		elif '|' in line:				# contents
			values = line.split('|')
			title = values[0].strip()
			filename = values[1].strip()

			chapter = Chapter()
			chapter.title = values[0].strip()
			chapter.filename = values[1].strip()

			# replace extension with .html
			basename = os.path.basename(chapter.filename)
			chapter.htmlfile = os.path.splitext(basename)[0] + '.html'

			# for the ID, lowercase it all, strip punctuation, and replace spaces with underscores
			chapter.id = re.sub(r'[^a-zA-Z0-9]', r'', chapter.title.lower()).replace(' ', '_')
			
			# if there's no ID left (because the chapter title is all Unicode, for example),
			# use the basename of the file instead
			if not chapter.id:
				chapter.id = os.path.splitext(basename)[0]

			# see how deep in the tree we are
			depth = line.rfind("\t") + 1

			# keep track of maximum depth
			if depth > (epub.maxdepth - 1):
				epub.maxdepth = depth + 1

			# add the current chapter
			add_chapter(chapter, epub.children, depth)
		else:
			print "Error on the following line:\n"
			print line
			sys.exit(-1)

	fh.close()

	# create a (hopefully unique) book ID
	epub.bookid = '[' + epub.title + '|' + epub.author + ']'

	return epub


##### Convert straight quotes to curly ones
# Code expanded from educateQuotes() in Chad Miller's smartypants.py
#	(http://web.chad.org/projects/smartypants.py/smartypants.py-1.5_1.6)
# which in turn is a port of John Gruber's SmartyPants plugin

def curl_quotes(str):
	oldstr = str
	punct_class = r"""[!"#\$\%'()*+,-.\/:;<=>?\@\[\\\]\^_`{|}~]"""

	# Take care of quotes in html tags (<div class="poetry">, etc.)
	str = re.sub(r"""<(.*?)="(.*?)">""", r"""<\1=~~~\2~~~>""", str)

	# Special case for 'Twas and 'Tis
	str = re.sub(r"""'Twas""", r"""&#8217;Twas""", str)
	str = re.sub(r"""'twas""", r"""&#8217;twas""", str)
	str = re.sub(r"""'Tis""", r"""&#8217;Tis""", str)
	str = re.sub(r"""'tis""", r"""&#8217;tis""", str)

	# Special case if the very first character is a quote followed by
	# punctuation at a non-word-break. Close the quotes by brute force:
	str = re.sub(r"""^'(?=%s\\B)""" % (punct_class,), r"""&#8217;""", str)
	str = re.sub(r"""^"(?=%s\\B)""" % (punct_class,), r"""&#8221;""", str)

	# Special case for double sets of quotes, e.g.:
	#   <p>He said, "'Quoted' words in a larger quote."</p>
	str = re.sub(r""""'(?=\w)""", """&#8220;&#8216;""", str)
	str = re.sub(r"""'"(?=\w)""", """&#8216;&#8220;""", str)

	# Special case for decade abbreviations (the '80s):
	str = re.sub(r"""\b'(?=\d{2}s)""", r"""&#8217;""", str)

	close_class = r"""[^\ \t\r\n\[\{\(\-]"""
	dec_dashes = r"""&#8211;|&#8212;"""

	# Get most opening single quotes:
	opening_single_quotes_regex = re.compile(r"""
		(
		\s          |   # a whitespace char, or
		&nbsp;      |   # a non-breaking space entity, or
		--          |   # dashes, or
		&[mn]dash;  |   # named dash entities
		\xe2\x80\x94  | # encoded em-dash
		_	        |   # underscore (for italic)
		>	        |   # HTML tag
		%s          |   # or decimal entities
		&\#x201[34];    # or hex
		)
		'                 # the quote
		(?=\w)            # followed by a word character
		""" % (dec_dashes,), re.VERBOSE)
	str = opening_single_quotes_regex.sub(r"""\1&#8216;""", str)

	closing_single_quotes_regex = re.compile(r"""
		(%s)
		'
		(?!\s | s\b | \d)
		""" % (close_class,), re.VERBOSE)
	str = closing_single_quotes_regex.sub(r"""\1&#8217;""", str)

	# hand's
	str = re.sub(r"(.)'(.)", r"\1&#8217;\2", str)

	# Any remaining single quotes should be opening ones:
	str = re.sub(r"""'""", r"""&#8216;""", str)

	# Get most opening double quotes:
	opening_double_quotes_regex = re.compile(r"""
		(
		\s          |   # a whitespace char, or
		&nbsp;      |   # a non-breaking space entity, or
		--			|	# dashes, or
		&[mn]dash;  |   # named dash entities
		\xe2\x80\x94  | # encoded em-dash
		_	        |   # underscore (for italic)
		>	        |   # HTML tag
		%s          |   # or decimal entities
		&\#x201[34];    # or hex
		)
		"                 # the quote
		(?=\w)            # followed by a word character
		""" % (dec_dashes,), re.VERBOSE)
	str = opening_double_quotes_regex.sub(r"""\1&#8220;""", str)

	# Double closing quotes:
	closing_double_quotes_regex = re.compile(r"""
		#(%s)?   # character that indicates the quote should be closing
		"
		(?=\s)
		""" % (close_class,), re.VERBOSE)
	str = closing_double_quotes_regex.sub(r"""&#8221;""", str)

	closing_double_quotes_regex = re.compile(r"""
		(%s)   # character that indicates the quote should be closing
		"
		""" % (close_class,), re.VERBOSE)
	str = closing_double_quotes_regex.sub(r"""\1&#8221;""", str)

	# Any remaining quotes should be opening ones.
	str = re.sub(r'"', r"""&#8220;""", str)

	# Take care of quotes in html tags (<div class="poetry">, etc.)
	str = re.sub(r"""~~~""", r'"', str)

	return str


##### Main

def main():
	if (len(sys.argv) > 1):
		epub = process_book(sys.argv[1])
		epub.save()

if __name__ == "__main__":
	main()
