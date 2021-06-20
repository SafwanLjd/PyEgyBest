from base64 import urlsafe_b64decode as decode
from strsimpy.levenshtein import Levenshtein
from js2py import eval_js as executeJS
from bs4 import BeautifulSoup
import requests
import re


def search(query, includeShows=True, includeMovies=True, timeout=30, retries=1):
	searchURL = f"https://egy.best/explore/?q={query}%20"
	searchResponse = None
	resultsList = []
	
	try:
		if retries > 0:
			searchResponse = requests.get(searchURL, timeout=timeout)
			
			content = searchResponse.text
			soup = BeautifulSoup(content, features="html.parser")

			mvoiesClass = soup.body.find(attrs={"id": "movies", "class": "movies"})
			searchResults = mvoiesClass.findAll("a")

			for result in searchResults:
				if " ".join(result.get("class")) == "auto load btn b":
					continue

				link = result.get("href")
				
				titleClass = result.find(attrs={"class": "title"})
				title = titleClass.text if titleClass else None

				imgTag = result.find("img")
				posterURL = imgTag.get("src") if imgTag else None
				
				ratingClass = result.find(attrs={"class": "i-fav rating"})
				rating = ratingClass.text if ratingClass else None

				if link.split("/")[3] == "series" and includeShows:
					resultsList.append(Show(link, title, posterURL, rating))
				elif link.split("/")[3] == "movie" and includeMovies:
					resultsList.append(Episode(link, title, posterURL, rating))

			resultsList.sort(key=lambda element: Levenshtein().distance(query, element.title))

	except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
		print("Could Not Connect to Host: " + searchResponse.url.split("/")[2])
		return search(query, includeMovies=includeMovies, includeShows=includeShows, timeout=(timeout + 1), retries=(retries - 1))
	
	finally:
		return resultsList


