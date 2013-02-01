import re
import urllib2
import time, os, re
from Cookie import BaseCookie
import plistlib
from datetime import datetime, timedelta

from constants2 import *

from CrunchyrollUserAPI import *

"""
schema inside Dict{}
    all items (even movies) can be referenced by a the series dict.
    series are known by seriesID (a unique number), provided by crunchyroll.com
    Dict['series'] =
    { seriesId: {
        "title": title,
        "seriesId": seriesId,
        "tvdbId": tvdbId,
        "description": seriesDescription,
        "thumb": thumb,
        "art": art,
        "rating": rating,
        "simpleRating": simpleRating,
        "dateUpdated": dateUpdated,
        "seasonList": []
        }
    }
"""
"""
    Dict['seasons'] =
    { seasonId: {
        "title": title,
        "seasonId": seasonId,
        "seriesId": seriesId,
        "thumb": thumb,
        "art": art,
        "epsRetreived": None,
        "epList": [],
        "dateUpdated": dateUpdated,
        "seasonNumber": seasonNumber,
        "description": description
        }
    }
"""
""" 
    episodesList contains playable media (it's actually a dict, but let's not get finicky).
    episodes are known by mediaId (a unique number), provided at crunchyroll.com
    This is an episode entry in the list:
    Dict['episodes'] =
    { mediaId: {
        "title": episodeTitle,
        "description": episodeDescription,
        "mediaId": mediaId,
        "episodeNumber": episodeNumber,
        "freePubDate": freePubDate,
        "freePubDateEnd": freePubDateEnd,
        "premiumPubDate": premiumPubDate,
        "premiumPubDateEnd": premiumPubDateEnd,
        "publisher": publisher,
        "duration": duration,
        "subtitleLanguages": subtitleLanguages,
        "rating": rating,
        "simpleRating": simpleRating,
        "countries": countries,
        "dateUpdated": dateUpdated,
        "season": season,
        "seasonId": seasonId,
        "mediaLink": mediaLink,
        "category": category,
        "thumb": thumb,
        "art": art,
        "seriesTitle": seriesTitle,
        "availableResolutions": availableResolutions
        }
    }
"""

def debugFeedItem(item):
    for sub in list(item):
        text1 = "%s: %s" % (sub.tag, sub.text)
        Log.Debug(text1)
        for sub2 in list(sub):
            text2 = "\t%s/%s: %s\n%s" % (sub.tag, sub2.tag, sub2.text, list(sub2))
            Log.Debug(text2)
            for sub3 in list(sub2):
                text3 = "\t\t%s/%s/%s: %s\n%s" % (sub.tag, sub2.tag, sub3.tag, sub3.text, list(sub3))
                Log.Debug(text3)
                for sub4 in list(sub3):
                    text4 = "\t\t\t%%s/%s/%s: %s\n%s" % (sub.tag, sub2.tag, sub3.tag, sub4.tag, sub4.text, list(sub4))
                    Log.Debug(text4)


PLUGIN_NAMESPACE = {"media":"http://search.yahoo.com/mrss/", "crunchyroll":"http://www.crunchyroll.com/rss"}

def cacheFullSeriesList():
    #startTime = Datetime.Now()
    PLUGIN_NAMESPACE = {"media":"http://search.yahoo.com/mrss/", "crunchyroll":"http://www.crunchyroll.com/rss"}
    feedHtml = XML.ElementFromURL(SERIES_FEED_URL,cacheTime=SERIES_FEED_CACHE_TIME)
#    Log.Debug(str(feedHtml))
    items = feedHtml.xpath("//item")
    if Dict['series'] is None:
        Dict['series'] = {}
    
    if Dict['seasons'] is None:
        Dict['seasons'] = {}
    
    dateUpdated = datetime.utcnow()
    
    for item in items:
#        debugFeedItem(item.xpath("."))
        seasonId = int(item.xpath("./guid")[0].text.split(".com/")[1].split("-")[1])
        try:
            seasonNumber = int(item.xpath("./crunchyroll:season", namespaces=PLUGIN_NAMESPACE)[0].text)
        except:
            seasonNumber = None
        thumb = str(item.xpath("./media:thumbnail", namespaces=PLUGIN_NAMESPACE)[0].get('url')).split("_")[0]+"_full.jpg"
        art = thumb
        seasonTitle = item.xpath("./title")[0].text
        seriesId = int(item.xpath("./crunchyroll:series-guid", namespaces=PLUGIN_NAMESPACE)[0].text.split(".com/series-")[1])
        simpleRating = item.xpath("./media:rating", namespaces=PLUGIN_NAMESPACE)[0].text
        tvdbId = None
        description = item.xpath("./description")[0].text
        seriesDescription = None
        
        if not str(seriesId) in Dict['series'] or Dict['series'][str(seriesId)] is None:
            series = {
                "title": seasonTitle,
                "seriesId": seriesId,
                "tvdbId": tvdbId,
                "description": seriesDescription,
                "thumb": thumb,
                "art": art,
                "rating": None,
                "simpleRating": simpleRating,
                "dateUpdated": dateUpdated,
                "seasonList": []
            }
            Dict['series'][str(seriesId)] = series
        
        if not seasonId in Dict['series'][str(seriesId)]['seasonList']:
            Dict['series'][str(seriesId)]['seasonList'].append(seasonId)
        
        Dict['series'][str(seriesId)]['dateUpdated'] = dateUpdated
        
        if not str(seasonId) in Dict['seasons'] or Dict['seasons'][str(seasonId)] is None:
            season = {
                "title": seasonTitle,
                "seasonId": seasonId,
                "seriesId": seriesId,
                "thumb": thumb,
                "art": art,
                "epsRetreived": None,
                "epList": [],
                "dateUpdated": dateUpdated,
                "seasonNumber": seasonNumber,
                "description": description
            }
            Dict['seasons'][str(seasonId)] = season
        
    
    #make sure that the season list for each series is in order
    for seriesid in Dict['series'].keys():
        series = Dict['series'][seriesid]
