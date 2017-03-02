import codecs
import re
import urlparse

from lib.abstract import printable


class Error(Exception): pass
class ParseError(Error): pass
class ConsumeError(ParseError): pass


def iter_lines_tagged(file, eol=r'(?:\r?\n|\n?\r)'):
	"""Iterate over every line in the file. Return a
	tuple (tag, text) where <tag> is "eop" if the line
	marks an "end of part", "eob" if it marks an "end
	of block", or "text" if it is a proper row of text.

	A LiveHeader output file consists of "blocks"
	of text separated by hyphen-only lines. Each block
	consists of three "parts".

	Each blocks is the log of a single request-response
	interaction.
	"""

	m = re.compile(
		r'(?:'
		r'(?P<eop>' + eol + r')|'
		r'(?P<eob>-{5,})|'
		r'(?P<text>.+?)'
		r')'
		r'(?:' + eol + r'|$)')

	for x in m.finditer(file.read()):

		if x.group("eop"):
			yield "eop", None
		elif x.group("eob"):
			yield "eob", None
		elif x.group("text"):
			yield "text", x.group("text")


def parse_key_value_pair(text, sep=r':'):
	"""Split a (line of) text at the first
	occurrence of <sep>.
	"""
	kv = re.split(sep, text, maxsplit=1)
	if not len(kv) == 2: raise ParseError("parse_key_value_pair: text is not a key-value pair: |%s|" % text)
	return kv[0].strip(), kv[1].strip()


@printable
class Interaction(object):
	"""Represents a single request-response interaction
	i.e. a parsed "block" that had been read from a
	LiveHeader output file.
	"""

	def __init__(self):
		self.url = "" ## The URL that was fetched.
		self.get = "" ## The HTTP GET string.
		self.ret = "" ## The HTTP response string.
		self.req = {} ## The request headers.
		self.res = {} ## The response headers.


class TaggedLineConsumer(object):

	def __init__(self, cls):
		self.cls = cls
		self.reset()

	def reset(self):
		self.it = self.cls()
		self.method = self.consume_first

	def consume_first(self, *aa, **kk):
		raise NotImplementedError

	def skip_until_next(self, *aa, **kk):
		pass

	def consume(self, *aa, **kk):

		try:
			return self.method(*aa, **kk)
		except ConsumeError as e:
			self.method = self.skip_until_next
			return e


class InteractionTLC(TaggedLineConsumer):

	def __init__(self):
		TaggedLineConsumer.__init__(self, Interaction)

	def consume_first(self, *aa, **kk):
		return self.consume_url(*aa, **kk)

	def skip_until_next(self, tag, text):
		if tag == "eob":
			self.method = self.consume_url

	def consume_url(self, tag, text):
		if tag != "text": raise ConsumeError("Interaction.scan: expected the interaction's URL line")
		self.it.url = text
		self.method = self.consume_eop

	def consume_eop(self, tag, text):
		if tag != "eop": raise ConsumeError("Interaction.scan: expected end of part")
		self.method = self.consume_get

	def consume_get(self, tag, text):
		if tag != "text": raise ConsumeError("Interaction.scan: expected the interaction's GET line")
		self.it.get = text
		self.method = self.consume_kv_or_eop

	def consume_kv_or_eop(self, tag, text):
		if tag == "eop":
			self.method = self.consume_ret
		elif tag == "text":
			try: k, v = parse_key_value_pair(text)
			except ParseError:
				self.data = urlparse.parse_qs(text)
				self.method = self.consume_ret
			else:
				self.it.req[k] = v
				# self.method = consume_kv_or_eop
		else:
			raise ConsumeError("Interaction.scan: expected request header field or end of part")
			
	def consume_ret(self, tag, text):
		if tag != "text": raise ConsumeError("Interaction.scan: expected the interaction's RET line")
		self.it.ret = text
		self.method = self.consume_kv_or_eob

	def consume_kv_or_eob(self, tag, text):
		if tag == "eob":
			it = self.it
			self.it = Interaction()
			self.method = self.consume_url
			return it
		elif tag == "text":
			k, v = parse_key_value_pair(text)
			self.it.res[k] = v
			# self.method = consume_kv_or_eob
		else:
			raise ConsumeError("Interaction.scan: expected response header field or end of block")


if "__main__" == __name__:
	path = "samples/1"
	count = 0
	with codecs.open(path, "rb", "utf8") as file:
		tlc = InteractionTLC()
		for tl in iter_lines_tagged(file):
			obj = tlc.consume(*tl)
			if isinstance(obj, Error):
				print obj
				print "-" * 78
			elif obj:
				count += 1
				# print obj
				# print "-" * 78
	print count, "interactions found"
