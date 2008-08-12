# Python imports
import os
import subprocess
import time
import socket

# find an elementtree implementation
ET = None
errors = []
try:
    import elementtree.ElementTree as ET
except ImportError, e:
    errors.append(e)
try:
    import cElementTree as ET
except ImportError, e:
    errors.append(e)
try:
    import lxml.etree as ET
except ImportError, e:
    errors.append(e)
try:
    import xml.etree.ElementTree as ET
except ImportError, e:
    errors.append(e)
if ET is None:
    raise ImportError(str(errors))


# TODO: do this properly
sharedir = '/usr/share/tp'


class ServerList(dict):
	"""\
	Builds a list of servers from multiple XML files.
	Includes rulesets and special parameters.
	"""

	def absorb_xml(self, xmlfile):
		"""\
		Import an XML file describing a server or server component.
		"""
		xmltree = ET.parse(xmlfile)
		for server in xmltree.findall('server'):
			sname = server.attrib['name']
			if not self.has_key(sname):
				self[sname] = {}
				self[sname]['forced'] = []
				self[sname]['parameters'] = {}
				self[sname]['rulesets'] = {}
			if not self[sname].has_key('longname') and server.find('longname') is not None:
				self[sname]['longname'] = server.find('longname').text
			if not self[sname].has_key('version') and server.find('version') is not None:
				self[sname]['version'] = server.find('version').text
			if not self[sname].has_key('description') and server.find('description') is not None:
				self[sname]['description'] = server.find('description').text
			for forced in server.findall('forced'):
				self[sname]['forced'].append(forced.text)
			for sparam in server.findall('parameter'):
				pname = sparam.attrib['name']
				self[sname]['parameters'][pname] = {
						'type' : sparam.attrib['type'],
						'longname' : sparam.find('longname').text,
						'description' : sparam.find('description').text,
						'default' : sparam.find('default').text,
						'commandstring' : sparam.find('commandstring').text
					}
			for ruleset in server.findall('ruleset'):
				rname = ruleset.attrib['name']
				self[sname]['rulesets'][rname] = {
						'longname' : ruleset.find('longname').text,
						'version' : ruleset.find('version').text,
						'description' : ruleset.find('description').text,
						'forced' : [],
						'parameters' : {},
					}
				for forced in ruleset.findall('forced'):
					self[sname]['rulesets'][rname]['forced'].append(forced.text)
				for rparam in ruleset.findall('parameter'):
					pname = rparam.attrib['name']
					self[sname]['rulesets'][rname]['parameters'][pname] = {
							'type' : rparam.attrib['type'],
							'longname' : rparam.find('longname').text,
							'description' : rparam.find('description').text,
							'default' : rparam.find('default').text,
							'commandstring' : rparam.find('commandstring').text
						}

class AIList(dict):
	"""\
	Builds a list of AIs from multiple XML files.
	Includes rulesets and special parameters.
	"""

	def absorb_xml(self, xmlfile):
		"""\
		Import an XML file describing a server or server component.
		"""
		xmltree = ET.parse(xmlfile)
		for aiclient in xmltree.findall('aiclient'):
			ainame = aiclient.attrib['name']
			if not self.has_key(ainame):
				self[ainame] = {}
				self[ainame]['rules'] = []
				self[ainame]['forced'] = []
				self[ainame]['parameters'] = {}
			for rules in aiclient.findall('rules'):
				self[ainame]['rules'].append(rules.text)
			for forced in aiclient.findall('forced'):
				self[ainame]['forced'].append(forced.text)
			for aiparam in aiclient.findall('parameter'):
				pname = aiparam.attrib['name']
				self[ainame]['parameters'][pname] = {
						'type' : aiparam.attrib['type'],
						'longname' : aiparam.find('longname').text,
						'description' : aiparam.find('description').text,
						'default' : aiparam.find('default').text,
						'commandstring' : aiparam.find('commandstring').text,
					}


class InitError(Exception):
	pass

