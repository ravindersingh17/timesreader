import os, sys,json, time
from textwrap import TextWrapper
import timescrawler
from threading import Thread
from queue import Queue
from displaylib import Display

app_dir = os.path.join(os.path.expanduser("~"), ".nytreader")
CACHE_TIME = 3600

def getapikey():
    return json.loads(open(os.path.join(app_dir, "api.json")).read())["key"]

def runsearch():
    print("Not implemented yet")
    return

def get_comments_wrapper(link, q):
    q.put(timescrawler.get_comments(link))


def wrap_article_to_disp(content, width):
    return TextWrapper(width).wrap("\n".join(content["body"]))

def get_story_from_cache(link):
    filename = link[len(timescrawler.NYT_URL):].replace("/","_")
    if not os.path.exists(os.path.join(app_dir, "articles", filename)): return False
    return json.loads(open(os.path.join(app_dir, "articles", filename)).read())

def save_story_to_cache(link, content):
    filename = link[len(timescrawler.NYT_URL):].replace("/","_")
    if not os.path.exists(os.path.join(app_dir, "articles")): os.mkdir(os.path.join(app_dir, "articles"))
    with open(os.path.join(app_dir, "articles", filename), "w") as f: f.write(json.dumps(content))

@Display.new_screen
def showarticle(disp, link):
    content = get_story_from_cache(link)
    if not content:
        disp.set_status("Fetching article ...")
        content = timescrawler.get_story_text(link)
        save_story_to_cache(link, content)
        disp.set_status("")
    article_screen = disp.active_screen
    _, screenwidth = disp.getscreenmaxyx()
    disp.set_title(content["title"])
    wrapped_article = wrap_article_to_disp(content, screenwidth)
    disp.insert_content(article_screen, wrapped_article)
    key = 0
    q = Queue()
    comments = {}
    comment_thread = Thread(target=get_comments_wrapper,args=(link, q))
    comment_thread.start()
    while True:
        key = disp.getkey(False)
        if key == "q": break
        elif key == "DOWN": disp.scroll(1)
        elif key == "UP": disp.scroll(-1)
        elif key == "c":
            if not comments:
                disp.set_status("Comments not processed yet")
                continue
            showcomments(disp, link, comments)
        elif key == "r":
            disp.set_status("Refreshing page..")
            content = timescrawler.get_story_text(link)
            save_story_to_cache(link,content)
            disp.set_status("")
            disp.insert_content(article_screen, wrap_article_to_disp(content, screenwidth))

        else:
            if not comments:
                try:
                    comments = q.get(False)
                    disp.set_status("%d Comments" % (comments["total"]))
                except:
                    pass
            time.sleep(.1)


def fill_screen_comments(disp,screen, comments):
    _,maxx = disp.getscreenmaxyx(screen)
    comments_map = []
    for idx, c in enumerate(comments):
        comments_map.append(disp.add_content(screen, "%s (%s Recommend)\n"%(c["userDisplayName"], \
                c["recommendations"]), 0, 1))
        for line in TextWrapper(maxx).wrap(c["commentBody"]): disp.add_content(screen, line + "\n")
        for r in c["replies"]:
            disp.add_content(screen, "%s (%s Recommend)\n"%(r["userDisplayName"],r["recommendations"]),\
                    5, 1)
            for line in TextWrapper(maxx -5).wrap(r["commentBody"]):disp.add_content(screen, line + "\n", 5)
    return comments_map

