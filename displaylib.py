import curses
from textwrap import TextWrapper
from time import time
from hashlib import md5

class Display:
    MAX_PAD_LINES = 5000
    MAX_TAB_LINES = 20000
    MARGIN = 5
    wrapper = curses.wrapper

    def __init__(self, stdscr):
        curses.curs_set(0)
        self.stdscr = stdscr
        self.stdscr.clear()
        self.stdscr.refresh()
        self.maxy, self.maxx = self.stdscr.getmaxyx()
        self.screens = {}
        self.add_screen("root")
        self.active_screen = "root"
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_YELLOW, curses.COLOR_BLACK)

    #Decorator
    def new_screen(func):
        def create_screen(*args, **kwargs):
            disp = args[0]
            parent = disp.active_screen
            screen_id = disp.add_screen()
            disp.set_title("")
            disp.switch_to_screen(screen_id)
            func(*args, **kwargs)
            disp.switch_to_screen(parent)
            del(disp.screens[screen_id])
            return
        return create_screen

    def set_title(self, title):
        self.stdscr.move(0,0)
        self.stdscr.clrtoeol()
        if type(title) == str:
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(0,0, title)
            self.stdscr.attroff(curses.A_BOLD)
        else: #dict
            xoffset = 0
            for i,tab in enumerate(title["tabs"]):
                if i == title["active"]:
                    self.stdscr.attron(curses.A_BOLD)
                    self.stdscr.addstr(0, xoffset, tab)
                    self.stdscr.attroff(curses.A_BOLD)
                else:
                    self.stdscr.attron(curses.A_DIM)
                    self.stdscr.addstr(0, xoffset, tab)
                    self.stdscr.attroff(curses.A_DIM)
                xoffset += (len(tab) + 2)
        self.stdscr.refresh()

    def add_screen(self, screen_id = None):
        if not screen_id: screen_id = md5(str(time()).encode("utf-8")).hexdigest()
        pad = curses.newpad(Display.MAX_TAB_LINES, self.maxx - Display.MARGIN * 2)
        self.screens[screen_id] = {"pad": pad, "content": [], "curpos": 0}
        return screen_id

    def insert_content(self, screen_id, content, margin = 0, color = 3):
        if screen_id not in self.screens : return False
        curscreen = self.screens[screen_id]
        curscreen["content"] = [ " "*margin + x for x in content ]
        curscreen["curpos"] = 0
        curscreen["pad"].clear()
        for line in curscreen["content"]: curscreen["pad"].addstr(line + "\n", curses.color_pair(color))
        if self.active_screen == screen_id:
            self.refresh(screen_id)

    def add_highlight(self, screen_id, line_num):
        if not screen_id in self.screens: return False
        self.screens[screen_id]["pad"].insch(line_num, 0, ">", curses.A_BOLD | curses.color_pair(4))
        self.refresh()

    def remove_highlight(self, screen_id, line_num):
        if not screen_id in self.screens: return False
        self.screens[screen_id]["pad"].delch(line_num, 0)
        self.refresh()

    def add_content(self, screen_id, new_content, margin = 0, color = 3):
        if screen_id not in self.screens: return False
        if type(new_content) == str: new_content = [new_content]
        curscreen = self.screens[screen_id]
        screen_pos = len(curscreen["content"])
        start_pos = screen_pos
        for line in new_content:
            curscreen["content"].append(" "*margin + line)
            curscreen["pad"].addstr(screen_pos, margin, line, curses.color_pair(color))
            screen_pos += 1
        return start_pos


    def getscreenmaxyx(self, screen_id = None):
        if not screen_id: screen_id = self.active_screen
        return self.screens[screen_id]["pad"].getmaxyx()

    def getscreenyx(self, screen_id = None):
        if not screen_id: screen_id = self.active_screen
        return self.screens[screen_id]["pad"].getyx()

    def switch_to_screen(self, screen_id):
        if screen_id not in self.screens: return False
        self.active_screen = screen_id
        self.refresh(screen_id)

    def refresh(self, screen_id = None):
        if not screen_id: screen_id = self.active_screen
        if screen_id not in self.screens: return False
        curscreen = self.screens[screen_id]
        curscreen["pad"].refresh(curscreen["curpos"], 0, 1, Display.MARGIN, self.maxy - 2, self.maxx - Display.MARGIN)

    def set_status(self, status):
        self.stdscr.move(self.maxy - 1, 0)
        self.stdscr.clrtoeol()
        self.stdscr.addstr(self.maxy - 1, 0, status)
        self.stdscr.refresh()

    def getkey(self, block = True):
        if not block: self.stdscr.nodelay(1)
        else: self.stdscr.nodelay(0)
        key = self.stdscr.getch()
        if key in range(ord("a"), ord("z") + 1) or key in range(ord("A"), ord("Z") +1) or \
                key in range(ord("0"), ord("9")+1): return chr(key)
        if key == curses.KEY_UP: return "UP"
        if key == curses.KEY_DOWN: return "DOWN"
        if key == ord("\t"): return "TAB"
        return key

    def scroll(self, lines):
        curscreen = self.screens[self.active_screen]
        if lines > 0: curscreen["curpos"] = min(curscreen["curpos"]+lines, len(curscreen["content"]))
        else: curscreen["curpos"] = max(0, curscreen["curpos"]+lines)
        self.refresh()




