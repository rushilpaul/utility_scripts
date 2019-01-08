#!/usr/bin/python

import sys, json, os, traceback, string, ntpath, subprocess, re
from HTMLParser import HTMLParser
from urlparse import urlparse, parse_qs
import requests as R
from bs4 import BeautifulSoup as BS

if len(sys.argv) <= 1:
	print 'Usage:', sys.argv[0], '<CourseURL> [curl]'
	sys.exit(1)

courseUrl = sys.argv[1]
curlDownloader = False

if 'curl' in sys.argv[1:]:
	curlDownloader = True

apiResponseDataDir = 'API_Response_data_files'

userAgent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
cookieHeader = { 'user-agent' : userAgent, 'Cookie' : 'evi="Sg4="; ud_firstvisit=2018-12-27T12:33:57.933567+00:00:1gcUrN:k4bULZyPAfUW86rv24sm2PumCJk; __udmy_2_v57r=7ff20f2adf074b5c9072ae9d441d0ac0; csrftoken=sn6GifXnjFueMM5RL48p4SskEq9OYPIR2gpRtLHE4CLeewwf7ACt8CI7mYXWFp8A; dj_session_id=ruz3mfmod1fjcg0tekio3s68r9b00o67; client_id=bd2565cb7b0c313f5e9bae44961e8db2; ud_credit_last_seen=None; access_token=ldNCv9Z2WZ7mEr2YpIo7Dxx9PJxop27hDyPf9cPA; ufb_acc="E0AecllSVw=="; _ga=GA1.2.1652209469.1545915786; _ga=GA1.3.1652209469.1545915786; _pxvid=c0e48090-09d7-11e9-9950-31a50ec8e150; _gid=GA1.2.1933479833.1546591936; _gid=GA1.3.1933479833.1546591936; _ga=GA1.1.1652209469.1545915786; volume=0.5; mute=0; quality_1358570=720; _gid=GA1.1.1933479833.1546591936; playbackspeed=1.25; ud_rule_vars="eJyFjcsKwjAURH-lZKuRm9ukeXxLoMQ8JKgU09RN6b8biqI7V7OYOWdWUl25xBrD-MxzrlMxMiWEhC4kkPwsvAaJLurAOQvgPBg_TdccienIasnNzXUs8bHElsHVaFthCQJTlCFF2TE0fW-EPGkBrGcHAANgybGtUi6N2o__sci50r_sfuynpczxbaj5_jVoCozC0GEjtMHhJEAphR_DRrYXBlxHBA==:1ggEla:WmRwxhIvGVUVqkRJCF53Z9CwfkI"; intercom-session-sehj53dd=UGNFOFpha1cyTkcxczhQQ05EWWd6VWpadnQ2bk1oWHJ4S2xiMlMrWTRUdTFvcmptWmtnQTIyeFBnbGd2d3RMOS0tU29iNnN6VG8rcXNNbEd2SXBPWnB0QT09--a5601fe0f9f6e1216732e62c5fe0901d85d172c0; _px2=eyJ1IjoiM2U4MWNhMjAtMTFlZi0xMWU5LWEyMDgtZWRmMDNlYzAxZjQzIiwidiI6ImMwZTQ4MDkwLTA5ZDctMTFlOS05OTUwLTMxYTUwZWM4ZTE1MCIsInQiOjE1NDY4NTY5NDI2NzcsImgiOiJlMGIwNzIxYjc4N2UzMzEzNzY0Njg1ODIxNTM2MjJmNjBmMzdkOWY3OTI2NjkyODAwZGEzM2M5ODRlYTFkODczIn0=; _px3=790b62d9c2a894e53ab909c60d6e68bddd1e0f82043195999209f5c0b4a47aa5:ULdlsFxuhDKSe98LxwOEy0E3nyOEm4iUrJy7aBOveKQ0ElJB7nLEBEqg43vf9iUohUs6PqMBpMa68V6zLlIHxA==:1000:u9YpONsWr3o4UV0U6qE245LWfmiPdSEvAJ27Cqdc+K8LaxcWo0hyA8d7gfa099VhOsJYocdZuaZSlCvLjh20XaqumpLZ7g/6796tRMSemqc3S6631ZuBRRhOgCUXI2J+SzAhehuFKbfngEznyg4OHmDQ+QA3m2JiQHZxfEJ7aa4=; _gat_UA-12366301-43=1' };
bearerTokenHeader = { 'Authorization' : 'Bearer ldNCv9Z2WZ7mEr2YpIo7Dxx9PJxop27hDyPf9cPA' }
session = R.Session()

