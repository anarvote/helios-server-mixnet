#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    Copyright © 2016 RunasSudo (Yingtong Li)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# ily Python 3
from __future__ import print_function, unicode_literals

from mixnet.Ciphertext import Ciphertext
from mixnet.CiphertextCollection import CiphertextCollection
from mixnet.EGCryptoSystem import EGCryptoSystem
from mixnet.PrivateKey import PrivateKey
from mixnet.PublicKey import PublicKey
from mixnet.ShufflingProof import ShufflingProof

import json, sys, urllib2

electionUrl = sys.argv[1].rstrip("/")
NUM_BITS = 2048 # TODO: Actually detect this

class statusCheck:
	def __init__(self, status):
		print(status, end="")
	def __enter__(self):
		return
	def __exit__(self, type, value, traceback):
		if value:
			print(": FAIL")
		else:
			print(": OK")

with statusCheck("Downloading election data"):
	# Election
	election = json.load(urllib2.urlopen(electionUrl))
	
	cryptosystem = EGCryptoSystem.load(NUM_BITS, long(election["public_key"]["p"]), long(election["public_key"]["g"]))
	pk = PublicKey(cryptosystem, long(election["public_key"]["y"]))
	
	# Ballots
	ballots = []
	ballotList = json.load(urllib2.urlopen(electionUrl + "/ballots"))
	for ballotInfo in ballotList:
		ballot = json.load(urllib2.urlopen(electionUrl + "/ballots/" + ballotInfo["voter_uuid"] + "/last"))
		ballots.append(ballot)
	
	# Mixes & Proofs
	mixnets = []
	numMixnets = json.load(urllib2.urlopen(electionUrl + "/mixnets"))
	for i in xrange(0, numMixnets):
		mixedAnswers = json.load(urllib2.urlopen(electionUrl + "/mixnets/" + str(i) + "/answers"))
		shufflingProof = json.load(urllib2.urlopen(electionUrl + "/mixnets/" + str(i) + "/proof"))
		mixnets.append((mixedAnswers, shufflingProof))
	
	assert(numMixnets == 1)

with statusCheck("Verifying mix"):
	proof = ShufflingProof.from_dict(mixnets[0][1], pk, NUM_BITS)
	
	orig = CiphertextCollection(pk)
	for ballot in reversed(ballots):
		ciphertext = Ciphertext(NUM_BITS, orig._pk_fingerprint)
		
		ciphertext.append(long(ballot["vote"]["answers"][0]["choices"][0]["alpha"]), long(ballot["vote"]["answers"][0]["choices"][0]["beta"]))
		
		orig.add_ciphertext(ciphertext)
	
	shuf = CiphertextCollection(pk)
	for ballot in mixedAnswers["answers"]:
		ciphertext = Ciphertext(NUM_BITS, shuf._pk_fingerprint)
		
		ciphertext.append(long(ballot["choice"]["alpha"]), long(ballot["choice"]["beta"]))
		
		shuf.add_ciphertext(ciphertext)
	
	# TODO: Verify the Helios challenge
	def _generate_challenge(a, b):
		return mixnets[0][1]["challenge"]
	proof._generate_challenge = _generate_challenge
	
	if not proof.verify(orig, shuf):
		raise Exception()
