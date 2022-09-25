#A part of the BrowserNav addon for NVDA
#Copyright (C) 2017-2022 Tony Malykh
#This file is covered by the GNU General Public License.
#See the file LICENSE  for more details.

import baseObject
import textInfos

from . import quickJump

class EndOfDocumentException(RuntimeError):
    pass

class Paragraph(baseObject.AutoPropertyObject):
    def __init__(self, textInfo):
        info = textInfo.copy()
        info.collapse()
        info.expand(textInfos.UNIT_PARAGRAPH)
        self.textInfo = info

    def move(self, offset: int):
        info = self.textInfo.copy()
        result = info.move(textInfos.UNIT_PARAGRAPH, offset)
        if result != offset:
            raise EndOfDocumentException()
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
