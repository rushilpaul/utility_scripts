#!/usr/bin/python

import sys, json, os, traceback
from urlparse import urlparse, parse_qs
import requests as R

if len(sys.argv) <= 1:
	print 'Usage:', sys.argv[0], '<CourseURL>'
	sys.exit(1)

courseId = sys.argv[1]
print 'Course to be downloaded', courseId

bearerToken = "Bearer ldNCv9Z2WZ7mEr2YpIo7Dxx9PJxop27hDyPf9cPA"
headers = { 'Authorization' : bearerToken, 'Cookie' : '__udmy_2_v57r=7ff20f2adf074b5c9072ae9d441d0ac0; ufb_acc="E0AecllSVw=="; _ga=GA1.2.1652209469.1545915786; _gid=GA1.2.1933479833.1546591936; intercom-session-sehj53dd=cncyZWlYbnlpaGhPaHFPNHFFMDhGdHVCQ0RrcFpPTWx5U3VESk9FKzBrQ1JBS0xyM1FaMW9ad0xJczRUWDc3cS0ta3kxM0JEcWVjaGZIS2JEUnZ5bUt1dz09--572e37ba14fcf5f8369c92b9837760ea86f06fc4' }

def downloadFile(url, fileName, depth):
	
	prefix = '\t' * depth

	if os.path.isfile(fileName):
		print prefix + 'File already exists. Skipping this'
		return

	resp = R.get(url, headers = headers)
	if not resp.ok:
		print prefix + 'Could not download file {0}. Status code {1}'.format(fileName, resp.status_code)
		return
	open(fileName, 'wb').write(resp.content)


# lectureNumber is used to order supplement assets within a chapter
def downloadSupplementAssets(courseId, lectureId, lectureNumber, assetId, chapterName, fileName):

	assetUrl = "https://cisco.udemy.com/api-2.0/users/me/subscribed-courses/{0}/lectures/{1}/supplementary-assets/{2}?fields[asset]=download_urls".format(courseId, lectureId, assetId)

	resp = R.get(assetUrl, headers = headers)
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
		downloadFile(fileUrl, os.path.join(chapterName, str(lectureNumber) + '. ' + fileName), 2)
		print '\t\tFinished downloading the supplementary file:', fileName


def downloadVideo(video, fileName):
	
	url = video['file']
	if(video['type'] == 'video/mp4'):
		fileName += '.mp4'
	else:
		print '\tNot sure what file extension to apply to ' + fileName

	print '\tStarted downloading video', fileName
	downloadFile(url, fileName, 1)
	print '\tFinished downloading video', fileName



# lectureNumber is used to order lectures within a chapter
def downloadLecture(courseId, lectureId, lectureNumber, chapterName):

	courseUrl = "https://cisco.udemy.com/api-2.0/users/me/subscribed-courses/{0}/lectures/{1}?fields%5Basset%5D=@min,download_urls,external_url,slide_urls,status,captions,thumbnail_url,time_estimation,stream_urls".format(courseId, lectureId)

	resp = R.get(courseUrl, headers = headers)
	if not resp.ok:
		print 'Could not get course details: ' + str(resp.status_code)
		return

	course = json.loads(resp.text)

	open('API_response_lectureId_' + lectureId, 'wb').write(json.dumps(course, indent = 4))

	fileName = str(course['title'])
	fileName = os.path.join(chapterName, str(lectureNumber) + '. ' + fileName)

	for video in course['asset']['stream_urls']['Video']:
		if video['label'] == '720':
			# start a separate thread probably
			downloadVideo(video, fileName)
			break


def start(courseId):

	courseUrl = "https://cisco.udemy.com/api-2.0/courses/{0}/cached-subscriber-curriculum-items/?page_size=140000&fields[lecture]=@min,object_index,asset,supplementary_assets,sort_order&fields[quiz]=@min,object_index,title,sort_order&fields[practice]=@min,object_index,title,sort_order&fields[chapter]=@min,object_index,title,sort_order&fields[asset]=@min,asset_type".format(courseId)

	resp = R.get(courseUrl, headers = headers)
	if not resp.ok:
		print 'Could not get course details: ' + str(resp.status_code)
		return None
	
	course = json.loads(resp.text)

	open('API_response_courseId_' + courseId, 'wb').write(json.dumps(course, indent = 4))

	if(course['next'] != None):
		print 'There are more sections that need to be fetched. This is not enough'

	count = course['count']
	print 'Total items to download', count

	entities = course['results']
	entities = sorted(entities, key = lambda x : x['sort_order'], reverse = True)
	
	chapterName = None
	lectureNumber = 1

	for i in range(count):

		entity = entities[i]
		eClass = entity['_class'].lower()

		if eClass == 'chapter':
			chapterName = entity['title']
			print ''
			try:
				os.mkdir(chapterName)
				print 'Directory for chapter {0} created'.format(chapterName)
				lectureNumber = 1

			except OSError as e:
				print 'Directory {0} already exists. Continuing anyway'.format(chapterName)

		elif eClass == 'lecture' and entity['asset']['asset_type'].lower() == 'video':
			lectureId = entity['id']
			try:
				downloadLecture(courseId, str(lectureId), lectureNumber, chapterName)
			except Exception as e:
				print '\tSomething went wrong while downloading lecture {0}'.format(entity['title'])
				print e
				print traceback.print_exc()

			# Find and download supplementary assets
			supAssets = entity['supplementary_assets']
			if supAssets != None and len(supAssets) > 0:
				for supAsset in supAssets:
					if supAsset['_class'].lower() == 'asset':
						downloadSupplementAssets(courseId, lectureId, lectureNumber, supAsset['id'], chapterName, supAsset['title'])

			lectureNumber += 1
			print ''	# new line


resp = start(courseId)
