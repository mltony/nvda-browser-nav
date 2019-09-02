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

BrowserNav works in any browser supported by NVDA.

Keystrokes:

* NVDA+Alt+UpArrow or DownArrow: Jump to previous or next paragraph with the same horizontal offset or font size.
* NVDA+alt+LeftArrow: Jump to previous paragraph with lesser offset or greater font size.
* NVDA+Alt+RightArrow: Jump to next paragraph with greater offset or smaller font size.
* NVDA+O: Switch rotor setting between horizontal offset, font size, font size with font style.
* P or Shift+P: Jump to next or previous paragraph.
* Y or Shift+Y: Jump to next or previous tab.

## Source code
Source code is available at <http://github.com/mltony/nvda-indent-nav>.