def formatFileName(fName):
    invalid_chars = "/\\:"
    finalName = ""
    for i in fName:
    	if i == ' ':
    		finalName += '-'
    	elif i in invalid_chars:
    		finalName += ' '
    	else:
    		finalName += i
    return finalName

def downloadFileUsingCurl(url, fileName, headers, depth):

	prefix = '\t' * depth

	if os.path.isfile(fileName):
		print prefix + 'File already exists. Skipping this'
		return

	args = []
	for h in headers:
		args.append('-H')
		args.append(h + ': ' + headers[h])

	subprocess.check_output(['curl'] + args + [url, '-o', fileName])

def downloadFile(url, fileName, headers, depth):
	
	if (curlDownloader):
		downloadFileUsingCurl(url, fileName, headers, depth)
		return

	prefix = '\t' * depth

	if os.path.isfile(fileName):
		print prefix + 'File already exists. Skipping this'
		return

	resp = session.get(url, headers = headers)
	if not resp.ok:
		print prefix + 'Could not download file "{0}" at "{1}". Status code {2}'.format(fileName, url, resp.status_code)
		print resp.content
		return False
	open(fileName, 'wb').write(resp.content)
	return True


def downloadAsset(assetId, assetName, lectureNumber, chapterName):

	print '\tDownloading asset', assetName
	assetUrl = "https://cisco.udemy.com/api-2.0/assets/{0}?fields[asset]=@min,status,delayed_asset_message,processing_errors,body".format(assetId)
	resp = session.get(assetUrl, headers = bearerTokenHeader)
	if not resp.ok:
		print '\tCould not retrieve asset details for asset', assetName
		return False

	resp = json.loads(resp.text)

	open(os.path.join(chapterName, str(lectureNumber) + '. ' + formatFileName(assetName)), 'w').write(resp['body'].encode('utf-8'))
	return True


# lectureNumber is used to order supplement assets within a chapter
def downloadSupplementAssets(courseId, lectureId, lectureNumber, assetId, chapterName, fileName):

	assetUrl = "https://cisco.udemy.com/api-2.0/users/me/subscribed-courses/{0}/lectures/{1}/supplementary-assets/{2}?fields[asset]=download_urls".format(courseId, lectureId, assetId)

	resp = session.get(assetUrl, headers = bearerTokenHeader)
	if not resp.ok:
		print '\t\tCould not retrieve supplementary asset details for asset', assetId
		return

	files = json.loads(resp.text)['download_urls']['File']	

	for f in files:
		fileUrl = f['file']
		if fileUrl == None:
			continue
		parsed = urlparse(fileUrl)
		try:
			newFileName = parse_qs(parsed.query)['filename'][0]
			if newFileName != None and len(newFileName) > 0:
				fileName = newFileName
		except:
			pass

		print '\t\tDownloading a supplementary file:', fileName
		if downloadFile(fileUrl, os.path.join(chapterName, str(lectureNumber) + '. ' + formatFileName(fileName)), cookieHeader, 2):
			print '\t\tFinished downloading the supplementary file:', fileName


def downloadVideo(video, fileName):
	
	url = video['file']
	if(video['type'] == 'video/mp4'):
		fileName += '.mp4'
	else:
		print '\tNot sure what file extension to apply to ' + fileName

	print '\tStarted downloading video "{0}"'.format(ntpath.basename(fileName))
	if downloadFile(url, fileName, cookieHeader, 1):
		print '\tFinished downloading video "{0}"'.format(ntpath.basename(fileName))



# lectureNumber is used to order lectures within a chapter
def downloadVideoLecture(courseId, lectureId, lectureNumber, chapterName):

	courseUrl = "https://cisco.udemy.com/api-2.0/users/me/subscribed-courses/{0}/lectures/{1}?fields%5Basset%5D=@min,download_urls,external_url,slide_urls,status,captions,thumbnail_url,time_estimation,stream_urls".format(courseId, lectureId)

	resp = session.get(courseUrl, headers = bearerTokenHeader)
	if not resp.ok:
		print 'Could not get course details: ' + str(resp.status_code)
		return

	course = json.loads(resp.text)

	open(os.path.join(apiResponseDataDir, 'API_response_lectureId_' + lectureId + '.json'), 'wb').write(json.dumps(course, indent = 4))

	fileName = course['title'].encode('utf-8')
	fileName = os.path.join(chapterName, str(lectureNumber) + '. ' + formatFileName(fileName))

	for video in course['asset']['stream_urls']['Video']:
		if video['label'] == '720':
			# start a separate thread probably
			downloadVideo(video, fileName)
			break


