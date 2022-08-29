import os,re,sys
sys.path.append(r"H:\mltony\py_winsdk")
#sys.path.append(r"C:\Python37-32\Lib\site-packages")
# mkdir winsdk
# mkdir winsdk\windows
# mkdir winsdk\windows\applicationmodel
# cp -r  C:\Python37-32\Lib\site-packages\winsdk\windows\applicationmodel\datatransfer winsdk\windows\applicationmodel
# cp  C:\Python37-32\Lib\site-packages\winsdk\_winrt.pyd  ./winsdk/
# cp  C:\Python37-32\Lib\site-packages\winsdk\_winrt.pyi  ./winsdk/
# cp  C:\Python37-32\Lib\site-packages\winsdk\__init__.py  winsdk\
# cp  -r C:\Python37-32\Lib\site-packages\winsdk\windows/foundation  winsdk\windows/

from winsdk.windows.applicationmodel.datatransfer import Clipboard
a=Clipboard.get_history_items_async()
r=a.get_results()
q=r.items[1]
c=q.content
c.available_formats.get_at(1)
v = c.get_text_async()
v.status
res = v.get_results()
print(res)