#        Log.Debug(series['seasonList'])
        newSeasonList = sorted(series['seasonList'], key=lambda k: Dict['seasons'][str(k)]['seasonNumber'])
        Dict['series'][seriesid]['seasonList'] = newSeasonList
    
def cacheEpisodeListForSeason(seasonId):
    from datetime import datetime, timedelta
    

    #startTime = Datetime.Now()
    feed =  "%s%s" % (SEASON_FEED_BASE_URL, str(seasonId))
    feedHtml = XML.ElementFromURL(feed,cacheTime=SERIES_FEED_CACHE_TIME)
    items = feedHtml.xpath("//item")
    if Dict['episodes'] is None:
        Dict['episodes'] = {}
    
    dateUpdated = datetime.utcnow()
    
    try:
        rating = feedHtml.xpath("//rating")[0].text
        Log.Debug(rating)
        
        # see http://www.classify.org/safesurf/
        #SS~~000. Age Range
        #1) All Ages
        #2) Older Children
        #3) Teens
        #4) Older Teens
        #5) Adult Supervision Recommended
        #6) Adults
        #7) Limited to Adults
        #8) Adults Only
        #9) Explicitly for Adults

        # just pluck the age value from text that looks like:
        # (PICS-1.1 &quot;http://www.classify.org/safesurf/&quot; l r (SS~~000 5))
        ageLimit = re.sub(r'(.*\(SS~~\d{3}\s+)(\d)(\).*)', r'\2', rating)
        rating = int(ageLimit) # we don't care about the categories

    except (ValueError, IndexError, TypeError):
        rating = None
    
    seriesTitle = feedHtml.xpath("//crunchyroll:seriesTitle", namespaces=PLUGIN_NAMESPACE)[0].text
    seriesId = Dict['seasons'][str(seasonId)]["seriesId"]
    if not Dict['series'][str(seriesId)]["title"] is seriesTitle:
        Log.Debug("Series (%s) title (%s) does not match the one on the season (%s) feed (%s)." % (str(seriesId), Dict['series'][str(seriesId)]["title"], str(seasonId), seriesTitle))
        Dict['series'][str(seriesId)]["title"] = seriesTitle
    
    for item in items:
        mediaId = int(item.xpath("./crunchyroll:mediaId", namespaces=PLUGIN_NAMESPACE)[0].text)
        modifiedDate = item.xpath("./crunchyroll:modifiedDate", namespaces=PLUGIN_NAMESPACE)[0].text
