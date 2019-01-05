#!/usr/bin/python

import sys, json, os, traceback, string, ntpath
from urlparse import urlparse, parse_qs
import requests as R

if len(sys.argv) <= 1:
	print 'Usage:', sys.argv[0], '<CourseURL>'
	sys.exit(1)

courseId = sys.argv[1]
apiResponseDataDir = 'API_Response_data_files'

cookieHeader = { 'Cookie' : '__udmy_2_v57r=7ff20f2adf074b5c9072ae9d441d0ac0; ufb_acc="E0AecllSVw=="; _ga=GA1.2.1652209469.1545915786; _gid=GA1.2.1933479833.1546591936; intercom-session-sehj53dd=cncyZWlYbnlpaGhPaHFPNHFFMDhGdHVCQ0RrcFpPTWx5U3VESk9FKzBrQ1JBS0xyM1FaMW9ad0xJczRUWDc3cS0ta3kxM0JEcWVjaGZIS2JEUnZ5bUt1dz09--572e37ba14fcf5f8369c92b9837760ea86f06fc4' }
bearerTokenHeader = { 'Authorization' : 'Bearer ldNCv9Z2WZ7mEr2YpIo7Dxx9PJxop27hDyPf9cPA' }

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

def downloadFile(url, fileName, headers, depth):
	
	prefix = '\t' * depth

	if os.path.isfile(fileName):
		print prefix + 'File already exists. Skipping this'
		return

	resp = R.get(url, headers = headers)
	if not resp.ok:
		print prefix + 'Could not download file "{0}" at "{1}". Status code {2}'.format(fileName, url, resp.status_code)
		print resp.content
		return False
	open(fileName, 'wb').write(resp.content)
	return True


def downloadAsset(assetId, assetName, lectureNumber, chapterName):

	print '\tDownloading asset', assetName
	assetUrl = "https://cisco.udemy.com/api-2.0/assets/{0}?fields[asset]=@min,status,delayed_asset_message,processing_errors,body".format(assetId)
	resp = R.get(assetUrl, headers = bearerTokenHeader)
	if not resp.ok:
		print '\tCould not retrieve asset details for asset', assetName
		return False

	hresp = json.loads(resp.text)

	open(os.path.join(chapterName, str(lectureNumber) + '. ' + formatFileName(assetName)), 'w').write(resp['body'].encode('utf-8'))
	return True


# lectureNumber is used to order supplement assets within a chapter
def downloadSupplementAssets(courseId, lectureId, lectureNumber, assetId, chapterName, fileName):

	assetUrl = "https://cisco.udemy.com/api-2.0/users/me/subscribed-courses/{0}/lectures/{1}/supplementary-assets/{2}?fields[asset]=download_urls".format(courseId, lectureId, assetId)

	resp = R.get(assetUrl, headers = bearerTokenHeader)
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

	resp = R.get(courseUrl, headers = bearerTokenHeader)
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

	courseUrl = "https://cisco.udemy.com/api-2.0/courses/{0}/cached-subscriber-curriculum-items/?page_size=140000&fields[lecture]=@min,object_index,asset,supplementary_assets,sort_order&fields[quiz]=@min,object_index,title,sort_order&fields[practice]=@min,object_index,title,sort_order&fields[chapter]=@min,object_index,title,sort_order&fields[asset]=@min,asset_type".format(courseId)

	resp = R.get(courseUrl, headers = bearerTokenHeader)
	if not resp.ok:
		print 'Could not get course details: ' + str(resp.status_code)
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


try:
	os.mkdir(apiResponseDataDir)
except:
	pass

print 'Course to be downloaded', courseId
start(courseId)