@Display.new_screen
def showcomments(disp, link, comments):
    comment_screen = disp.active_screen
    tab_bar = {"tabs":["NYT Picks", "Reader Picks"], "active": 0}
    mode = "nytpicks"
    comments_map = {"nytpicks":{"map":[], "active":0}, "readerpicks":{"map":[], "active":0}}
    if comments["nytpicks"]:
        comments_map["nytpicks"]["map"] = fill_screen_comments(disp, comment_screen, comments["nytpicks"])
        disp.add_highlight(comment_screen, 0)
    else:
        del(tab_bar["tabs"][0])
        mode = "readerpicks"
    disp.set_title(tab_bar)
    reader_screen = disp.add_screen() if mode == "nytpicks" else comment_screen
    comments_map["readerpicks"]["map"] = fill_screen_comments(disp, reader_screen, comments["readerpicks"])
    disp.add_highlight(reader_screen, 0)
    curscreen = comment_screen if mode == "nytpicks" else reader_screen
    disp.switch_to_screen(curscreen)


    while True:
        curscreen = comment_screen if mode == "nytpicks" else reader_screen
        key = disp.getkey(False)
        if key == "q": break
        elif key == "DOWN": disp.scroll(1)
        elif key == "UP": disp.scroll(-1) 
        elif key == "r":
            if not comments["nytpicks"] or mode == "readerpicks": continue
            tab_bar["active"] = 1
            disp.set_title(tab_bar)
            disp.switch_to_screen(reader_screen)
            mode = "readerpicks"
        elif key == "n":
            if not comments["nytpicks"] or mode == "nytpicks": continue
            tab_bar["active"] = 0
            disp.set_title(tab_bar)
            disp.switch_to_screen(comment_screen)
            mode = "nytpicks"
        elif key == "TAB":
            disp.remove_highlight(curscreen, comments_map[mode]["active"])
            cur_idx = comments_map[mode]["map"].index(comments_map[mode]["active"])
            try: comments_map[mode]["active"] = comments_map[mode]["map"][cur_idx + 1]
            except IndexError: comments_map[mode]["active"] = 0
            disp.add_highlight(curscreen, comments_map[mode]["active"])
            disp.screens[curscreen]["curpos"] = comments_map[mode]["active"]
            disp.refresh()

        elif key == ord("m"):
            q = Queue()

            worker.start()
        else:
            time.sleep(.1)

def get_comments_by_offset_wrapper(story, picktype, offset, q):
    q.put(timescrawler.get_comments_by_offset(story, picktype, offset))

def get_cached_stories():
    article_cache = os.path.join(app_dir, "articlecache.json")
    if not os.path.exists(article_cache) or time.time() - os.path.getmtime(article_cache) > CACHE_TIME: return False
    return json.loads(open(article_cache).read())

def save_cached_stories(storiescache):
    with open(os.path.join(app_dir, "articlecache.json"), "w") as f:
        f.write(json.dumps(storiescache))

def runnewstoday(stdscr, use_cache = True):
    apikey = getapikey()
    disp = Display(stdscr)
    cached_stories = get_cached_stories()
    if not cached_stories or not use_cache:
        disp.set_status("Fetching Stories, please wait...")
        stories = timescrawler.get_stories_forday(apikey)
        disp.set_status("")
        save_cached_stories(stories)
    else:
        stories = cached_stories
    choice = ""
    offset = 0
    while choice != "q":
        content = []
        for i in range(offset, min(offset + 5, len(stories))):
            content.append(str(i - offset) + ": " + stories[i]["headline"]["main"])
        content.append("")
        content.append("Choose a news article to read, choose n for next pagei, p for previous, q to quit: ")
        disp.insert_content("root", content)
        choice = disp.getkey()
        if choice == "n" and offset + 5 < len(stories): offset += 5
        if choice == "p" and offset >= 5: offset -= 5
        elif choice in map(str, range(5)):
            try:
                showarticle(disp, stories[offset + int(choice)]["web_url"])
            except IndexError:
                pass
        else: continue

if __name__=="__main__":
    if len(sys.argv) < 2: Display.wrapper(runnewstoday)
    else:
        if sys.argv[1] == "-s" or sys.argv[1] == "--search":
            runsearch()
        if sys.argv[1] == "--no-cache": Display.wrapper(runnewstoday, False)
