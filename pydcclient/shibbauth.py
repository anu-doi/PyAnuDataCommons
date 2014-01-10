'''
Australian National University Data Commons
Copyright (C) 2013  The Australian National University

This file is part of Australian National University Data Commons.

Australian National University Data Commons is free software: you
can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

@author:Genevieve Turner <genevieve.turner@anu.edu.au>
'''

import http
import http.cookiejar
import urllib
import sys

from xml.etree import ElementTree as ET
from copy import  deepcopy

class MyCookieJar(http.cookiejar.MozillaCookieJar):
	"""
	Custom cookie jar subclassed from Mozilla because the file format
	stored is not useable by the libcurl libraries. See the comment below.
	"""
	def save(self, filename=None, ignore_discard=False, ignore_expires=False):
		if filename is None:
			if self.filename is not None: filename = self.filename
			else: raise ValueError(MISSING_FILENAME_TEXT)
		
		f = open(filename, "w")
		try:
			f.write(self.header)
			now = time.time()
			for cookie in self:
				if not ignore_discard and cookie.discard:
					inue
				if not ignore_expires and cookie.is_expired(now):
					continue
				if cookie.secure: secure = "TRUE"
				else: secure = "FALSE"
				if cookie.domain.startswith("."): initial_dot = "TRUE"
				else: initial_dot = "FALSE"
				if cookie.expires is not None:
					expires = str(cookie.expires)
				else:
					# change so that if a cookie does not have an expiration
					# date set it is saved with a '0' in that field instead
					# of a blank space so that the curl libraries can
					# read in and use the cookie
					#expires = ""
					expires = "0"
				if cookie.value is None:
					# cookies.txt regards 'Set-Cookie: foo' as a cookie
					# with no name, whereas cookielib regards it as a
					# cookie with no value.
					name = ""
					value = cookie.name
				else:
					name = cookie.name
					value = cookie.value
				f.write(
					"\t".join([cookie.domain, initial_dot, cookie.path,
							secure, expires, name, value])+
					"\n")
		finally:
			f.close()

