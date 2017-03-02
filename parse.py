import codecs
import re

from lib.abstract import printable


class Error(Exception): pass
class ParseError(Error): pass


def iter_blocks(path):
	"""The LiveHeader output file consists of blocks
	of text separated by hyphen-only lines. Open the
	file and iterate over the split blocks.
	"""

	## FIXME: This will overtax the CPU for large
	## files without a hyphen-only line.

	## TODO: Make a parser that works on a line-by-
	## line basis.

	m = re.compile(r'(?s)(.+?)\r?\n---+')
	with codecs.open(path, "rb", "utf8") as f:
		for x in m.finditer(f.read()):
			yield x.group(1)


@printable
class ParsedBlock(object):
	"""Represents a text block (e.g. as returned by
	iter_blocks()) parsed into its component parts.
	"""

	def __init__(self, text):
		p1, p2, p3 = self.split_block_into_parts(text)
		
		self.url = p1
		self.get, self.req = self.split_header_part(p2)
		self.ret, self.res = self.split_header_part(p3)

	@classmethod
	def split_block_into_parts(cls, text):
		"""Each block has three parts, separated by
		a double CRLF: the URL that was fetched, the
		request header, and the response header.
		"""
		parts = re.split(r'\r?\n\r?\n', text)
		if not len(parts) == 3: raise ParseError(
			"ParsedBlock: invalid block; expected exactly three compartments")
		return parts

	@classmethod
	def split_header_part(cls, text):
		"""Each of the two header parts will have
		a non-header line of text prior to its header's
		key-value fields. Return a 2-tuple: the first
		element is the non-header line of text, the
		second element a dictionary of the header fields.
		"""

		lines = re.split(r'\r?\n', text)

		if not lines: raise ParseError(
			"ParsedBlock: invalid block part; has too few lines; need at least 1")

		header = {}

		for line in lines[1:]:

			kv = re.split(r' *: *', line, maxsplit=1)
			if not len(kv) == 2: raise ParseError("ParsedBlock: invalid header field |%s|" % line)

			header[kv[0].strip()] = kv[1].strip()

		return (lines[0], header)


if "__main__" == __name__:
	for n, b in enumerate(iter_blocks("samples/1")):
		print ParsedBlock(b)
		break
