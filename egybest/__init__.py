from base64 import urlsafe_b64decode as decode
from strsimpy.ngram import NGram
from js2py import eval_js as executeJS
from bs4 import BeautifulSoup
import requests
import math
import re


class EgyBest:
	def __init__(self, mirrorURL=None):
		self.baseURL = mirrorURL if mirrorURL else "https://egy.best"
	
	def search(self, query, includeShows=True, includeMovies=True, originalOrder=False):
		searchURL = f"{self.baseURL}/explore/?q={query}%20"
		searchResponse = None
		resultsList = []
		
		try:
			searchResponse = requests.get(searchURL)
			
			pageContent = searchResponse.text
			soup = BeautifulSoup(pageContent, features="html.parser")

			resultsClass = soup.body.find(attrs={"id": "movies", "class": "movies"})
			searchResults = resultsClass.findAll("a")

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
			
			if not originalOrder:
				resultsList.sort(key=lambda element: NGram(1).distance(query, element.title))

		finally:
			return resultsList

	def getTopShows(self, n=50):
		iterations = int(math.ceil(n / 12))
		leftOver = n % 12
		topShowsList = []

		try:
			for iteration in range(iterations):
				topShows = __getTop(listType="tv", pageNum=(iteration + 1))
				for i in range(len(topShows)):
					if (iteration + 1) == iterations and i == leftOver:
						break

					topShowsList.append(topShows[i])

		finally:
			return topShowsList

	def getTopMovies(self, n=50):
		iterations = int(math.ceil(n / 12))
		leftOver = n % 12
		topMoviesList = []

		try:
			for iteration in range(iterations):
				topMovies = __getTop(listType="movies", pageNum=(iteration + 1))
				for i in range(len(topMovies)):
					if (iteration + 1) == iterations and i == leftOver:
						break

					topMoviesList.append(topMovies[i])

		finally:
			return topMoviesList

	def getTopShowsPage(self, pageNum):
		return self.__getTop(listType="tv", pageNum=pageNum)

	def getTopMoviesPage(self, pageNum):
		return self.__getTop(listType="movies", pageNum=pageNum)

	def __getTop(self, listType, pageNum):
		topURL = f"{self.baseURL}/{listType}/top/?page={pageNum}"
		topList = []

		try:
			topResponse = requests.get(topURL)

			pageContent = topResponse.text
			soup = BeautifulSoup(pageContent, "html.parser")

			resultsClass = soup.body.find(attrs={"id": "movies"})
			results = resultsClass.findAll("a")

			for result in results:
				if " ".join(result.get("class")) == "auto load btn b":
					continue

				link = result.get("href")

				titleClass = result.find(attrs={"class": "title"})
				title = titleClass.text if titleClass else None

				imgTag = result.find("img")
				posterURL = imgTag.get("src") if imgTag else None

				ratingClass = result.find(attrs={"class": "i-fav rating"})
				rating = ratingClass.text if ratingClass else None

				topList.append(Episode(link, title, posterURL, rating) if listType == "movies" else Show(link, title, posterURL, rating))

		finally:
			return topList


class Show:
	def __init__(self, link, title=None, posterURL=None, rating=None):
		self.link = link
		self.title = title
		self.posterURL = posterURL
		self.rating = rating

		self.soup = None

		self.seasonsList = []

	def getSeasons(self):
		try:
			if not self.soup:
				showPage = requests.get(self.link).text
				self.soup = BeautifulSoup(showPage, features="html.parser")

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
			if not self.soup:
				showPage = requests.get(self.link).text
				self.soup = BeautifulSoup(showPage, features="html.parser")

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
		
		self.soup = None

		self.episodesList = []

	def getEpisodes(self):
		try:
			if not self.soup:
				seasonPage = requests.get(self.link).text
				self.soup = BeautifulSoup(seasonPage, features="html.parser")

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
			if not self.soup:
				seasonPage = requests.get(self.link).text
				self.soup = BeautifulSoup(seasonPage, features="html.parser")

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

		self.soup = None

		self.downloadLinksList = []

	def getDownloadSources(self):
		try:
			baseURL = self.link.split("/")[0] + "//" + self.link.split("/")[2]
			
			session = requests.Session()

			if not self.soup:
				epispdePage = requests.get(self.link).text
				self.soup = BeautifulSoup(epispdePage, features="html.parser")

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
				qualityRegEx = "[0-9]{3,4}x[0-9]{3,4}"
				quality = self.__roundQuality(int(re.search(qualityRegEx, qualityInfo)[0].split("x")[1]))
				fileName = self.link.split("/")[4] + "-" + str(quality) + "p.mp4"
				mediaLink = requests.utils.quote(qualityLinksArray[i+1]).replace("_", "%5F").replace("/stream/", "/dl/").replace("/stream.m3u8", f"/{fileName}")

				self.downloadLinksList.append(DownloadSource(mediaLink, quality, fileName))

		finally:
			return self.downloadLinksList

	def refreshMetadata(self, posterOnly=False):
		title = self.title
		posterURL = self.posterURL

		try:
			if not self.soup:
				episodePage = requests.get(self.link).text
				self.soup = BeautifulSoup(episodePage, features="html.parser")

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
