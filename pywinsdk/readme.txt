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