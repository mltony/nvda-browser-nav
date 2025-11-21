2025 note: I used to have relative import converter to avoid package clashes. However the monolith package appears to have been deprecated. separate winrt packages are still available, but presumably it'll be much harder to make them relative yet still see each other. Therefore just use absolute packages and add them to sys.path. Hope we won't suffer from package conflicts.

```
c:\python313\python -m pip install  winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.ApplicationModel.DataTransfer
```
Then, navigate to `C:\Python313\Lib\site-packages`:
```
cp -r winrt* H:\mltony\nvda-browser-nav\addon\globalPlugins\browserNav\site-packages\ 
```

Then ld instructions

python-winsdk appears to be abandoned as of 2025.

We use modified version of python-winsdk package:
https://github.com/pywinrt/python-winsdk
Steps to cook it:
1. pip install winsdk
2. Get the package internals from C:\Python37-32\Lib\site-packages\winsdk into raw\
3. Leave only what we need - e.g. clipboard functionality and dependencies and delete all the rest.
4. Run convertTORelativeImport.py - to convert all imports in python code to relative versions.
This would allow to use this code without modifying sys.path.append.
5. Cooked version is in relative\ directory.
4. Run 