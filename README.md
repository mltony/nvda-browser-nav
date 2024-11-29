# BrowserNav addon for NVDA

This add-on provides NVDA users powerful navigation commands in browser mode. It works in web browsers, as well as any other applications that support NVDA browse mode, such as Word documents and email clients.

## Download

Please install via add-on store.

## Usage in browsers and other programs that support browse mode

Please note, that starting with NVDA v2024.2, vertical navigation and same style navigation commands are now available in NVDA core. It is preferred to use builtin commands. They are not assigned any default gesture, so gestures must be assigned by the user in Input gestures dialog.

BrowserNav can be used to navigate by horizontal offset from the left edge of the screen, by font size, or by font style. 

* When navigating by horizontal offset, you can easily find paragraphs that are vertically aligned on the page. IN particular, you can press NVDA+Alt+DownArrow or UpArrow to jump to the next or previous paragraph that has the same offset. For example, this can be useful when browsing hierarchical trees of comments (e.g. on reddit.com) to jump between first level comments and skipping all the higher level comments.
* When navigating by font size, you can easily find paragraphs written in the same font size, or smaller/greater font size.
* You can also navigate by font size with the constraint of same font style.

BrowserNav rotor is used to switch between these options. Depending on the setting of this rotor, BrowserNav will indicate with beeps either horizontal offset or font size of currently selected item. In addition, BrowserNav will crackle on QuickNav commands to indicate how much text has been skipped over (this feature is only available in Google Chrome and Firefox).

BrowserNav works in any browser supported by NVDA. Although some features may not be available in all browsers. BrowserNav also works in other applications that support NVDA browse mode, such as Word documents and email clients.

## Keystrokes:

* NVDA+Alt+UpArrow or DownArrow: Jump to previous or next paragraph with the same horizontal offset or font size.
* NVDA+Alt+Home or NVDA+alt+LeftArrow: Jump to previous paragraph with lesser offset or greater font size (parent paragraph).
* NVDA+Alt+End or NVDA+Control+alt+LeftArrow: Jump to next paragraph with lesser offset or greater font size (next parent paragraph).
* NVDA+Alt+PageDown or NVDA+Alt+RightArrow: Jump to next paragraph with greater offset or smaller font size (child paragraph).
* NVDA+Alt+PageUp or NVDA+Control+Alt+RightArrow: Jump to previous paragraph with greater offset or smaller font size (previous child paragraph).
* NVDA+O: Switch rotor setting between horizontal offset, font size, font size with font style.
* \\ or Shift+\\ (backslash): Scroll up or down to reveal each page element; can be useful in dynamic web pages to load all the elements; also can be useful in infinite scroll webpages to load the next chunk.
* NVDA+Shift+LeftArrow: Go back to previous location of cursor within current document.
* NVDA+E: edit semi-accessible edit boxes - see corresponding section below.
* T or Shift+T: jump to next or previous table, but place the cursor in the first cell. Sometimes NVDA puts the cursor just before the first cell and BrowserNav fixes this behavior.

## QuickJump Bookmarks

BrowserNav QuickJump bookmarks is a powerful tool that allows to navigate around web pages and automate some repetitive actions.

### Bookmark keystrokes

* NVDA+J: Show quickJump popup menu.
* J or Shift+J: Jump to next or previous QuickJump bookmark.
* / and Control+/: Toggle SkipClutter mode for navigating by line (Up and Down arrows) and by paragraph (Control+Up and Control+Down arrows) correspondingly.
* Alt+J: click all QuickClick bookmarks on the current page.
* Control+J: Speak all QuickSpeak bookmarks on the current page.
* Alt+1, Alt+2, ..., Alt+0: jump to next hierarchical bookmark of corresponding level. 0 corresponds to level 10.; alternatively, call numerical script if defined.
* Shift+Alt+1, Shift+Alt+2, ..., Shift+Alt+0: jump to previous hierarchical bookmark.
* Alt+` or Shift+Alt+`: jump to next or previous hierarchical bookmark of any level.

You can also configure custom keystrokes for most bookmark types (except for SkipClutter, Hierarchical and Numeric Script bookmarks).

### Sites

The first thing you would need to configure is the site where you want to create bookmarks. In most cases you would want to specify match type to be either domain match or Match domain and its subdomains. To illustrate the latter option, you can specify:

* URL: amazon.com
* Match type: Match domain and its subdomains
* This will match amazon.com, smile.amazon.com and all other *.amazon.com domains.

If you need finer control, you can also specify exact URL or define a regular expression for URL.

Because of this flexible definition, on every given webpage multiple QuickJump sites might be active at the same time.

### Bookmark types

Once you have configured site definition, you can proceed to define some bookmarks on it.

BrowserNav  supports several types of bookmarks:

* QuickJump bookmarks: you can jump to them by pressing J or Shift+J.
* SkipClutter bookmarks: These bookmarks are skipped automatically when navigating by line (Up/Down arrow) or by paragraph (Control+Up/Down arrows). This allows to hide clutter on webpages, such as empty lines, timestamps and any other redundant information. The information is not removed completely, SkipClutter can be temporarily disabled via / or Control+/ commands. By default SkipClutter skips empty paragraphs on all websites.
* QuickClick bookmarks: you can mark clickable elements, such as links, buttons or checkboxes to be QuickClick bookmarks. Then by pressing Alt+J you can quickly press all QuickClick bookmarks on current page with a single keystroke without moving the cursor. This can come in handy to press a frequently used button on a website, such as play button on YouTube or Mute button on video-conferencing websites.
* QuickSpeak bookmarks: you can read this type of bookmarks by pressing Control+J keystroke; Curosr won't move. This is handy to check frequently changed elements of the page. You can also set quickClick bookmark to be autorefreshable, that is BrowserNav will scan the page preiodically and would auto-speak if matched text changes.
* Hierarchical bookmarks: this is similar to quickJump bookmarks, but this takes into account horizontal offset of a bookmark. Sites like Reddit and Hacker News have a hierarchical tree of comments, that was pretty challenging to efficiently navigate for screenreader users. On these websites you can mark comments as a hierarchical bookmark and then you can navigate between them By pressing Alt+digit or Shift+Alt+ditgit, where digit stands for number row 1,2,3,...0 - that is the level of the comment. By default BrowserNav has hierarchical bookmarks configured for Hacker News and reddit.com.
* Script bookmarks: Just execute provided script when invoked.
* Numeric script: press Alt+0 through Alt+9 to execute script taking a number as its input. Can be handy for example to jump to `i`-th bookmark on the page in a single keystroke.

### Creating a new bookmark

Once you have configured a site, the easiest way to create a new bookmark would be to navigate to the desired paragraph in the document , press NVDA+J to show bookmarks context menu and select Bookmarks > Create new bookmark for site ...

Bookmark configuration dialog will open. You can now customize bookmark. You can change how text is matched (e.g. string match or regular expression).

Other options in this dialog:

* Category: defines bookmark type.
* Display name: optional name of this bookmark for better readability. This just gives a better name so that you can identify this bookmark in a long list of bookmarks.
* Spoken message when bookmark is found: optional message to speak every time you hit this bookmark in the document.
* Offset in paragraphs: after finding matched text BrowserNav will then shift cursor by this many paragraphs forward or back. This can be useful for example if target text that you want to jump to doesn't contain any common text that can be matched (e.g. forum post), but a preceding paragraph contains a matchable word (e.g. upvote). In this case you can match the word upvote and specify offset=1, to place the cursor on the first paragraph of the post instead of the word upvote.
* Attributes: space-separated list of paragraph attributes that are matched against. The list of available attributes for current paragraph is available in the next form field. List of attributes is prepopulated with some common roles and typically you don't need to edit it.
* Available attributes in current paragraph : these are all the attributes found in current paragraph. You can select and press Space to add them to the list of matched attributes.

### Advanced site options

In site configuration dialog you can specify a number of advanced options:

* Display name: optional display name for better readability in the list of sites.
* Focus mode: this allows to override default handling of focus events in NVDA. Certain websites misuse focus events. In order to use them more conveniently, you can either ignore focus events, or alternatively disable automatic entering of focus mode when a focus event is received.
* Live region mode: Some website misuse live regions. This option allows to disable live region announcements for current website only.
* Debug beep mode: this is mostly good for debugging purposes. You can make NVDA beep when certain event (focus, live region update or successful QuickClick) happened.

### Scripting

Starting from BrowserNav v2.5 you can customize your bookmarks with Python scripting. Scripting can be used for two purposes:
1. To enhance matching algorithm  where existing match options are not enough. This applies to QuickJump, QuickSpeak, QuickClick, hierarchical and SkipClutter bookmarks.
2. To execute arbitrary Python code in order to automate certain actions on the web pages. This can be done via Script or Numeric Script bookmarks.

#### Scripting API

In your script you are provided the following variables:
* `p` - current paragraph. This is an instance of `Paragraph` class defined in [paragraph.py](addon/globalPlugins/browserNav/paragraph.py)
* `t` - current `textInfo` object.

It is recommended to work with paragraphs, since they provide higher level interface then `textInfo`s.

Your script must decide whether current paragraph matches your custom rule or not. You can either:

* Return `True` if it matches, otherwise `False`.
* Return `None` or no `return` statement to indicate no match.
* Return an integer number `i` to indicate that `i`-th following or `i`-th preceding paragraph matches and must be spoken instead of current paragraph.
* Return tuple `(i: int, s:str)` to indicate match with offset (see previous point) and have BrowserNav speak message `s`.
* Call `match()` function to indicate a match. This function internally raises an Exception, so that execution of your script will be terminated after calling match. The function is defined as:
    ```
    def match(
        offset: int | TextInfo | Paragraph = None,
        message: str|TextInfo|Paragraph = None,
        xLocation: int|TextInfo|Paragraph = None) -> None,
    )
    ```
    * `message` is an optional message to be spoken before match.
    * `xLocation` is optional and is only used in hierarchical bookmarks to calculate the level.

You are also allowed to import any modules and write general purpose scripts.

