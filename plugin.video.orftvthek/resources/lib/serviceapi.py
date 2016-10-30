#!/usr/bin/python
# -*- coding: utf-8 -*-
import urllib,urllib2,re,xbmcplugin,xbmcgui,sys,xbmcaddon,base64,socket,datetime,time,os,os.path,urlparse,json
import CommonFunctions as common

import Settings
from base import *
from Scraper import *

class serviceAPI(Scraper):

	__urlBase       = 'https://api-tvthek.orf.at/api/v3/'
	__urlLive       = __urlBase + 'livestreams/24hours?limit=1000'
	__urlMostViewed = __urlBase + 'page/startpage'
	__urlNewest     = __urlBase + 'page/startpage/newest'
	__urlSearch     = __urlBase + 'search/%s?limit=1000'
	__urlShows      = __urlBase + 'profiles?limit=1000'
	__urlTips       = __urlBase + 'page/startpage/tips'
	__urlTopics     = __urlBase + 'topics/overview?limit=1000'

	serviceAPIEpisode    = __urlBase + 'episode/%s'
	serviceAPIDate       = __urlBase + 'schedule/%s?limit=1000'
	serviceAPIDateFrom   = __urlBase + 'schedule/%s/%d?limit=1000'
	serviceAPIProgram    = __urlBase + 'profile/%s/episodes'
	servieAPITopic       = __urlBase + 'topic/%s'
	serviceAPITrailers   = __urlBase + 'page/preview?limit=100'
	serviceAPIHighlights = __urlBase + 'page/startpage'


	def __init__(self,xbmc,settings,pluginhandle,quality,protocol,delivery,defaultbanner,defaultbackdrop,useSubtitles,defaultViewMode):
		self.translation = settings.getLocalizedString
		self.xbmc = xbmc
		self.defaultViewMode = defaultViewMode
		self.videoQuality = quality
		self.videoDelivery = delivery
		self.videoProtocol = protocol
		self.pluginhandle = pluginhandle
		self.defaultbanner = defaultbanner
		self.defaultbackdrop = defaultbackdrop
		self.useSubtitles = useSubtitles
		self.xbmc.log(msg='ServiceAPI  - Init done', level=xbmc.LOGDEBUG);


	def getHighlights(self):
		try:
			response = self.__makeRequest(self.serviceAPIHighlights)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for result in json.loads(response.read()).get('highlight_teasers'):
				if result.get('target').get('model') == 'Segment':
					self.JSONSegment2ListItem(result.get('target'))


	def getMostViewed(self):
		try:
			response = self.__makeRequest(self.__urlMostViewed)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for result in json.loads(response.read()).get('most_viewed_segments'):
				if result.get('model') == 'Segment':
					self.JSONSegment2ListItem(result)


	def getNewest(self):
		self.getTableResults(self.__urlNewest)


	def getTips(self):
		self.getTableResults(self.__urlTips)


	def getTableResults(self, urlAPI):
		try:
			response = self.__makeRequest(urlAPI)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for result in json.loads(response.read()):
				if result.get('model') == 'Episode':
					self.__JSONEpisode2ListItem(result)
				elif result.get('model') == 'Tip':
					self.__JSONVideoItem2ListItem(result.get('_embedded').get('video_item'))

		else:
			self.xbmc.log(msg='ServiceAPI no available ... switch back to HTML Parsing in the Addon Settings', level=xbmc.LOGDEBUG);
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )


	# Useful  Methods for JSON Parsing
	def JSONSegment2ListItem(self,JSONSegment):
		title        = JSONSegment.get('title').encode('UTF-8')
		image        = self.JSONImage(JSONSegment.get('_embedded').get('image'))
		description  = JSONSegment.get('description')
		duration     = JSONSegment.get('duration_seconds')
		date         = time.strptime(JSONSegment.get('episode_date')[0:19], '%Y-%m-%dT%H:%M:%S')
		streamingURL = self.JSONStreamingURL(JSONSegment.get('sources'))
		return [streamingURL, createListItem(title, image, description, duration, time.strftime('%Y-%m-%d', date), '', streamingURL, 'true', False, self.defaultbackdrop,self.pluginhandle)]


	def JSONImage(self,jsonImages, name = 'image_full'):
		return jsonImages.get('public_urls').get('highlight_teaser').get('url')

	def JSONStreamingURL(self,jsonVideos):
		source = None
		if jsonVideos.get('progressive_download') != None:
			for streamingUrl in jsonVideos.get('progressive_download'):
				if streamingUrl.get('quality_key') == self.videoQuality:
					return streamingUrl.get('src')
				source = streamingUrl.get('src')
			
		for streamingUrl in jsonVideos.get('hls'):
			if streamingUrl.get('quality_key') == self.videoQuality:
				return streamingUrl.get('src')
			source = streamingUrl.get('src')
		return source

	# list all Categories
	def getCategories(self):
		try:
			response = self.__makeRequest(self.__urlShows)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for result in json.loads(response.read()).get('_embedded').get('items'):
				self.__JSONProfile2ListItem(result)
		else:
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )


	# list all Episodes for the given Date
	def getDate(self, date, dateFrom = None):
		if dateFrom == None:
			url = self.serviceAPIDate % date
		else:
			url = self.serviceAPIDateFrom % (date, 7)
		response = self.__makeRequest(url)

		episodes = json.loads(response.read()).get('_embedded').get('items')
		if dateFrom != None:
			episodes = reversed(episodes)

		for episode in episodes:
			self.__JSONEpisode2ListItem(episode)


	# list all Entries for the given Topic
	def getTopic(self,topicID):
		response = self.__makeRequest(self.servieAPITopic % topicID)
		for entrie in json.loads(response.read()).get('_embedded').get('video_items'):
			self.__JSONVideoItem2ListItem(entrie)


	# list all Episodes for the given Broadcast
	def getProgram(self,programID,playlist):
		response = self.__makeRequest(self.serviceAPIProgram % programID)
		responseCode = response.getcode()

		if responseCode == 200:
			episodes = json.loads(response.read()).get('_embedded').get('items')
			if len(episodes) == 1:
				for episode in episodes:
					self.getEpisode(episode.get('id'), playlist)
					return

			for episode in episodes:
				self.__JSONEpisode2ListItem(episode, 'teaser')
		else:
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )


	# listst all Segments for the Episode with the given episodeID
	# If the Episode only contains one Segment, that get played instantly.
	def getEpisode(self,episodeID,playlist):
		playlist.clear()

		response = self.__makeRequest(self.serviceAPIEpisode % episodeID)
		result = json.loads(response.read())

		title       = result.get('title').encode('UTF-8')
		image       = self.JSONImage(result.get('_embedded').get('image'))
		description = result.get('description').encode('UTF-8') if result.get('description') != None else result.get('description')
		duration    = result.get('duration_seconds')
		date        = time.strptime(result.get('date')[0:19], '%Y-%m-%dT%H:%M:%S')

		if len(result.get('_embedded').get('segments')) == 1:
			listItem = self.JSONSegment2ListItem(result.get('_embedded').get('segments')[0])
			playlist.add(listItem[0], listItem[1])

		else:
			parameters = {'mode' : 'playlist'}
			u = sys.argv[0] + '?' + urllib.urlencode(parameters)
			createListItem('[ '+(self.translation(30015)).encode('UTF-8')+' ]', image, '%s\n%s' % ((self.translation(30015)).encode('UTF-8'), description), duration, time.strftime('%Y-%m-%d', date), result.get('_embedded').get('channel').get('name'), u, 'false', False, self.defaultbackdrop,self.pluginhandle)

			for segment in result.get('_embedded').get('segments'):
				listItem = self.JSONSegment2ListItem(segment)
				playlist.add(listItem[0], listItem[1])

	# Parses the Topic Overview Page
	def getThemen(self):
		try:
			response = self.__makeRequest(self.__urlTopics)
			responseCode = response.getcode()
		except ValueError, error:
			responseCode = 404
			pass
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for topic in json.loads(response.read()).get('_embedded').get('items'):
				title       = topic.get('title').encode('UTF-8')
				description = topic.get('description')
				link        = topic.get('id')
				addDirectory(title, None, self.defaultbackdrop, description, link, 'openTopic', self.pluginhandle)

		else:
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )


	# list all Trailers for further airings
	def getTrailers(self):
		try:
			response = self.__makeRequest(self.serviceAPITrailers)
			responseCode = response.getcode()
		except ValueError, error:
			responseCode = 404
			pass
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for episode in json.loads(response.read())['_embedded']['items']:
				self.__JSONEpisode2ListItem(episode)
		else:
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )


	# lists archiv overview (date listing)
	def getArchiv(self):
		for x in xrange(9):
			date  = datetime.datetime.now() - datetime.timedelta(days=x)
			title = '%s' % (date.strftime('%A, %d.%m.%Y'))
			parameters = {'mode' : 'openDate', 'link': date.strftime('%Y-%m-%d')}
			if x == 8:
				title = 'älter als %s' % title
				parameters = {'mode' : 'openDate', 'link': date.strftime('%Y-%m-%d'), 'from': (date - datetime.timedelta(days=150)).strftime('%Y-%m-%d')}
			u = sys.argv[0] + '?' + urllib.urlencode(parameters)
			createListItem(title, None, None, None, date.strftime('%Y-%m-%d'), '', u, 'False', True, self.defaultbackdrop,self.pluginhandle)

	# Returns Live Stream Listing
	def getLiveStreams(self):
		try:
			response = self.__makeRequest(self.__urlLive)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			for result in json.loads(response.read()).get('_embedded').get('items'):
				description     = result.get('description')
				program         = result.get('_embedded').get('channel').get('reel').upper()
				programName     = result.get('_embedded').get('channel').get('name')
				livestreamStart = time.strptime(result.get('start')[0:19], '%Y-%m-%dT%H:%M:%S')
				livestreamEnd   = time.strptime(result.get('end')[0:19],   '%Y-%m-%dT%H:%M:%S')
				duration        = max(time.mktime(livestreamEnd) - max(time.mktime(livestreamStart), time.mktime(time.localtime())), 1)

				# already playing
				if livestreamStart < time.localtime():
					link = self.JSONStreamingURL(result.get('sources'))
				else:
					link = sys.argv[0] + '?' + urllib.urlencode({'mode': 'liveStreamNotOnline', 'link': result.get('id')})

				title = "[%s] %s (%s)" % (programName, result.get('title'), time.strftime('%H:%M', livestreamStart))

				banner = self.JSONImage(result.get('_embedded').get('image'))

				createListItem(title, banner, description, duration, time.strftime('%Y-%m-%d', livestreamStart), programName, link, 'True', False, self.defaultbackdrop, self.pluginhandle)
		else:
			xbmc.executebuiltin('XBMC.Notification("%s", "%s", %s)' % ( (self.translation(30045)).encode("utf-8"), (self.translation(30046)).encode("utf-8"), "") )

	def getLiveNotOnline(self,link):
		try:
			response = self.__makeRequest(self.__urlBase + 'livestream/' + link)
			responseCode = response.getcode()
		except urllib2.HTTPError, error:
			responseCode = error.getcode()
			pass

		if responseCode == 200:
			result = json.loads(response.read())

			title       = result.get('title').encode('UTF-8')
			image       = self.JSONImage(result.get('_embedded').get('image'))
			description = result.get('description')
			duration    = result.get('duration_seconds')
			date        = time.strptime(result.get('start')[0:19], '%Y-%m-%dT%H:%M:%S')

			dialog = xbmcgui.Dialog()
			if dialog.yesno((self.translation(30030)).encode("utf-8"), ((self.translation(30031)).encode("utf-8")+" %s.\n"+(self.translation(30032)).encode("utf-8")) % time.strftime('%H:%M', date)):
				sleepTime = int(time.mktime(date) - time.mktime(time.localtime()))
				dialog.notification((self.translation(30033)).encode("utf-8"), '%s %s' % ((self.translation(30034)).encode("utf-8"),sleepTime))
				self.xbmc.sleep(sleepTime * 1000)
				if dialog.yesno('', (self.translation(30035)).encode("utf-8")):
					streamingURL = link = self.JSONStreamingURL(result.get('sources'))
					listItem = createListItem(title, image, description, duration, time.strftime('%Y-%m-%d', date), result.get('_embedded').get('channel').get('name'), streamingURL, 'true', False, self.defaultbackdrop, self.pluginhandle)
					self.xbmc.Player().play(streamingURL, listItem)


	def __makeRequest(self, url):
		request = urllib2.Request(url)
		request.add_header('Authorization', 'Basic %s' % 'cHNfYW5kcm9pZF92Mzo2YTYzZDRkYTI5YzcyMWQ0YTk4NmZkZDMxZWRjOWU0MQ==')
		return urllib2.urlopen(request)


	def __JSONEpisode2ListItem(self, JSONEpisode, ignoreEpisodeType = None):
		# Direcotory should be set to False, that the Duration is shown, but then there is an error with the Pluginhandle
		createListItem(
			JSONEpisode.get('title'),
			self.JSONImage(JSONEpisode.get('_embedded').get('image')),
			JSONEpisode.get('description'),
			JSONEpisode.get('duration_seconds'),
			time.strftime('%Y-%m-%d', time.strptime(JSONEpisode.get('date')[0:19], '%Y-%m-%dT%H:%M:%S')),
			JSONEpisode.get('_embedded').get('channel').get('name') if JSONEpisode.get('_embedded').get('channel') != None else None,
			sys.argv[0] + '?' + urllib.urlencode({'mode' : 'openEpisode', 'link': JSONEpisode.get('id')}),
			'False',
			True,
			self.defaultbackdrop,
			self.pluginhandle,
		)


	def __JSONProfile2ListItem(self, jsonProfile):
		createListItem(
			jsonProfile.get('title'),
			self.JSONImage(jsonProfile.get('_embedded').get('image')),
			jsonProfile.get('description'),
			None,
			None,
			None,
			sys.argv[0] + '?' + urllib.urlencode({'mode' : 'openProgram', 'link': jsonProfile.get('id')}),
			'False',
			True,
			self.defaultbackdrop,
			self.pluginhandle
		)


	def __JSONVideoItem2ListItem(self, jsonVideoItem):
		if jsonVideoItem.get('_embedded').get('episode') != None:
			self.__JSONEpisode2ListItem(jsonVideoItem.get('_embedded').get('episode'))
		elif jsonVideoItem.get('_embedded').get('segment') != None:
			self.JSONSegment2ListItem(jsonVideoItem.get('_embedded').get('segment'))
