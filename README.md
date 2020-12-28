# BrowserNav addon for NVDA
This add-on provides NVDA users powerful navigation commands in browser mode.
For example, with BrowserNav you can find vertically aligned paragraphs, that is paragraphs with the same horizontal offset. This can be used to read hierarchical trees of comments or malformed HTML tables.
You can also find paragraphs written in the same font size or style.
BrowserNav also provides new QuickNav commands: P for next paragraph and Y for next tab.
## Download
* Current stable version: [BrowserNav](https://github.com/mltony/nvda-browser-nav/releases/latest/download/browsernav.nvda-addon)
* Last Python 2 version (compatible with NVDA 2019.2 and prior): [BrowserNav v1.1](https://github.com/mltony/nvda-browser-nav/releases/download/v1.1/BrowserNav-1.1.nvda-addon)

## Usage in browsers
BrowserNav can be used to navigate by  horizontal offset from the left edge of the screen, by font size, or by font style. 
* When navigating by horizontal offset, you can easily find paragraphs that are vertically aligned on the page. IN particular, you can press NVDA+Alt+DownArrow or UpArrow to jump to the next or previous paragraph that has the same offset. For example, this can be useful when browsing hierarchical trees of comments (e.g. on reddit.com) to jump between  first level comments and skipping all the higher level comments.
* When navigating by font size, you can easily find paragraphs written in the same font size, or smaller/greater font size.
* You can also navigate by font size with the constraint of same font style.

BrowserNav rotor is used to switch between these options. Depending on the setting of this rotor, BrowserNav will indicate with beeps either horizontal offset or font size of currently selected item. In addition, BrowserNav will crackle on QuickNav commands to indicate how much text has been skipped over (this feature is only available in Google Chrome and Firefox).

BrowserNav works in any browser supported by NVDA. Although some features may not be available in all browsers.

## Keystrokes:

* NVDA+Alt+UpArrow or DownArrow: Jump to previous or next paragraph with the same horizontal offset or font size.
* NVDA+Alt+Home or NVDA+alt+LeftArrow: Jump to previous paragraph with lesser offset or greater font size (parent paragraph).
* NVDA+Alt+End or NVDA+Control+alt+LeftArrow: Jump to next paragraph with lesser offset or greater font size (next parent paragraph).
* NVDA+Alt+PageDown or NVDA+Alt+RightArrow: Jump to next paragraph with greater offset or smaller font size (child paragraph).
* NVDA+Alt+PageUp or NVDA+Control+Alt+RightArrow: Jump to previous paragraph with greater offset or smaller font size (previous child paragraph).
* NVDA+O: Switch rotor setting between horizontal offset, font size, font size with font style.
* J or Shift+J: Jump to next or previous browser mark. Browser marks are keywords that you search on web pages often and can be configured in BrowserNav settings.
* Y or Shift+Y: Jump to next or previous tab.
* P or Shift+P: Jump to next or previous dialog.
* Z or Shift+Z: Jump to next or previous menu.
* \` orShift+\` (backquote or tilde): Jump to next or previous format change.
* \\ or Shift+\\ (backslash): Scroll up or down to reveal each page element; can be useful in dynamic web pages to load all the elements; also can be useful in infinite scroll webpages to load the next chunk.
* 0 or Shift+0: Jump to next or previous tree view.
* 9 or Shift+9: Jump to next or previous tool bar.
* NVDA+E: edit semi-accessible edit boxes - see next section

## Editing semi-accessible edit boxes

Many modern web applications, notably Jupyter among others,  use edit boxes, that are not that accessible, e.g. they appear blank, but you can copy text in and out of them using Control+A, Control+C and Control+V keystrokes.

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