#        Log.Debug(modifiedDate)
        feedEntryModified = datetime.strptime(modifiedDate, "%a, %d %b %Y %H:%M:%S %Z")
        
        if not str(mediaId) in Dict['episodes'] or Dict['episodes'][str(mediaId)]["dateUpdated"] <= feedEntryModified:
            #TODO: should use <title> or <crunchyroll:episodeTitle> for the title?
            try: episodeTitle = item.xpath("./crunchyroll:episodeTitle", namespaces=PLUGIN_NAMESPACE)[0].text
            except: episodeTitle = item.xpath("./title")[0].text
            if episodeTitle.startswith("%s - " % seriesTitle):
                episodeTitle = episodeTitle.replace("%s - " % seriesTitle, "")
            elif episodeTitle.startswith("%s Season " % seriesTitle):
                episodeTitle = episodeTitle.replace("%s Season " % seriesTitle, "")
                episodeTitle = episodeTitle.split(" ", 1)[1].lstrip("- ")

            episodeDescription = item.xpath("./description")[0].text
            if "/><br />" in episodeDescription:
                episodeDescription = episodeDescription.split("/><br />")[1]
            
            episodeNumber = int(item.xpath("./crunchyroll:episodeNumber", namespaces=PLUGIN_NAMESPACE)[0].text)
            freePubDate = datetime.datetime.strptime(item.xpath("./crunchyroll:freePubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
            freePubDateEnd = datetime.datetime.strptime(item.xpath("./crunchyroll:freeEndPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
            premiumPubDate = datetime.datetime.strptime(item.xpath("./crunchyroll:premiumPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
            premiumPubDateEnd = datetime.datetime.strptime(item.xpath("./crunchyroll:premiumEndPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
            publisher = item.xpath("./crunchyroll:publisher", namespaces=PLUGIN_NAMESPACE)[0].text
            duration = int(item.xpath("./crunchyroll:duration", namespaces=PLUGIN_NAMESPACE)[0].text) * 1000
            subtitleLanguages = item.xpath("./crunchyroll:subtitleLanguages", namespaces=PLUGIN_NAMESPACE)[0].text.split(",")
            simpleRating = item.xpath("./media:rating", namespaces=PLUGIN_NAMESPACE)[0].text
            countries = item.xpath("./media:restriction", namespaces=PLUGIN_NAMESPACE)[0].text.strip().split(" ")
            try: season = int(item.xpath("./crunchyroll:season", namespaces=PLUGIN_NAMESPACE)[0].text)
            except: season = 0
            mediaLink = item.xpath(EPISODE_MEDIA_LINK_XPATH)[0].text.strip()
            category = item.xpath("./category")[0].text
            thumb = str(item.xpath("./enclosure")[0].get('url')).split("_")[0]+"_full.jpg"
            art = thumb
            
            #FIXME: figure out how to deal with video resolutions
            availableResolutions = None
            
            episode = {
                "title": episodeTitle,
                "description": episodeDescription,
                "mediaId": mediaId,
                "episodeNumber": episodeNumber,
                "freePubDate": freePubDate,
                "freePubDateEnd": freePubDateEnd,
                "premiumPubDate": premiumPubDate,
                "premiumPubDateEnd": premiumPubDateEnd,
                "publisher": publisher,
                "duration": duration,
                "subtitleLanguages": subtitleLanguages,
                "rating": rating,
                "simpleRating": simpleRating,
                "countries": countries,
                "dateUpdated": dateUpdated,
                "season": season,
                "seasonId": seasonId,
                "mediaLink": mediaLink,
                "category": category,
                "thumb": thumb,
                "art": art,
                "seriesTitle": seriesTitle,
                "availableResolutions": availableResolutions
            }
            
            Dict['episodes'][str(mediaId)] = episode
        
    Dict['seasons'][str(seasonId)]["epsRetreived"] = dateUpdated
    Dict['seasons'][str(seasonId)]["epList"] = sorted(Dict['seasons'][str(seasonId)]["epList"], key=lambda k: Dict['episodes'][str(k)]["episodeNumber"])
#    
#    
#    @parallelize
#    def parseSeriesItems():
#        for item in items:
#            seriesId = int(item.xpath("./guid")[0].text.split(".com/")[1])
#            @task
#            def parseSeriesItem(item=item,seriesId=seriesId):
#                if not (str(seriesId) in Dict['series']):
#                    title = item.xpath("./title")[0].text
#                    if Prefs['fanart'] is True:
#                        tvdbIdr = tvdbscrapper.GetTVDBID(title, Locale.Language.English)
#                        tvdbId = tvdbIdr['id']
#                    else:
#                        tvdbId = None
#                        
#                    description = item.xpath("./description")[0].text
#                    thumb = str(item.xpath("./property")[0].text).replace("_large",THUMB_QUALITY[Prefs['thumb_quality']])
#                    
#                    if ART_SIZE_LIMIT is False:
#                        art = thumb
#                    else:
#                        art = None
#                    series = {
#                        "title": title,
#                        "seriesId": seriesId,
#                        "tvdbId": tvdbId,
#                        "description": description,
#                        "thumb": thumb,
#                        "art": art
#                    }
#                    dictInfo = series
#                    dictInfo['epsRetrived'] = None
#                    dictInfo['epList'] = []
#                    Dict['series'][str(seriesId)] = dictInfo
#                else:
#                    title = item.xpath("./title")[0].text
#                    thumb = str(item.xpath("./property")[0].text).replace("_large",THUMB_QUALITY[Prefs['thumb_quality']])
#
#                    if ART_SIZE_LIMIT is False:
#                        art = thumb
#                    else:
#                        art = None
#                    seriesDict = Dict['series'][str(seriesId)]
#                    seriesDict['thumb'] = thumb
#                    seriesDict['art'] = art
#                    Dict['series'][str(seriesId)] = seriesDict
#                    series = {
#                        "title": seriesDict['title'],
#                        "seriesId": seriesId,
#                        "tvdbId": seriesDict['tvdbId'],
#                        "description": seriesDict['description'],
#                        "thumb": seriesDict['thumb'],
#                        "art": seriesDict['art']
#                    }
#                seriesList.append(series)

def getEpisodeListFromFeed(feed, sort=True):
#    import datetime
    try:
        episodeList = []
        dateUpdated = datetime.utcnow()
        
        # timeout errors driving me nuts, so
        req = HTTP.Request(feed, timeout=100)
        feedHtml = XML.ElementFromString(req.content)
#        feedHtml = XML.ElementFromURL(feed)
        items = feedHtml.xpath("//item")
#        seriesTitle = feedHtml.xpath("//channel/title")[0].text.replace(" Episodes", "")
        @parallelize
        def parseEpisodeItems():
            for item in items:
                mediaId = int(item.xpath("./guid")[0].text.split("-")[-1])
                feedEntryModified = datetime.datetime.strptime(item.xpath("./crunchyroll:modifiedDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
                @task
                def parseEpisodeItem(item=item,mediaId=mediaId,feedEntryModified=feedEntryModified):
                    if not str(mediaId) in Dict['episodes'] or Dict['episodes'][str(mediaId)]["dateUpdated"] <= feedEntryModified:
                        seriesTitle = item.xpath("./crunchyroll:seriesTitle", namespaces=PLUGIN_NAMESPACE)[0].text
                        #TODO: should use <title> or <crunchyroll:episodeTitle> for the title?
                        title = item.xpath("./crunchyroll:episodeTitle", namespaces=PLUGIN_NAMESPACE)[0].text
#                        if title.startswith("%s - " % seriesTitle):
#                            title = title.replace("%s - " % seriesTitle, "")
#                        elif title.startswith("%s Season " % seriesTitle):
#                            title = title.replace("%s Season " % seriesTitle, "")
#                            title = title.split(" ", 1)[1].lstrip("- ")
                        
                        episodeDescription = item.xpath("./description")[0].text
                        if "/><br />" in episodeDescription:
                            episodeDescription = episodeDescription.split("/><br />")[1]
                        episodeDescription = stripHtml(episodeDescription)
                        
                        try:
                            episodeNumber = int(item.xpath("./crunchyroll:episodeNumber", namespaces=PLUGIN_NAMESPACE)[0].text)
                        except:
                            episodeNumber = None
                        
                        freePubDate = datetime.strptime(item.xpath("./crunchyroll:freePubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
                        freePubDateEnd = datetime.strptime(item.xpath("./crunchyroll:freeEndPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
                        premiumPubDate = datetime.strptime(item.xpath("./crunchyroll:premiumPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
                        premiumPubDateEnd = datetime.strptime(item.xpath("./crunchyroll:premiumEndPubDate", namespaces=PLUGIN_NAMESPACE)[0].text, FEED_DATE_FORMAT)
                        try: publisher = item.xpath("./crunchyroll:publisher", namespaces=PLUGIN_NAMESPACE)[0].text
                        except: publisher = ""
                        duration = int(item.xpath("./crunchyroll:duration", namespaces=PLUGIN_NAMESPACE)[0].text) * 1000
                        subtitleLanguages = item.xpath("./crunchyroll:subtitleLanguages", namespaces=PLUGIN_NAMESPACE)[0].text.split(",")
                        simpleRating = item.xpath("./media:rating", namespaces=PLUGIN_NAMESPACE)[0].text
                        countries = item.xpath("./media:restriction", namespaces=PLUGIN_NAMESPACE)[0].text.strip().split(" ")
                        try: season = int(item.xpath("./crunchyroll:season", namespaces=PLUGIN_NAMESPACE)[0].text)
                        except: season = None
                        mediaLink = item.xpath(EPISODE_MEDIA_LINK_XPATH)[0].text.strip()
                        category = item.xpath("./category")[0].text
                        try: thumb = str(item.xpath("./media:thumbnail", namespaces=PLUGIN_NAMESPACE)[0].get('url')).split("_")[0]+THUMB_QUALITY[Prefs['thumb_quality']]+".jpg"
                        except IndexError:
                            if "http://static.ak.crunchyroll.com/i/coming_soon_new_thumb.jpg" in description:
                                thumb = "http://static.ak.crunchyroll.com/i/coming_soon_new_thumb.jpg"
                            else:
                                thumb = "" # FIXME happens on newbie content, could be a bad idea b/c of cache.
                        art = thumb
                        
                        try:
                            rating = item.xpath("../rating")[0].text
                            Log.Debug(rating)
                            
                            # see http://www.classify.org/safesurf/
                            #SS~~000. Age Range
                            #1) All Ages
                            #2) Older Children
                            #3) Teens
                            #4) Older Teens
                            #5) Adult Supervision Recommended
                            #6) Adults
                            #7) Limited to Adults
                            #8) Adults Only
                            #9) Explicitly for Adults

                            # just pluck the age value from text that looks like:
                            # (PICS-1.1 &quot;http://www.classify.org/safesurf/&quot; l r (SS~~000 5))
                            ageLimit = re.sub(r'(.*\(SS~~\d{3}\s+)(\d)(\).*)', r'\2', rating)
                            rating = int(ageLimit) # we don't care about the categories
                            
                        except (ValueError, IndexError, TypeError):
                            rating = None

                        if Dict['episodes'][str(mediaId)]["dateUpdated"] <= feedEntryModified:
                            seasonId = Dict['episodes'][str(mediaId)]["seasonId"]
                        #FIXME: figure out how to deal with getting resolutions.
                        availableResolutions = None
                        
                        episode = {
                            "title": title,
                            "description": episodeDescription,
                            "mediaId": mediaId,
                            "episodeNumber": episodeNumber,
                            "freePubDate": freePubDate,
                            "freePubDateEnd": freePubDateEnd,
                            "premiumPubDate": premiumPubDate,
                            "premiumPubDateEnd": premiumPubDateEnd,
                            "publisher": publisher,
                            "duration": duration,
                            "subtitleLanguages": subtitleLanguages,
                            "rating": rating,
                            "simpleRating": simpleRating,
                            "countries": countries,
                            "dateUpdated": dateUpdated,
                            "season": season,
                            "seasonId": seasonId,
                            "mediaLink": mediaLink,
                            "category": category,
                            "thumb": thumb,
                            "art": art,
                            "seriesTitle": seriesTitle,
                            "availableResolutions": availableResolutions
                        }
                        
                        Dict['episodes'][str(mediaId)] = episode
                    else:
                        episode = Dict['episodes'][str(mediaId)]
                    episodeList.append(episode)
        if sort:
            return sorted(episodeList, key=lambda k: k['episodeNum'])
        else:
            return episodeList

    except Exception, arg:
        Log.Error("#####We got ourselves a dagnabbit exception:")
        Log.Error(repr(Exception) + repr(arg))
        Log.Error("feed: %s" % feed)
        #Log.Error("Content:")
        #Log.Error(req.content) # too verbose, uncomment if needed
        # maybe just pass the exception up the chain here
        # instead of returning None
        return None

def getSeriesListFromFeed(feed, sort=True, sortBy="title"):
    #TODO: implement a check to eliminate need for call if series were cached recently
    cacheFullSeriesList()
    
    feedHtml = HTML.ElementFromURL(feed,cacheTime=SERIES_FEED_CACHE_TIME)
    seriesList = []
    items = feedHtml.xpath("//item")
    for item in items:
        seriesGUID = item.xpath("./guid")[0].text.replace("http://www.crunchyroll.com/", "")
        if not seriesGUID in Dict['series']:
            #TODO: figure out what to do if the series can't be found in Dict['series']
            Log.Debug("Could not find series with seriesGUID %s in Dict['series'].")
        else:
            seriesList.append(Dict['series'][str(seriesGUID)])
        
    if sort:
#        if sortBy == title:
#            return sorted(seriesList, key=lambda k: getSortTitle(k))
#        else:
            return sorted(seriesList, key=lambda k: k[sortBy])
    else:
        return seriesList



def GetEpisodeListFromQuery(queryString):
    "return a list of relevant episode dicts matching queryString"
    return getEpisodeListFromFeed(SEARCH_URL+queryString.strip().replace(' ', '%20'), sort=False)


def GetQueueList():
    login()
    queueHtml = HTML.ElementFromURL(QUEUE_URL,cacheTime=QUEUE_LIST_CACHE_TIME)
    queueList = []
    items = queueHtml.xpath("//div[@id='main_content']/ul[@id='sortable']/li[@class='queue-item']")
    for item in items:
        title = item.xpath(".//span[@class='series-title ellipsis']")[0].text
        seriesId = int(item.xpath("@series_id")[0].replace("queue_item_",""))
#        epToPlay = BASE_URL+item.xpath(".//a[@itemprop='url']/@href")[0].split("?t=")[0]
        
#        episodeTitle= item.xpath(".//a[@itemprop='url']/@title")[0]
#        episodeDescription = item.xpath(".//p[@itemprop='description']")

#        if episodeDescription:
#            episodeDescription = episodeDescription[0].text.strip('\n').strip()
#        else:
#            episodeDescription = ""
        """
        make sure item has an ID and does not error out from an empty string.
        This happens for series that were on cruncyroll but cruchyroll nolonger has rights to show.
        """
        episodeMediaIDStr = item.xpath("@media_id")[0]
        if not (episodeMediaIDStr == ""):
            episodeMediaID = int(episodeMediaIDStr)
            
            nextUpText = item.xpath(".//span[@class='series-data ellipsis']")[0].text
            fixit = ""
            for line in nextUpText.split('\n'):
                fixit = fixit + line.strip('\n').strip() +'\n'

            nextUpText = fixit

            queueItem = {
                "title": title,
                "upNextMediaId": episodeMediaId,
                "seriesId": seriesId#,
            }
            queueList.append(queueItem)
        
    return queueList


def recoverEpisodeDict(mediaId):
    """
    try everything possible to recover the episode info for
    mediaId and save it in Dict{}. If it fails, return none.
    """
    Log.Debug("#######recovering episode dictionary for mediaID %s" % str(mediaId))
    # make sure the series list is up to date
    cacheFullSeriesList()
    
    # figure out method of getting the seriesId that the episode is in...
    # get all the seasons that are in that series
    seasonList = getListOfSeasonsInSeries(seriesId)
    for seasonId in seasonList:
        cacheEpisodeListForSeason(seasonId)
    
#    # get a link with title in it.
#    #import urllib2
#    req = urllib2.urlopen(BASE_URL+"/media-" + str(mediaId) + "?pskip_wall=1")
#    redirectedUrl = req.geturl()
#    req.close
#    #FIXME: update for new system
#    redirectedUrl = redirectedUrl.replace("?pskip_wall=1", "")    
#    seriesName = redirectedUrl.split(".com/")[1].split("/")[0]
#    seriesUrl = seriesTitleToUrl(seriesName)
#    getEpisodeListFromFeed(seriesUrl) # for side-effect of caching episode
    
    if str(mediaId) in Dict['episodes']:
        return Dict['episodes'][str(mediaId)]
    
    # FIXME: blah
    # not good so far, we need a feed that provides full episodes. Yikes.
    # try grabbing from boxee_feeds
    # need seriesID as in boxee_feeds/showseries/384855
    # which can be retrieved from the seriesUrl contents, whew...
    # alternatively, use http://www.crunchyroll.com/series-name/episodes
    # which gives full episodes, but, well, is HTML and has less media info
    return None


def GetPopularAnimeEpisodes():
    "return a list of anime episode dicts that are currently popular"
    return getEpisodeListFromFeed(POPULAR_ANIME_FEED, sort=False)

def GetPopularDramaEpisodes():
    "return a list of drama episode dicts that are currenly popular"
    return getEpisodeListFromFeed(POPULAR_DRAMA_FEED, sort=False)

def GetPopularVideos():
    "return the most popular videos."
    return getEpisodeListFromFeed(POPULAR_FEED, sort=False)

def GetRecentVideos():
    "return a list of episode dicts of recent videos of all types"
    return getEpisodeListFromFeed(RECENT_VIDEOS_FEED, sort=False)

def GetRecentAnimeEpisodes():
    "return a list of episode dicts of recently added anime episodes"
    return getEpisodeListFromFeed(RECENT_ANIME_FEED, sort=False)

def GetRecentDramaEpisodes():
    "return a list of recently added drama videos"
    return getEpisodeListFromFeed(RECENT_DRAMA_FEED, sort=False)

def GetAnimeSeriesList():
    "return a list of all available series in anime"
    return getSeriesListFromFeed(SERIES_FEED_BASE_URL + "genre_anime_all", sort=True)

def GetDramaSeriesList():
    "return a list of all available series in Drama"
    return getSeriesListFromFeed(SERIES_FEED_BASE_URL + "drama", sort=True)

def GetAllSeries():
    "return a list of series dicts that represent all available series"
    list = []
    anime = getAnimeSeriesList()
    drama = getDramaSeriesList()
    # FIXME: if there's overlap, we'll have dupes...
    list = anime + drama
#    list = sorted(list, key=lambda k: getSortTitle(k))
    return list

def GetPopularDramaSeries():
    "return a list of series dicts of most popular drama"
    return getSeriesListFromFeed(SERIES_FEED_BASE_URL + "drama_popular", sort=False)

def GetPopularAnimeSeries():
    "return a list of series dicts of most popular anime"
    return getSeriesListFromFeed(SERIES_FEED_BASE_URL + "anime_popular", sort=False)

def GetAnimeSeriesByGenre(genre):
    queryStr = ANIME_GENRE_LIST[genre].replace(' ', '%20')
    feed = SERIES_FEED_BASE_URL + "anime_withtag/" + queryStr
    return getSeriesListFromFeed(feed)

def GetDramaSeriesByGenre(genre):
    queryStr = DRAMA_GENRE_LIST[genre].replace(' ', '%20')
    feed = SERIES_FEED_BASE_URL + "genre_drama_" + queryStr
    return getSeriesListFromFeed(feed)

def GetSeriesByGenre(genre):
    list = []
    drama, anime = [],[]
    try:
        drama = getDramaSeriesByGenre(genre)
    except KeyError: # may not have that genre
        drama = []
    try:
        anime = getAnimeSeriesByGenre(genre)
    except KeyError:
        anime = []

    # FIXME: if there's overlap, we'll have dupes...    
    return anime + drama


def GetSeriesDict(seriesId):
    """
    return an series dict object identified by seriesId.
    If you know the seriesId, it SHOULD be in the cache already.
    If not, you could get None if recovery doesn't work. This might 
    happen with seriesId's that come from the great beyond 
    (queue items on server, e.g.)
    Sry bout that.
    """
    if str(seriesId) not in Dict['series']:
        # get brutal
        Log.Debug("#######recovering series dictionary for seriesID %s" % str(seriesId))
        cacheFullSeriesList()
#        # get a link with title in it.
#        #import urllib2
#        req = urllib2.urlopen(BASE_URL+"/media-" + str(mediaId) + "?pskip_wall=1")
#        redirectedUrl = req.geturl()
#        req.close
#        #FIXME: update for new system
#        redirectedUrl = redirectedUrl.replace("?pskip_wall=1", "")    
#        seriesName = redirectedUrl.split(".com/")[1].split("/")[0]
#        seriesUrl = seriesTitleToUrl(seriesName)
#        getEpisodeListFromFeed(seriesUrl) # for side-effect of caching episode
        
        if str(mediaId) in Dict['episodes']:
            return Dict['episodes'][str(mediaId)]
        
        # FIXME: blah
        # not good so far, we need a feed that provides full episodes. Yikes.
        # try grabbing from boxee_feeds
        # need seriesID as in boxee_feeds/showseries/384855
        # which can be retrieved from the seriesUrl contents, whew...
        # alternatively, use http://www.crunchyroll.com/series-name/episodes
        # which gives full episodes, but, well, is HTML and has less media info
        
    return Dict['series'].get(str(seriesId))

def GetListOfSeasonsInSeries(seriesId):
    # make sure the seriesId is in the cache
    if not str(seriesId) in Dict['series']:
        Log.Debug("Did not find seriesID %s in the cache. refreshing the cache now"%str(seriesId))
        cacheFullSeriesList()
        # check again since the cache was just updated
        if not str(seriesId) in Dict['series']:
            Log.Warning("Unable to locate seriesID %s on crunchyroll.com"%str(seriesId))
            return []
    
    # the seriesId is in the cache so return the list of seasonIds
    return Dict['series'][str(seriesId)]['seasonList']

def GetSeasonDict(seasonId):
    # make sure the seasonId is in the cache
    if not str(seasonId) in Dict['seasons']:
        Log.Debug("Did not find seasonsID %s in the cache. refreshing the cache now"%str(seasonId))
        cacheFullSeriesList()
        # check again since the cache was just updated
        if not str(seasonId) in Dict['seasons']:
            Log.Warning("Unable to locate seasonID %s on crunchyroll.com"%str(seasonId))
            return []
    
    # the seriesId is in the cache so return the list of seasonIds
    return Dict['seasons'][str(seasonId)]

def GetListOfEpisodesInSeason(seasonId):
    # make sure the seasonId is in the cache
    if not str(seasonId) in Dict['seasons']:
        Log.Debug("Did not find seasonID %s in the cache. refreshing the cache now"%str(seasonId))
        cacheFullSeriesList()
        # check again since the cache was just updated
        if not str(seasonId) in Dict['seasons']:
            Log.Warning("Unable to locate seasonID %s on crunchyroll.com"%str(seasonId))
            return []
    
    # the seriesId is in the cache so return the list of seasonIds
    #TODO: should probably add some code to make sure that the list is up to date.
    if Dict['seasons'][str(seasonId)]['epsRetreived'] is None or (datetime.utcnow() - Dict['seasons'][str(seasonId)]['epsRetreived']).hours > 5:
        cacheEpisodeListForSeason(seasonId)
        Dict['seasons'][str(seasonId)]['epsRetreived'] = datetime.utcnow()
        
    return Dict['seasons'][str(seasonId)]['epList']

def GetEpisodeDict(mediaId):
    """
    return an episode dict object identified by mediaId.
    If you know the mediaId, it SHOULD be in the cache already.
    If not, you could get None if recovery doesn't work. This might 
    happen with mediaId's that come from the great beyond 
    (queue items on server, e.g.) and are in series with a lot of episodes.
    Sry bout that.
    """
    if str(mediaId) not in Dict['episodes']:
        # get brutal
        recoverEpisodeDict(mediaId)
        
    return Dict['episodes'].get(str(mediaId))


def SeriesTitleToUrl(title):
    toremove = ["!", ":", "'", "?", ".", ",", "(", ")", "&", "@", "#", "$", "%", "^", "*", ";", "~", "`"]
    for char in toremove:
        title = title.replace(char, "")
    title = title.replace("  ", " ").replace(" ", "-").lower()
    while "--" in title:
        title = title.replace("--","-")
    if title in SERIES_TITLE_URL_FIX.keys():
        title = SERIES_TITLE_URL_FIX[title]
    url = "%s/%s.rss" % (BASE_URL, title)
    Log.Debug("Series URL:" + url)
    return url

def GetVideoInfo(mediaId, availRes):

    if not mediaId:
        #occasionally this happens, so make sure it's noisy
        raise Exception("#####getVideoInfo(): NO MEDIA ID, SORRY!")
        
    url = "http://www.crunchyroll.com/xml/?req=RpcApiVideoPlayer_GetStandardConfig&media_id=%s&video_format=102&video_quality=10&auto_play=1&show_pop_out_controls=1&pop_out_disable_message=Only+All-Access+Members+and+Anime+Members+can+pop+out+this" % mediaId
    html = HTML.ElementFromURL(url)
    episodeInfo = {}
    episodeInfo['baseUrl'] = MEDIA_URL + str(mediaId)
    episodeInfo['availRes'] = availRes
    # width and height may not exist or may be bogus (Bleach eps 358)
    try:
        width = float(html.xpath("//stream_info/metadata/width")[0].text)
        height = float(html.xpath("//stream_info/metadata/height")[0].text)
        ratio = width/height
    except (IndexError, ValueError, TypeError):
        ratio = 1
        
    d = html.xpath("//stream_info/metadata/duration")
    if len(d):
        try: episodeInfo['duration'] = int(float(d[0].text)*1000)
        except Exception, arg:
            Log.Debug(repr(arg) + "\nsetting duration to 0")
            episodeInfo['duration'] = 0
    else:
        Log.Debug("#########Couldnt find duration")
        episodeInfo['duration'] = 0
    
    n = html.xpath("//media_metadata/episode_number")
    if len(n):
        try: episodeInfo['episodeNum'] = int(html.xpath("//media_metadata/episode_number")[0].text)
        except (ValueError, TypeError): episodeInfo['episodeNum'] = 0
    else: episodeInfo['duration'] = 0
    
    episodeInfo['wide'] = (ratio > 1.5)
    return episodeInfo

def GetAvailResForMediaId(mediaId):
    """
    given an mediaId, return a list of integers
    of available heights.
    
    If user is a guest, just return 360, which
    is all they get ;-)
    """
    
    if not Prefs['username'] or not Prefs['password']:
        return [360]

    login()

    availRes = [360]
    url = "%s/media-%s"%(BASE_URL,str(mediaId))
    link = url.replace(BASE_URL, "")
    req = HTTP.Request(url=url, immediate=True, cacheTime=3600*24)
    html = HTML.ElementFromString(req)
    
    try: 
        small = not isPremium()

    except: small = False

    if small is False:
        try:
            if len(html.xpath("//a[@token='showmedia.480p']")) > 0:
                availRes.append(480)
            if len(html.xpath("//a[@token='showmedia.720p']")) > 0:
                availRes.append(720)        
            if len(html.xpath("//a[@token='showmedia.1080p']")) > 0:
                availRes.append(1080)

        except Exception,arg:
            Log.Error("####getAvalResFromPage() we got ourselves an exception:")
            Log.Error(repr(Exception) + repr(arg))
    
    return availRes

def GetVideoMediaIdFromLink(link):
    mtmp = link.split(".com/")[1].split("/")[1].split("-")
    mediaId = int(mtmp[len(mtmp)-1])
    return mediaId

def GetEpInfoFromLink(link):
    #FIXME: currently this works fine for Queue items, which include
    # the title in the link, but should fail horribly
    # with "www.crunchyroll.com/media-45768" style links
    # which are given by feedburner, et. al.
    # furthermore, rss feeds that we use to populate the Dict{} may not contain all episodes.
    mediaId = getVideoMediaIdFromLink(link)
    if not str(mediaId) in Dict['episodes']:
        seriesname = link.split(".com/")[1].split("/")[0]
        url = seriesTitleToUrl(seriesname)
        getEpisodeListFromFeed(url) #TODO: investigate reason for calling this...
    episode = getEpisodeDict(mediaId)
    return episode

def GetMetadataFromUrl(url):
    episodeId = url.split(".com/")[1].split("/")[1].split("-")
    episodeId = episodeId[len(episodeId)-1]
    if not str(episodeId) in Dict['episodes']:
        seriesName=url.split(".com/")[1].split("/")[0]
        getEpisodeListFromFeed(BASE_URL+"/%s.rss"%seriesName)
    episodeData = getEpisodeDict(mediaId)
    metadata = {
        "title": episodeData['title']
    }
    return metadata


def GetPrefRes(availRes):

    if not Prefs['username'] or not Prefs['password']:
        return 360 # that's all you get
    login()
    preferredRes = 360

    if Prefs['quality'] == "Ask":
        #bwaaat? shouldn't call this
        Log.Error("####Can't determine preferred res because user wants to choose!")
    else:
        # the assumption is that the user chooses a resolution
        # (instead of "highest available") to control bandwidth/cpu use
        # so pick the highest res that is <= user's selection
        preferredRes = Quality2Resolution[Prefs['quality']]    
    
    if len(availRes):
        reslist = availRes

        # lowest first
        reslist.sort()
        
        chosenRes = 360 # in case reslist is empty
        for res in reslist:
            if res <= preferredRes:
                chosenRes = res
            else:
                break
    
    return chosenRes

def GetVideoUrl(videoInfo, resolution):
    """
    construct a URL to display at resolution based on videoInfo
    without checking for coherence to what the site's got
    or if the resolution is valid
    """
    url = videoInfo['baseUrl']+"?p" + str(resolution) + "=1"
    url = url + "&skip_wall=1"
    url = url + ("&t=0" if Prefs['restart'] == 'Restart' else "")
    url = url + "&small="+("1" if videoInfo['small'] is True else "0")
    url = url + "&wide="+("1" if videoInfo['wide'] is True or JUST_USE_WIDE is True else "0")
    return url