def start(courseId):

	try:
		os.mkdir(apiResponseDataDir)
	except:
		pass

	courseUrl = "https://cisco.udemy.com/api-2.0/courses/{0}/cached-subscriber-curriculum-items/?page_size=140000&fields[lecture]=@min,object_index,asset,supplementary_assets,sort_order&fields[quiz]=@min,object_index,title,sort_order&fields[practice]=@min,object_index,title,sort_order&fields[chapter]=@min,object_index,title,sort_order&fields[asset]=@min,asset_type".format(courseId)

	resp = session.get(courseUrl, headers = bearerTokenHeader)

	if not resp.ok:
		print 'Could not get course details: ' + str(resp.status_code)
		print resp.text
		print 'Are you enrolled for this course?'
		return None
	
	course = json.loads(resp.text)

	open(os.path.join(apiResponseDataDir, 'API_response_courseId_' + courseId + '.json'), 'wb').write(json.dumps(course, indent = 4))

	if(course['next'] != None):
		print 'There are more sections that need to be fetched. This is not enough'

	count = course['count']
	print 'Total items to download', count

	entities = course['results']
	entities = sorted(entities, key = lambda x : x['sort_order'], reverse = True)
	
	chapterName = None
	lectureNumber = 1
	chapterNumber = 1

	for entity in entities:

		eClass = entity['_class'].lower()
		if 'asset' in entity:
			asset = entity['asset']
		else:
			asset = None

		if eClass == 'chapter':
			chapterName = str(chapterNumber) + '. ' + entity['title'].encode('utf-8').strip()
			lectureNumber = 1
			chapterNumber += 1
			print ''
			try:
				os.mkdir(chapterName)
				print 'Directory for chapter "{0}" created'.format(chapterName)

			except OSError as e:
				print 'Directory "{0}" already exists. Continuing anyway'.format(chapterName)

		elif eClass == 'lecture':

			if asset != None and asset['asset_type'].lower() == 'video':

				lectureId = str(entity['id'])
				downloadVideoLecture(courseId, lectureId, lectureNumber, chapterName)

				# Find and download supplementary assets
				supAssets = entity['supplementary_assets']
				if supAssets != None and len(supAssets) > 0:
					for supAsset in supAssets:
						if supAsset['_class'].lower() == 'asset' and supAsset['asset_type'].lower() == 'file':
							downloadSupplementAssets(courseId, lectureId, lectureNumber, supAsset['id'], chapterName, fileName = supAsset['title'])

			elif asset != None and asset['asset_type'].lower() == 'article':
				downloadAsset(str(asset['id']), entity['title'], lectureNumber, chapterName)

			lectureNumber += 1
			print ''	# new line


def enrollInCourse(courseId):

	url = "https://cisco.udemy.com/course/subscribe/?courseId={0}".format(courseId)

	resp = sendRequestWithRedirect(url)
	if not resp.ok:
		print 'Could not enroll in course! Response code:', resp.status_code
		print resp.text
		return

	print 'Successfully enrolled in course', courseId


def findCourseId(url):

	resp = sendRequestWithRedirect(url)
	if not resp.ok:
		return None

	soup = BS(resp.text, features = 'html.parser')

	try:
		# Assume user is enrolled in the course
		text = soup.select('div[ng-init]')[0].get('ng-init')
		x = re.search('\\d+', re.search('"id"\\s?:\\s?\\d+', text).group(0))
		return x.group(0).encode('utf-8')
	except:
		# User is probably not enrolled
		try:
			return soup.find('body').get('data-clp-course-id').encode('utf-8')
		except:
			return None
	

def sendRequestWithRedirect(url):

	resp = None
	while True:
	
		print 'Getting', url
		resp = session.get(url, headers = cookieHeader, allow_redirects = False)
		print resp.status_code
		if not resp.ok:
			print 'Request to the server failed at', url
			break
		if resp.status_code / 100 == 3:
			url = 'https://cisco.udemy.com' + resp.headers['Location']
		elif resp.status_code / 100 == 2:
			break
		else:
			print 'Request to the server failed at', url
			break
	return resp


courseId = findCourseId(courseUrl)
if courseId == None:
	print 'Could not find courseId from the URL', courseUrl
	sys.exit(2)

enrollInCourse(courseId)
start(courseId)

