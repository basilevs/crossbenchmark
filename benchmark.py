#!/usr/bin/python
from subprocess import Popen, PIPE
from sys import argv, exit
from argparse import ArgumentParser
from tempfile import mkstemp
from operator import xor
from pickle import dump, load
from os.path import exists


class Stat:
	def __init__(self, real = 0, user = 0, sys = 0, count = 1):
		self.count = count
		self.real = real
		self.user = user
		self.sys = sys
	def __add__(self, other):
		return Stat(self.real + other.real, self.user + other.user, self.sys + other.sys, self.count + other.count)
	def __str__(self):
		return "".join(map(str, ('real ',self.real/self.count, ', user ', self.user/self.count, ', system ', self.sys/self.count)))
	def __repr__(self):
		return 'Stat'+repr((self.real,self.user,self.sys,self.count))

Stat.empty = Stat(count=0)

parser = ArgumentParser(description = 'Benchmarks software, collects statistics. Remembers timngs for different command line arguments.')
parser.add_argument('--dump', '-d', action = 'store_true', help = 'just print previously collected statistis, do not execute anything')
parser.add_argument('--warmup', '-w', action = 'store_true', help = 'perform a warmup run before measurements')
parser.add_argument('--ignore-errors', '-i', dest = 'ignoreerrors', action = 'store_true', help = 'ignore error codes returned by benchmarked program')
parser.add_argument('--file', '-f', default = 'benchmark.dat', help = 'use this file for statistics storage')
parser.add_argument('--count', '-c', type = int, default = 1, help = 'A number of time to execute target. If this is greater than one, first run is not accounted in statistics.')

config, targetArgs = parser.parse_known_args(argv[1:])
targetArgs = tuple(targetArgs)

if len(targetArgs) == 0:
	config.count = 0
	config.warmup = False

def hashList(list):
	return reduce(xor, map(hash, list))

timeArgs=('/usr/bin/time', '--format', '%e\t%U\t%S', '--')

def collect():
	process = Popen(timeArgs+targetArgs, stdout=PIPE, stderr=PIPE)
	lines = process.stderr.readlines()
	line = lines[-1]
	process.stderr.close()
	process.stdout.close()
	rv = Stat()
	rv.count = 1
	rc = process.wait()
	print "".join(lines)
	if not config.ignoreerrors and rc != 0 :
		raise RuntimeError(" ".join(targetArgs)+" returned code "+str(rc))
	try:
		rv.real,rv.user,rv.sys = map(float, line.split('\t'))
	except ValueError:
		raise
	return rv


storage = {}
if exists(config.file):
	with open(config.file, 'r') as f:
		storage = load(f)

def keyToStr(key):
	return " ".join(key)
def keyWidth(key):
	return len(keyToStr(key))

defaultKeyWidth = 0
def printItem(key):
	global defaultKeyWidth
	if not defaultKeyWidth:
		defaultKeyWidth = keyWidth(key) + 1
	format = "%%%ds : %%d, %%f , %%f, %%f" % defaultKeyWidth
	value = storage[key]
	print format % (keyToStr(key), value.count, value.real/value.count, value.user/value.count, value.sys/value.count)
	
if config.dump:
	words = set(targetArgs)
	def valid(x):
		for word in words:
			if keyToStr(x).find(word) < 0:
				return False
		return True
	filtered = filter(valid, storage.keys())
	if len(filtered) > 0:
		defaultKeyWidth = max(map(keyWidth, filtered)) + 1
		map(printItem, filtered)
else:	
	if config.warmup and config.count >= 1:
		collect()
	for v in range(config.count):
		oldstat = storage.get(targetArgs, Stat.empty)
		stat = collect()
		storage[targetArgs] = oldstat + stat
		printItem(targetArgs)
	with open(config.file, 'w') as f:
		dump(storage, f)


	
		
