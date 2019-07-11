from bs4 import BeautifulSoup as BS
import requests, re, json
from datetime import datetime

NYT_URL = "https://www.nytimes.com"
NYT_API_URL = "https://api.nytimes.com"

def get_stories_today_scrape():
    soup = BS(requests.get(NYT_URL).text, "html.parser")
    now = datetime.now()
    yearpart = "("+str(now.year -1).zfill(2) + "|" + str(now.year).zfill(2) \
            + ")" if now.month == 1 and now.day == 1 else str(now.year).zfill(2)
    monthpart = "("+str(12 if now.month == 1 else now.month - 1) + "|" + str(now.month).zfill(2) + ")" \
        if  now.day == 1 else str(now.month).zfill(2)
    searchdate = re.compile("^/%s/%s/.+" % (yearpart, monthpart))
    return list({ NYT_URL + x["href"].replace("#commentsContainer", ""):x.text for x in soup.find_all("a", { "href": searchdate}) })

def get_stories_forday(apikey):
    #date format yyyymmdd
    stories = get_stories_today_scrape()
    params = {"api-key": apikey, "page": 0}
    params["fq"] = "web_url:( " + " ".join('"'+x+'"' for x in stories) + " )"
    url = NYT_API_URL + "/svc/search/v2/articlesearch.json"
    stories = []
    while True:
        req = json.loads(requests.get(url, params=params).text)
        if not req["response"]["docs"]: break
        stories += req["response"]["docs"]
        params["page"] += 1
    return stories

def get_story_text(link):
    soup = BS(requests.get(link).text, "html.parser")
    title = soup.find("span", {"class", "css-fwqvlz"}).text

    paragraphs = soup.find_all("p", {"class": "css-exrw3m evys1bk0"})

    #Store any links found
#    for i, p in enumerate(paragraphs):
#        links = p.find_all("a", {"class": "css-1g7m0tk"})
#        for l in links: p.insert_after(l, "[link:%s]"%(l["href"]))

    ptext = [ p.text for p in paragraphs ]

    return {"title": title, "body": ptext}

def get_comments(story):
    link = NYT_URL + "/svc/community/V3/requestHandler"
    params = {
            'url': story,
            'method': "get",
            'offset': 0,
            'includeReplies': 'true',
            'sort': 'newest',
            'cmd': 'GetCommentsNYTPicks',
            }
    nytpicks = json.loads(requests.get(link, params = params).text)
    params["commentSequence"] = 0
    params["sort"] = "reader"
    params["cmd"] = "GetCommentsReadersPicks"
    readerpicks = json.loads(requests.get(link, params=params).text)
    ret = {}
    if nytpicks["status"] == "OK":
        ret["total"] = nytpicks["results"]["totalCommentsFound"]
        ret["parentcomments"] = nytpicks["results"]["totalParentCommentsFound"]
        ret["replycomments"] = nytpicks["results"]["totalReplyCommentsFound"]
        ret["nytpicks"] = nytpicks["results"]["comments"]
        ret["readerpicks"] = readerpicks["results"]["comments"]
    return ret

def get_comments_by_offset(story, picktype, offset):
    link = NYT_URL + "/svc/community/V3/requestHandler"
    cmd = "GetCommentsNYTPicks" if picktype == "nytpicks" else "GetCommentsReadersPicks"
    params = {
            'url': story,
            'method': "get",
            'offset': offset,
            'includeReplies': 'true',
            'limit': 25,
            'cmd': cmd,
            }
    return json.loads(requests.get(link, params = params).text)

def get_replies_for_comment(story, commentid):
    link = NYT_URL + "/svc/community/V3/requestHandler"
    params = {
            'url': story,
            'method': "get",
            'offset': 0,
            'commentSequence': commentid,
            'cmd': 'GetCommentsBySequence',
            }
    return json.loads(requests.get(link, params = params).text)


