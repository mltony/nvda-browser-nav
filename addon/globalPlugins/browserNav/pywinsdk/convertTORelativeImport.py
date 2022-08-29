import os,re,sys

sourceDir = r'.\raw'
destDir = r'.\relative'
# Make sure to include cygwin in your path. We use unix commands like cp, rm, ...

os.system(f"rm -rf {destDir}")
os.system(f"mkdir {destDir}")

importRe = re.compile(r"^\s*(?:from|import)\s+(\S+)")
def processLine(path, line):
    m  =importRe.search(line)
    if not m:
        return line
    module = m.group(1)
    if module[0] == '.':
        #print (line)
        return line
    tokens = module.split(".")
    if tokens[0] != path[0]:
        #print(f"2 {tokens[0]} != {path[0]}")
        return line
    #print("zip")
    #print(list(zip(tokens, path)))
    try:
        i=0
        while True:
            if tokens[i] != path[i]:
                break
            i += 1
    except IndexError:
        pass
    # now i is the index of the first position where tokens[i] != path[i]
    dots = "." * (len(path) - i + 1)
    if line.lstrip().startswith("import"):
        n = len(tokens)
        print(f"tokens = {tokens}")
        print(f'path={path}')
        print(f"i={i} n={n}")
        
        if False:
            if i == n:
                _import = "__init__"
            else:
                _import = tokens[n-1]
        else:
            _import = tokens[n-1]
            if i == n:
                dots += '.'
        _from = dots + " " + ".".join(tokens[i:n-1])
        print(f'dots={dots}')
        _statement = f"from {_from} import {_import}"
        newLine = re.sub(r'import\s+(\S+)', _statement, line)
    elif line.lstrip().startswith("from"):
        _from = dots + " " + ".".join(tokens[i:-1])
        _statement = f"from {_from}"
        newLine = re.sub(r'from\s+(\S+)', _statement, line)
    else:
        raise Exception("WTF")
    print(f"  Replacing:\n    {line}\n    {newLine}")
    return newLine
    
def processFile(f1, f2, path):
    print(f"{f1}")
    if f1.endswith(".pyd"):
        os.system(f"cp {f1} {f2}")
        return
    if not f1.endswith(".py") and not f1.endswith(".pyi"):
        raise Exception("Unknown file type")
    lines = open(f1, "r", encoding='utf-8').readlines()
    lines = [s.rstrip("\r\n") for s in lines]
    lines = [processLine(path, line) for line in lines]
    with open(f2, "w", encoding='utf-8') as f:
        print("\n".join(lines), file=f)

def walkDir(path):
    path1 = os.path.join(sourceDir, *path)
    path2 = os.path.join(destDir, *path)
    for f in os.listdir(path1):
        if f == '__pycache__':
            continue
        f1 = os.path.join(path1, f)
        f2 = os.path.join(path2, f)
        if os.path.isdir(f1):
            os.system(f"mkdir {f2}")
            walkDir(path + [f])
        else:
            processFile(f1, f2, path)
walkDir([])
if False:
    processLine(
        r"winsdk\windows\applicationmodel\datatransfer".split("\\"), 
        "import winsdk"
    )
    processLine(
        r"winsdk\windows\foundation".split("\\"), 
        "    import winsdk.windows.foundation.collections"
    )    