class Show:
	def __init__(self, link, title=None, posterURL=None, rating=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.rating = rating
		self.seasonsList = []

		soup = None
		try:
			showPage = requests.get(self.link).text
			soup = BeautifulSoup(showPage, features="html.parser")

		finally:
			self.soup = soup

	def getSeasons(self):
		try:
			seasons = self.soup.body.find(attrs={"class": "contents movies_small"}).findAll("a")
			for season in seasons:
				seasonLink = season.get("href")
				
				titleClass = season.find(attrs={"class": "title"})
				seasonTitle = titleClass.text if titleClass else None
				
				imgTag = season.find("img")
				seasonPosterURL = imgTag.get("src") if imgTag else None

				self.seasonsList.insert(0, Season(seasonLink, seasonTitle, seasonPosterURL))

		finally:
			return self.seasonsList

	def refreshMetadata(self, posterOnly=False):
		title = self.title
		posterURL = self.posterURL
		rating = self.rating

		try:
			if not posterOnly:
				name = self.soup.body.find(attrs={"itemprop": "name"})
				if name:
					title = name.text

				ratingValue = self.soup.body.find(attrs={"itemprop": "ratingValue"})
				if ratingValue:
					rating = ratingValue.text

			imgClass = self.soup.body.find(attrs={"class": "movie_img"})
			if imgClass:
				imgTag = imgClass.find("img")
				if imgTag:
					posterURL = imgTag.get("src")

		finally:
			self.title = title
			self.posterURL = posterURL
			self.rating = rating


class Season:
	def __init__(self, link, title=None, posterURL=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.episodesList = []

		soup = None
		try:
			showPage = requests.get(self.link).text
			soup = BeautifulSoup(showPage, features="html.parser")

		finally:
			self.soup = soup

	def getEpisodes(self):
		try:
			episodes  = self.soup.body.find(attrs={"class": "movies_small"}).findAll("a")
			for episode in episodes:
				episodeLink = episode.get("href")
				
				titleClass = episode.find(attrs={"class": "title"})
				episodeTitle = titleClass.text if titleClass else None
				
				imgTag = episode.find("img")
				episodePosterURL = imgTag.get("src") if imgTag else None
				
				ratingClass = episode.find(attrs={"class": "i-fav rating"})
				episodeRating = ratingClass.text if ratingClass else None

				self.episodesList.insert(0, Episode(episodeLink, episodeTitle, episodePosterURL, episodeRating))
					
		finally:
			return self.episodesList

	def refreshMetadata(self, posterOnly=False):
		title = self.title
		posterURL = self.posterURL

		try:
			if not posterOnly:
				name = self.soup.body.find(attrs={"itemprop": "name"})
				if name:
					title = name.text

			imgClass = self.soup.body.find(attrs={"class": "movie_img"})
			if imgClass:
				imgTag = imgClass.find("img")
				if imgTag:
					posterURL = imgTag.get("src")

		finally:
			self.title = title
			self.posterURL = posterURL


class Episode:
	def __init__(self, link, title=None, posterURL=None, rating=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.rating = rating
		self.downloadLinksList = []

		soup = None
		try:
			showPage = requests.get(self.link).text
			soup = BeautifulSoup(showPage, features="html.parser")

		finally:
			self.soup = soup

	def getDownloadSources(self):
		try:
			session = requests.Session()

			baseURL = self.link.split("/")[0] + "//" + self.link.split("/")[2]

			episodeSoup = self.soup

			vidstreamURL = baseURL + episodeSoup.body.find("iframe", attrs={"class": "auto-size"}).get("src")

			vidstreamResponseText = session.get(vidstreamURL).text
			videoSoup = BeautifulSoup(vidstreamResponseText, features="html.parser")

			try:
				qualityLinksFileURL = baseURL + videoSoup.body.find("source").get("src")

			except AttributeError:
				jsCode = str(videoSoup.find_all("script")[1])

				verificationToken = str(re.findall("\{'[0-9a-zA-Z_]*':'ok'\}", jsCode)[0][2:-7])
				encodedAdLinkVar = re.findall("\([0-9a-zA-Z_]{2,12}\[Math", jsCode)[0][1:-5]
				firstEncodingArray = re.findall(",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[1][1:-3]
				secondEncodingArray = re.findall(",[0-9a-zA-Z_]{2,12}=\[\]", jsCode)[2][1:-3]

				jsCode = re.sub("^<script type=\"text/javascript\">", "", jsCode)
				jsCode = re.sub("[;,]\$\('\*'\)(.*)$", ";", jsCode)
				jsCode = re.sub(",ismob=(.*)\(navigator\[(.*)\]\)[,;]", ";", jsCode)
				jsCode = re.sub("var a0b=function\(\)(.*)a0a\(\);", "", jsCode)
				jsCode += "var link = ''; for (var i = 0; i <= " + secondEncodingArray + "['length']; i++) { link += " + firstEncodingArray + "[" + secondEncodingArray + "[i]] || ''; } return [link, " + encodedAdLinkVar + "[0]] }"

				jsCodeReturn = executeJS(jsCode)()
				verificationPath = jsCodeReturn[0]
				encodedAdPath = jsCodeReturn[1]

				adLink = baseURL + "/" + str(decode(encodedAdPath + "=" * (-len(encodedAdPath) % 4)), "utf-8")
				session.get(adLink)

				verificationLink = baseURL + "/tvc.php?verify=" + verificationPath
				session.post(verificationLink, data={verificationToken: "ok"})

				vidstreamResponseText = session.get(vidstreamURL).text
				videoSoup = BeautifulSoup(vidstreamResponseText, features="html.parser")

				qualityLinksFileURL = baseURL + videoSoup.body.find("source").get("src")

			qualityLinks = session.get(qualityLinksFileURL).text
			qualityLinksArray = qualityLinks.split("\n")[1::]

			for i in range(0, len(qualityLinksArray)-2, 2):
				qualityInfo = qualityLinksArray[i]
				link = qualityLinksArray[i+1].replace("/stream/", "/dl/")
				qualityRegEx = "[0-9]{3,4}x[0-9]{3,4}"
				quality = self.__roundQuality(int(re.search(qualityRegEx, qualityInfo)[0].split("x")[1]))
				fileName = self.link.split("/")[4] + "-" + str(quality) + "p.mp4"

				self.downloadLinksList.append(DownloadSource(link, quality, fileName))

		finally:
			return self.downloadLinksList

	def refreshMetadata(self, posterOnly=False):
		title = self.title
		posterURL = self.posterURL

		try:
			if not posterOnly:
				name = self.soup.body.find(attrs={"class": "movie_title"})
				if name:
					title = name.text

			imgClass = self.soup.body.find(attrs={"class": "movie_img"})
			if imgClass:
				imgTag = imgClass.find("img")
				if imgTag:
					posterURL = imgTag.get("src")

		finally:
			self.title = title
			self.posterURL = posterURL

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