class ShibbolethAuthentication:
	
	def get_shibboleth_cookies(idp_endpoint, sp_login_url, username, password, debug=False):
		cookie_jar = http.cookiejar.LWPCookieJar()
		cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
		
		httpsHandler = urllib.request.HTTPSHandler(debuglevel = 0)
		
		opener = urllib.request.build_opener(cookie_handler, httpsHandler)
		
		headers = {
					'Accept' :   'text/html; application/vnd.paos+xml',
					'PAOS'   :   'ver="urn:liberty:paos:2003-08";"urn:oasis:names:tc:SAML:2.0:profiles:SSO:ecp"'
					}
		
		request = urllib.request.Request(url=sp_login_url, headers=headers)
		
		try:
			response = opener.open(request)
		except Exception as e:
			print >>sys.stderr, "First request to SP failed: %s" % e
			sys.exit(1)
	    
		sp_response = ET.XML(response.read())
	    
		if debug: 
			print
			print("###### BEGIN SP RESPONSE")
			print
			print(ET.tostring(sp_response))
			print
			print("###### END SP RESPONSE")
			print
			
		namespaces = {
					'ecp' : 'urn:oasis:names:tc:SAML:2.0:profiles:SSO:ecp',
					'S'   : 'http://schemas.xmlsoap.org/soap/envelope/',
					'paos': 'urn:liberty:paos:2003-08'
					}
		
		ET.register_namespace("ecp", 'urn:oasis:names:tc:SAML:2.0:profiles:SSO:ecp')
		ET.register_namespace("S",'http://schemes.xmlsoap.org/soap/envelope/')
		ET.register_namespace("paos",'urn:libery:paos:2003-06')
		
		try:
			relay_state = sp_response.findall(".//ecp:RelayState", namespaces=namespaces)[0]
		except Exception as e:
			print("Unable to parse relay state element from SP response: ", e, file=sys.stderr)
			sys.exit(1)
		
		if debug:
			print
			print("###### BEGIN RELAY STATE ELEMENT")
			print(ET.tostring(relay_state))
			print
			print("###### END RELAY STATE ELEMENT")
			print
	
		# pick out the responseConsumerURL attribute so that it can
		# later be compared with the assertionConsumerURL sent by the IdP
		try:
			#TODO find out why we can't start with ./S:Envelope
			#response_consumer_url = sp_response.find("./S:Envelope/S:Header/paos:Request", namespaces=namespaces).attrib['responseConsumerURL']
			response_consumer_url = sp_response.find(".//S:Header/paos:Request", namespaces=namespaces).attrib['responseConsumerURL']
		except Exception as e:
			print("Unable to parse responseConsumerURL attribute from SP response: ", e, file=sys.stderr)
			sys.exit(1)
		
		if debug: 
			print
			print("###### BEGIN RESPONSE CONSUMER URL")
			print
			print(response_consumer_url)
			print
			print("###### END RESPONSE CONSUMER URL")
			print
	
		# make a deep copy of the SP response and then remove the header
		# in order to create the package for the IdP
		idp_request = deepcopy(sp_response)
		header = idp_request[0]
		idp_request.remove(header)
		
		if debug: 
			print
			print("###### BEGIN IDP REQUEST")
			print
			print(ET.tostring(idp_request))
			print
			print("###### END IDP REQUEST")
			print
	
	
	
		password_mgr = urllib.request.HTTPPasswordMgrWithDefaultRealm()
		password_mgr.add_password(None, idp_endpoint, username, password)
		auth_handler = urllib.request.HTTPBasicAuthHandler(password_mgr)
		opener.add_handler(auth_handler)
	
		# POST the request to the IdP 
		request = urllib.request.Request(idp_endpoint, data=ET.tostring(idp_request))
		request.get_method = lambda: 'POST'
	
		try:
			response = opener.open(request)
		except Exception as e:
			print >>sys.stderr, "Request to IdP failed: %s" % e
			sys.exit(1)
	
		idp_response = ET.XML(response.read())
		if debug: 
			print
			print("###### BEGIN IDP RESPONSE")
			print
			print(ET.tostring(idp_response))
			print
			print("###### END IDP RESPONSE")
			print
	
		try:
			#TODO find out why we can't use top level envelope
			#assertion_consumer_service =  idp_response.find("./S:Envelope/S:Header/ecp:Response", namespaces=namespaces).attrib('AssertionConsumerServiceURL')
			assertion_consumer_service =  idp_response.find(".//S:Header/ecp:Response", namespaces=namespaces).get('AssertionConsumerServiceURL')
		except Exception as e:
			print("Error parsing assertionConsumerService attribute from IdP response: ", e, file=sys.stderr)
			sys.exit(1)
	
		if debug: 
			print
			print("###### BEGIN ASSERTION CONSUMER SERVICE URL")
			print
			print(assertion_consumer_service)
			print
			print("###### END ASSERTION CONSUMER SERVICE URL")
			print
	
		# if the assertionConsumerService attribute from the IdP 
		# does not match the responseConsumerURL from the SP
		# we cannot trust this exchange so send SOAP 1.1 fault
		# to the SP and exit
		if assertion_consumer_service != response_consumer_url:
			print("ERROR: assertionConsumerServiceURL %s does not" % assertion_consumer_service, file=sys.stderr)
			print("match responseConsumerURL %s" % response_consumer_url, file=sys.stderr)
			print("", file=sys.stderr)
			print("sending SOAP fault to SP",file=sys.stderr)
			
			soap_fault = """
				<S:Envelope xmlns:S="http://schemas.xmlsoap.org/soap/envelope/">
					<S:Body>
						<S:Fault>
							<faultcode>S:Server</faultcode>
							<faultstring>responseConsumerURL from SP and assertionConsumerServiceURL from IdP do not match</faultstring>
						</S:Fault>
					</S:Body>
				</S:Envelope>
				"""
	
			headers = {
						'Content-Type' : 'application/vnd.paos+xml',
						}
			
			request = urllib.request.Request(url=response_consumer_url, data=soap_fault, headers=headers)
			request.get_method = lambda: 'POST'
	
			# POST the SOAP 1.1 fault to the SP and ignore any return 
			try:
				response = opener.open(request)
				
			except Exception as e:
				pass
	
			sys.exit(1)
	
		# make a deep cop of the IdP response and replace its
		# header contents with the relay state initially sent by
		# the SP
		sp_package = deepcopy(idp_response)
		sp_package[0][0] = relay_state 
	
		if debug: 
			print
			print("###### BEGIN PACKAGE TO SEND TO SP")
			print
			print(ET.tostring(sp_package))
			print
			print("###### END PACKAGE TO SEND TO SP")
			print
	
	
		headers = {
					'Content-Type' : 'application/vnd.paos+xml',
					}
	
		# POST the package to the SP
		request = urllib.request.Request(url=assertion_consumer_service, data=ET.tostring(sp_package), headers=headers)
		request.get_method = lambda: 'POST'
	
		try:
			response = opener.open(request)
		except Exception as e:
			print >>sys.stderr, "Error POSTing package to SP: %s" % e
			sys.exit(1)
			
		
		#return opener
		return cookie_jar

def main():
	
	cookie_jar = ShibbolethAuthentication.get_shibboleth_cookies('https://23wj72s.uds.anu.edu.au/idp/profile/SAML2/SOAP/ECP','https://23wj72s.uds.anu.edu.au/Shibboleth.sso/Login','myself','testpassword')
	cookie_handler = urllib.request.HTTPCookieProcessor(cookie_jar)
	
	httpsHandler = urllib.request.HTTPSHandler(debuglevel = 0)
	
	opener = urllib.request.build_opener(cookie_handler, httpsHandler)
	
	headers = {
				'Content-Type' : 'text/html',
				}
	request = urllib.request.Request(url='https://23wj72s.uds.anu.edu.au/DataCommons/rest/display/test:1?layout=def:display', headers=headers)
	
	try:
		response = opener.open(request)
	except Exception as e:
		print >>sys.stderr, "Error POSTing package to SP: %s" % e
		sys.exit(1)
	
	print(response.read())

if __name__ == "__main__":
	main()
