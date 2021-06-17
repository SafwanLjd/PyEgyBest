from base64 import urlsafe_b64decode as decode
from strsimpy.levenshtein import Levenshtein
from js2py import eval_js as executeJS
from bs4 import BeautifulSoup
import requests
import re


def search(query, includeShows=True, includeMovies=True):
	resultsList = []
	try:
		content = requests.get(f'https://egy.best/explore/?q={query}\u0020', allow_redirects=True).text
		soup = BeautifulSoup(content, features='html.parser')

		if soup.body is not None:
			searchResults = soup.body.find('div', attrs={'id': 'movies', 'class': 'movies'}).findAll('a')

			for result in searchResults:
				isButton = ' '.join(result.get('class')) == "auto load btn b"
				if not isButton:
					link = BeautifulSoup(str(result), features='html.parser').a.get('href')
					title = result.find('span', attrs={'class': 'title'}).text
					posterURL = result.find('img').get('src')

					try:
						rating = result.find('i', attrs={'class': 'i-fav rating'}).text
					except Exception as exception:
						rating = None

					if link.split('/')[3] == 'series' and includeShows:
						resultsList.append(Show(link, title, posterURL, rating))
					elif link.split('/')[3] == 'movie' and includeMovies:
						resultsList.append(Episode(link, title, posterURL, rating))

			resultsList.sort(key=lambda element: Levenshtein().distance(query, element.title))

	except Exception as excepttion:
		print(excepttion)

	return resultsList


class Show:
	def __init__(self, link, title=None, posterURL=None, rating=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.rating = rating
		self.seasonsList = []
	
	def getSeasons(self):
		try:
			series = requests.get(self.link).text
			soup = BeautifulSoup(series, features='html.parser')

			if soup.body is not None:
				seasons = soup.body.find('div', attrs={'class': 'contents movies_small'}).findAll('a')

				for season in seasons:
					seasonLink = BeautifulSoup(str(season), features='html.parser').a.get('href')
					seasonTitle = season.find('span', attrs={'class': 'title'}).text
					seasonPosterURL = season.find('img').get('src')

					self.seasonsList.insert(0, Season(seasonLink, seasonTitle, seasonPosterURL))
					
		except Exception as excepttion:
			print(excepttion)

		return self.seasonsList

class Season:
	def __init__(self, link, title=None, posterURL=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.episodesList = []
	
	def getEpisodes(self):
		try:
			season = requests.get(self.link).text
			soup = BeautifulSoup(season, features='html.parser')

			if soup.body is not None:
				episodes = soup.body.find('div', attrs={'class': 'movies_small'}).findAll('a')

				for episode in episodes:
					episodeLink = BeautifulSoup(str(episode), features='html.parser').a.get('href')
					episodeTitle = episode.find('span', attrs={'class': 'title'}).text
					episodePosterURL = episode.find('img').get('src')
					
					try:
						episodeRating = episode.find('i', attrs={'class': 'i-fav rating'}).text
					except Exception as exception:
						episodeRating = None

					self.episodesList.insert(0, Episode(episodeLink, episodeTitle, episodePosterURL, episodeRating))
					
		except Exception as excepttion:
			print(excepttion)

		return self.episodesList

class Episode:
	def __init__(self, link, title=None, posterURL=None, rating=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.rating = rating
		self.downloadLinksList = []

	def getDownloadSources(self):
		try:
			session = requests.Session()

			baseURL = self.link.split('/')[0] + "//" + self.link.split('/')[2]

			episode = session.get(self.link).text
			episodeSoup = BeautifulSoup(episode, features='html.parser')

			vidstreamURL = baseURL + episodeSoup.body.find('iframe', attrs={'class': 'auto-size'}).get('src')

			vidstreamResponse = session.get(vidstreamURL).text
			videoSoup = BeautifulSoup(vidstreamResponse, features='html.parser')

			try:
				qualityLinksFileURL = baseURL + videoSoup.body.find('source').get('src')
			except Exception:
				jsCode = str(videoSoup.find_all('script')[1])

				verificationToken = str(re.findall("\{'[0-9a-zA-Z_]*':'ok'\}", jsCode)[0][2:-7])
				encodedAdLinkVar = re.findall("\([0-9a-zA-Z_]{2,12}\[Math", jsCode)[0][1:-5]
				firstEncodingArray = re.findall(",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[1][1:-3]
				secondEncodingArray = re.findall(",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[2][1:-3]

				jsCode = re.sub('^<script type="text/javascript">', "", jsCode)
				jsCode = re.sub("[;,]\$\('\*'\)(.*)$", ";", jsCode)
				jsCode = re.sub(",ismob=(.*)\(navigator\[(.*)\]\)[,;]", ";", jsCode)
				jsCode = re.sub("var a0b=function\(\)(.*)a0a\(\);", "", jsCode)
				jsCode += "var link = ''; for (var i = 0; i <= " + secondEncodingArray + "['length']; i++) { link += " + firstEncodingArray + "[" + secondEncodingArray + "[i]] || ''; } return [link, " + encodedAdLinkVar + "[0]] }"

				jsCodeReturn = executeJS(jsCode)()
				verificationPath = jsCodeReturn[0]
				encodedAdPath = jsCodeReturn[1]

				adLink = baseURL + "/" + str(decode(encodedAdPath + '=' * (-len(encodedAdPath) % 4)), "utf-8")
				session.get(adLink)

				verificationLink = baseURL + "/tvc.php?verify=" + verificationPath
				session.post(verificationLink, data={verificationToken: 'ok'})

				vidstreamResponse = session.get(vidstreamURL).text
				videoSoup = BeautifulSoup(vidstreamResponse, features='html.parser')

				qualityLinksFileURL = baseURL + videoSoup.body.find('source').get('src')

			qualityLinks = session.get(qualityLinksFileURL).text
			qualityLinksArray = qualityLinks.split('\n')[1::]

			for i in range(0, len(qualityLinksArray)-2, 2):
				qualityInfo = qualityLinksArray[i]
				link = qualityLinksArray[i+1].replace("/stream/", "/dl/")
				qualityRegEx = "[0-9]{3,4}x[0-9]{3,4}"
				quality = self.__roundQuality(int(re.search(qualityRegEx, qualityInfo)[0].split('x')[1]))
				fileName = self.link.split('/')[4] + "-" + str(quality) + "p.mp4"

				self.downloadLinksList.append(DownloadSource(link, quality, fileName))
		except Exception as exception:
			print(exception)

		return self.downloadLinksList

	def __roundQuality(self, originalQuality):
		qualities = [2160, 1080, 720, 480, 360, 240]
		lastDifference = abs(qualities[0] - originalQuality)

		roundedQuality = qualities[0]
		for quality in qualities:
			difference = abs(quality - originalQuality)
			if difference < lastDifference:
				lastDifference = difference
				roundedQuality = quality
		return roundedQuality

class DownloadSource:
	def __init__(self, link, quality=None, fileName=None):
		self.link = link
		self.quality = quality
		self.fileName = fileName