class SinglePlayerGame:
	"""\
	A single-player game manager.
	"""

	def __init__(self):
		#reset active flag
		self.active = False
		self.sname = None

		# build a server list
		self.serverlist = ServerList()
		for xmlfile in os.listdir(os.path.join(sharedir, 'servers')):
			xmlfile = os.path.join(sharedir, 'servers', xmlfile)
			if os.path.isfile(xmlfile) and xmlfile.endswith('xml'):
				self.serverlist.absorb_xml(xmlfile)

		# build an AI client list
		self.ailist = AIList()
		for xmlfile in os.listdir(os.path.join(sharedir, 'aiclients')):
			xmlfile = os.path.join(sharedir, 'aiclients', xmlfile)
			if os.path.isfile(xmlfile) and xmlfile.endswith('xml'):
				self.ailist.absorb_xml(xmlfile)

		# prepare internals
		self.sname = ''
		self.rname = ''
		self.sparams = {}
		self.rparams = {}
		self.opponents = []

	def __del__(self):
		if self.active:
			self.stop()

	@property
	def rulesets(self):
		"""\
		Returns a list of available rulesets from all servers.
		"""
		rulesets = []
		for sname in self.serverlist.keys():
			for rname in self.serverlist[sname]['rulesets'].keys():
				if rname not in rulesets:
					rulesets.append(rname)
		return rulesets

	def ruleset_info(self, rname):
		for sname in self.serverlist.keys():
			if self.serverlist[sname]['rulesets'].has_key(rname):
				return self.serverlist[sname]['rulesets'][rname]

	def list_servers_with_ruleset(self):
		"""\
		Returns a list of servers supporting the game ruleset.
		"""
		servers = []
		for sname in self.serverlist.keys():
			if self.serverlist[sname]['rulesets'].has_key(self.rname):
				servers.append(sname)
		return servers

	def list_aiclients_with_ruleset(self):
		"""\
		Returns a list of AI clients supporting the game ruleset.
		"""
		aiclients = []
		for ainame in self.ailist.keys():
			if self.rname in self.ailist[ainame]['rules']:
				aiclients.append(ainame)
		return aiclients

	def list_sparams(self):
		"""\
		Returns the parameter list for the current server.
		"""
		return self.serverlist[self.sname]['parameters']

	def list_rparams(self):
		"""\
		Returns the parameter list for the current server.
		"""
		return self.serverlist[self.sname]['rulesets'][self.rname]['parameters']

	def add_opponent(self, ainame, aiuser, aiparams):
		"""\
		Adds an AI client opponent to the game (before starting).

		Parameters:
		ainame (string) - the name of the AI client
		aiuser (string) - the desired username of the opponent
		aiparams (dict) - parameters {'name', 'value'}
		"""
		for aiclient in self.opponents:
			if aiclient['user'] is aiuser:
				return False

		aiclient = {
				'name' : ainame,
				'user' : aiuser.translate(''.join([chr(x) for x in range(256)]),' '),
				'parameters' : aiparams,
			}
		self.opponents.append(aiclient)

		return True

	def start(self):
		"""\
		Starts the server and AI clients.
		Returns port number if successful (OK to connect).
		Returns False otherwise.
		"""
		# find a free port
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.bind(('localhost',0))
		port = s.getsockname()[1]
		s.close()

		try:
			# start server
			server = self.serverlist[self.sname]
			parameters = server['parameters']
			ruleset = server['rulesets'][self.rname]

			# start server - create server command line
			servercmd = "%s start %s %s" % (os.path.join(sharedir, 'servers', self.sname + '.init'), self.rname, port)

			# start server - add forced parameters to command line
			for forced in server['forced']:
				servercmd += ' ' + forced

			# start server - add regular parameters to command line
			for pname in parameters.keys():
				value = parameters[pname]['default']
				if self.sparams.has_key(pname):
					value = self.sparams[pname]
				value = self._format_value(value, parameters[pname]['type'])
				if value is None:
					continue
				servercmd += ' ' + parameters[pname]['commandstring'] % value

			# start server - add forced ruleset parameters to command line
			for forced in ruleset['forced']:
				servercmd += ' ' + forced
			
			# start server - add regular ruleset parameters to command line
			for pname in ruleset['parameters'].keys():
				value = ruleset['parameters'][pname]['default']
				if self.rparams.has_key(pname):
					value = self.rparams[pname]
				value = self._format_value(value, ruleset['parameters'][pname]['type'])
				if value is None:
					continue
				servercmd += ' ' + ruleset['parameters'][pname]['commandstring'] % value

			# start server - call the control script
			rc = subprocess.call(servercmd, shell=True)
			if rc is not 0:
				raise InitError, 'Server ' + sname + ' failed to start'

			# wait for the server to initialize
			# FIXME: what is the system is loaded?
			time.sleep(5)
	
			# start AI clients
			for aiclient in self.opponents:
				aicmd = "%(path)s start %(rname)s %(port)i %(user)s" % {
							'path': os.path.join(sharedir, 'aiclients', aiclient['name'] + '.init'),
							'port': port,
							'rname': rname,
							'user': aiclient['user'],
						}
				
				# add forced parameters to command line
				for forced in self.ailist[aiclient['name']]['forced']:
					aicmd += ' ' + forced

				# add regular parameters to command line
				for pname in self.ailist[aiclient['name']]['parameters'].keys():
					value = self.ailist[aiclient['name']]['parameters'][pname]['default']
					if aiclient['parameters'].has_key(pname):
						value = aiclient['parameters'][pname]
					value = self._format_value(value, self.ailist[aiclient['name']]['parameters'][pname]['type'])
					if value is None:
						continue
					aicmd += ' ' + self.ailist[aiclient['name']]['parameters'][pname]['commandstring'] % value

				# call the control script
				rc = subprocess.call(aicmd, shell=True)
				if rc is not 0:
					raise InitError, 'AI client ' + aiclient['name'] + ' failed to start'

			# set active flag
			self.active = True

		except:
			self.stop()
			return False

		return port

	def stop(self):
		"""\
		Stops the server and AI clients.
		Should be called by the client when disconnecting/closing.
		"""
		# stop server
		if self.sname is not None:
			servercmd = os.path.join(sharedir, 'servers', self.sname + '.init') + ' stop'
			os.system(servercmd)
			self.sname = None

		# stop AI clients
		for aiclient in self.opponents:
			aicmd = os.path.join(sharedir, 'aiclients', aiclient['name'] + '.init') + ' stop'
			os.system(aicmd)

		# reset active flag
		self.active = False

	def _format_value(self, value, type):
		"""\
		Internal: formats a parameter value based on type.
		"""
		if value is None:
			return None
		elif type is 'I':
			return int(value)
		elif type is 'S':
			return str(value)
		elif type is 'B':
			return ''
		else:
			return None