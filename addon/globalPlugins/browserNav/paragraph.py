#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import baseObject
import re
import textInfos

from . import quickJump

class NotFoundError(RuntimeError):
    pass
    
def textInfoRange(info1, info2):
    if isinstance(info1, Paragraph):
        info1 = info1.textInfo
    if isinstance(info2, Paragraph):
        info2 = info2.textInfo
    result = info1.copy()
    result.setEndPoint(info2, which='endToEnd')
    return result


class Paragraph(baseObject.AutoPropertyObject):
    def __init__(self, textInfo, _normalize=True, _end=None):
        info = textInfo.copy()
        if _normalize:
            info.collapse()
            info.expand(textInfos.UNIT_PARAGRAPH)
        self.textInfo = info
        # _end can be True, False, or None
        self._end = _end
        
    #@classmethod
    def move(self, offset: int):
        info = self.textInfo.copy()
        if self._end == False:
            # Special handling if we're at home position
            # offset must be positive, and to get to the first paragraph we don't have to move anywhere, so adjusting offset
            if offset < 0:
                raise NotFoundError()
            elif offset > 0:
                offset -= 1
        result = info.move(textInfos.UNIT_PARAGRAPH, offset)
        if result != offset:
            raise NotFoundError()
        return Paragraph(info)

    def _get_next(self):
        return self.move(1)

    def _get_previous(self):
        return self.move(-1)

    def _get_textInfo(self):
        return self.textInfo.copy()

    def _get_text(self):
        return self.textInfo.text

    def _get_textWithFields(self):
        return self.textInfo.getTextWithFields()

    def _get_attributes(self):
        return quickJump.extractAttributesSet(self.textInfo)

    def _get_roles(self):
        return {
            attr.value
            for attr in self.attributes
            if attr.attribute == quickJump.ParagraphAttribute.ROLE
        }

    def get_headingLevel(self):
        try:
            return max([
                attr.value
                for attr in self.attributes
                if attr.attribute == quickJump.ParagraphAttribute.HEADING
            ])
        except ValueError:
            return None

    def _homeOrEnd(self, end=False):
        info = self.textInfo.copy()
        info.expand(textInfos.UNIT_STORY)
        info.collapse(end)
        return Paragraph(info, normalize=False, end=end)

    def _get_home(self):
        return self._homeOrEnd(end=False)

    def _get_end(self):
        return self._homeOrEnd(end=True)

    def find(self, text, caseSensitive=False,reverse=False):
        info = self.textInfo.copy()
        info.collapse(end=not reverse)
        if info.find(text, caseSensitive=caseSensitive, reverse=reverse):
            info.move(len(text), unit=TextInfos.UNIT_CHARACTER, endpoint='end')
            return info
        else:
            raise NotFoundError()
            
    def findRegexp(self, regexp, caseSensitive=False,reverse=False):
        if isinstance(regexp, str):
            regexp = re.compile(regexp, flags=0 if caseSensitive else re.IGNORECASE)
        direction = -1 if reverse else 1
        p = self
        while True:
            p = p.move(direction)
            if regexp.search(p.text) is not None:
                return p
            
    def quickNavGenerator(self, itemType, reverse=False):
        info = self.textInfo.copy()
        info.collapse(end=not reverse)
        vBuf = info.obj
        iterFactory = vBuf._iterNodesByType(itemType,direction=-1 if reverse else 1,info=info)
        return iterFactory(direction, info)

    def findQuickNav(self, itemType, reverse=False):
        gen = self.quickNavGenerator(itemType, reverse)
        try:
            return next(gen)
        except StopIteration:
            raise NotFoundError()
            
    def _get_PreviousHeading(self):
        return self.findQuickNav(itemType="heading", reverse=True)
    def _get_nextHeading(self):
        return self.findQuickNav(itemType="heading", reverse=False)
    def _get_PreviousHeading1(self):
        return self.findQuickNav(itemType="heading1", reverse=True)
    def _get_nextHeading1(self):
        return self.findQuickNav(itemType="heading1", reverse=False)
    def _get_PreviousHeading2(self):
        return self.findQuickNav(itemType="heading2", reverse=True)
    def _get_nextHeading2(self):
        return self.findQuickNav(itemType="heading2", reverse=False)
    def _get_PreviousHeading3(self):
        return self.findQuickNav(itemType="heading3", reverse=True)
    def _get_nextHeading3(self):
        return self.findQuickNav(itemType="heading3", reverse=False)
    def _get_PreviousHeading4(self):
        return self.findQuickNav(itemType="heading4", reverse=True)
    def _get_nextHeading4(self):
        return self.findQuickNav(itemType="heading4", reverse=False)
    def _get_PreviousHeading5(self):
        return self.findQuickNav(itemType="heading5", reverse=True)
    def _get_nextHeading5(self):
        return self.findQuickNav(itemType="heading5", reverse=False)
    def _get_PreviousHeading6(self):
        return self.findQuickNav(itemType="heading6", reverse=True)
    def _get_nextHeading6(self):
        return self.findQuickNav(itemType="heading6", reverse=False)
    def _get_PreviousTable(self):
        return self.findQuickNav(itemType="table", reverse=True)
    def _get_nextTable(self):
        return self.findQuickNav(itemType="table", reverse=False)
    def _get_PreviousLink(self):
        return self.findQuickNav(itemType="link", reverse=True)
    def _get_nextLink(self):
        return self.findQuickNav(itemType="link", reverse=False)
    def _get_PreviousVisitedLink(self):
        return self.findQuickNav(itemType="visitedLink", reverse=True)
    def _get_nextVisitedLink(self):
        return self.findQuickNav(itemType="visitedLink", reverse=False)
    def _get_PreviousUnvisitedLink(self):
        return self.findQuickNav(itemType="unvisitedLink", reverse=True)
    def _get_nextUnvisitedLink(self):
        return self.findQuickNav(itemType="unvisitedLink", reverse=False)
    def _get_PreviousFormField(self):
        return self.findQuickNav(itemType="formField", reverse=True)
    def _get_nextFormField(self):
        return self.findQuickNav(itemType="formField", reverse=False)
    def _get_PreviousList(self):
        return self.findQuickNav(itemType="list", reverse=True)
    def _get_nextList(self):
        return self.findQuickNav(itemType="list", reverse=False)
    def _get_PreviousListItem(self):
        return self.findQuickNav(itemType="listItem", reverse=True)
    def _get_nextListItem(self):
        return self.findQuickNav(itemType="listItem", reverse=False)
    def _get_PreviousButton(self):
        return self.findQuickNav(itemType="button", reverse=True)
    def _get_nextButton(self):
        return self.findQuickNav(itemType="button", reverse=False)
    def _get_PreviousEdit(self):
        return self.findQuickNav(itemType="edit", reverse=True)
    def _get_nextEdit(self):
        return self.findQuickNav(itemType="edit", reverse=False)
    def _get_PreviousFrame(self):
        return self.findQuickNav(itemType="frame", reverse=True)
    def _get_nextFrame(self):
        return self.findQuickNav(itemType="frame", reverse=False)
    def _get_PreviousSeparator(self):
        return self.findQuickNav(itemType="separator", reverse=True)
    def _get_nextSeparator(self):
        return self.findQuickNav(itemType="separator", reverse=False)
    def _get_PreviousRadioButton(self):
        return self.findQuickNav(itemType="radioButton", reverse=True)
    def _get_nextRadioButton(self):
        return self.findQuickNav(itemType="radioButton", reverse=False)
    def _get_PreviousComboBox(self):
        return self.findQuickNav(itemType="comboBox", reverse=True)
    def _get_nextComboBox(self):
        return self.findQuickNav(itemType="comboBox", reverse=False)
    def _get_PreviousCheckBox(self):
        return self.findQuickNav(itemType="checkBox", reverse=True)
    def _get_nextCheckBox(self):
        return self.findQuickNav(itemType="checkBox", reverse=False)
    def _get_PreviousGraphic(self):
        return self.findQuickNav(itemType="graphic", reverse=True)
    def _get_nextGraphic(self):
        return self.findQuickNav(itemType="graphic", reverse=False)
    def _get_PreviousBlockQuote(self):
        return self.findQuickNav(itemType="blockQuote", reverse=True)
    def _get_nextBlockQuote(self):
        return self.findQuickNav(itemType="blockQuote", reverse=False)
    def _get_PreviousLandmark(self):
        return self.findQuickNav(itemType="landmark", reverse=True)
    def _get_nextLandmark(self):
        return self.findQuickNav(itemType="landmark", reverse=False)
    def _get_PreviousEmbeddedObject(self):
        return self.findQuickNav(itemType="embeddedObject", reverse=True)
    def _get_nextEmbeddedObject(self):
        return self.findQuickNav(itemType="embeddedObject", reverse=False)
    def _get_PreviousAnnotation(self):
        return self.findQuickNav(itemType="annotation", reverse=True)
    def _get_nextAnnotation(self):
        return self.findQuickNav(itemType="annotation", reverse=False)
    def _get_PreviousError(self):
        return self.findQuickNav(itemType="error", reverse=True)
    def _get_nextError(self):
        return self.findQuickNav(itemType="error", reverse=False)
    def _get_PreviousArticle(self):
        return self.findQuickNav(itemType="article", reverse=True)
    def _get_nextArticle(self):
        return self.findQuickNav(itemType="article", reverse=False)
    def _get_PreviousGrouping(self):
        return self.findQuickNav(itemType="grouping", reverse=True)
    def _get_nextGrouping(self):
        return self.findQuickNav(itemType="grouping", reverse=False)