You can use `print()` statement to debug your script: the output will be printed to NVDA log.

#### Example scripts

1. This script checks that current paragraph is a link and that the text of the previous heading level 5 starts with text of current paragraph:
    ```
    try:
        if controlTypes.Role.LINK in p.roles and p.previousHeading5.textInfo.text.startswith(p.text):
            print(f"pp5 {p.previousHeading5.textInfo.text}")
            return True
    except NotFoundError:
        return None
    ```
2. This script doesn't perform a match, but activates the last edit box on the page:
    '''
    p.end.previous.previousEdit.activate()
    '''
4. This script finds username, which can be one or two paragraphs ahead; then it finds the beginning of the comment by analyzing font size; then it finds the end of the comment by searching for "Reply" text. Then it matches the entire body of the comment and adds username to be spoken prior to matched text:
    ```
    user = p.next
    if user.text == "downvote":
        user = user.next
    try:
        username = user.text.split()[0]
    except IndexError:
        username = '?'
    pp = p
    begin = None
    for i in range(5):
        fs = pp.attributes.get(ParagraphAttribute.FONT_SIZE, [])
        #print(f"i={i} fs={fs}")
        if '9_pt' in fs:
            begin = pp
            break
        pp = pp.next
    else:
        return
    end = begin
    while end.text != 'reply':
        end = end.next
    match(textInfoRange(begin, end), username)
    ```
5. This script is a generator, which means whatever it yields will be used as sleep time before the next line is executed. This script will be executed in a background thread in a non-blocking manner.
    This script performs a series of actions:
    * Finds a button with a given name and presses it.
    * Enters dialog that pops up: `p.home.nextEmbeddedObject.activate()`
    * Obtains newly focused element within that dialog: `d = getFocusParagraph()`
    * Finds and checks checkbox in that dialog.
    * Finds another button in that dialog window by name and presses it.
    These steps are repeated 20 times via `retry` function. Then after 500 ms pause, it finds "Run Query" button and presses it.
    ```
    def waitForDialogAndClickCheckbox():
        try:
            p.home.find("Link Last Used").activate()
            p.home.nextEmbeddedObject.activate()
        except NotFoundError:
            pass
        d = getFocusParagraph()
        c = d.home.nextCheckBox
        if controlTypes.State.CHECKED not in c.obj.states:
            c.activate() 
        d.home.find("Link QCPR Project").activate()
    
    yield from retry(waitForDialogAndClickCheckbox, count=20)
    yield 500
    yield from retry(lambda: p.home.find("Run Query").activate(), count=10)
    ```
6. This is a numeric script since it takes `level` as input variable. This finds `level`-th edit box from the beginning of the page (or from the end if level is negative) and invokes `script_editJupyter` on it.
    ```
    if level > 0:
        p = p.home
        for i in range(level):
            p = Paragraph(p.nextEdit.textInfo)
    elif level <= 0:
        level = 1-level
        p = p.end.previous
        tones.beep(500, 50)
        for i in range(level):
            p = Paragraph(p.previousEdit.textInfo)
        else:
            tones.beep(500, 50)
    p.textInfo.obj.currentFocusableNVDAObject = p.textInfo.focusableNVDAObjectAtStart
    p.textInfo.obj.script_editJupyter(None)
    ```
### Configuration

Bookmark definitions are stored in NVDA configuration directory in file `browserNavRules.json`. You can edit this file manually or share it with someone.

NVDA Configuration directory can be found by opening Start menu and typing: Explore NVDA user configuration directory.

BrowserNav comes with default configuration file with sample bookmarks.

## Editing semi-accessible edit boxes

Many modern web applications, notably Jupyter among others, use edit boxes, that are not that accessible, e.g. they appear blank, but you can copy text in and out of them using Control+A, Control+C and Control+V keystrokes.

BrowserNav offers an experimental feature to edit those edit boxes in a more convenient way. IN order to use it:

1. Find edit box in the browser window.
2. Press NVDA+E.
3. A new window will appear with the contents of that edit box.
4. Edit the contents of that edit box in this window.
5. Once you're done, you can press Escape to close the accessible edit window and update the edit box on the web page.
6. Alternatively, you can press Control+Enter, Shift+Enter or Alt+Enter. This will close the edit window, update the edit box and pass on the gesture on to the web application.
7. In order to close the edit window without saving changes, press Alt+F4.
8. At any time, if the contents of previously edited text is lost, press NVDA+Control+E to copy it to clipboard.

Notes:

* Do not change the state of the browser, e.g. do not switch tabs and do not focus other elements within the tab while edit text window is open. Doing so will prevent BrowserNav from correctly updating text in the edit box.
* Make sure to release Control, Shift or Alt modifiers quickly affter pressing Control+Enter, Shift+Enter, or Alt+Enter. Holding them for over a second will cause problems.
* This feature is currently experimental. Please expect only about 90-95% success rate.
* It has been thoroughly tested with Google Chrome and Firefox. It might work in other browsers, but there's a higher chance of issues, such as information loss.

## Source code

Source code is available at <http://github.com/mltony/nvda-indent-nav>.
