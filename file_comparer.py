from file import File

class SimpleFileObject:
    def __init__(self, name: str, length: int = None, hash: str = None, modified: int = None, tree: list = None):
        self.name = name
        self.length = length
        self.hash = hash
        self.tree = tree
        self.modified = modified

        isFile = self.isFile
        isDir = self.isDirectory
        isValidFile = length is not None and hash is not None

        if not isFile and not isDir:
            assert False, f'unknown file type: the file type must be explicated by parameters ({self.name})'

        if isFile and isDir:
            assert False, f'inexplicit file/dir type: the file type must be either File or Directory ({self.name})'

        if isFile and not isValidFile:
            missingParameter = 'length' if length is None else 'hash'
            assert False, f'missing necessary parameter: {missingParameter} ({self.name})'

    @staticmethod
    def FromDict(obj: dict):
        if 'tree' in obj:
            tree = [SimpleFileObject.FromDict(f) for f in obj['tree']]
            return SimpleFileObject(obj['name'], tree=tree)
        else:
            return SimpleFileObject(obj['name'], length=obj['length'], hash=obj['hash'], modified=obj['modified'])

    @staticmethod
    def FromFile(file: File):
        if file.isDirectory:
            tree = [SimpleFileObject.FromFile(f) for f in file]
            return SimpleFileObject(file.name, tree=tree)
        else:
            return SimpleFileObject(file.name, length=file.length, hash=file.sha1, modified=file.modified)

    @property
    def isDirectory(self):
        return self.tree is not None

    @property
    def isFile(self):
        return self.length is not None or self.hash is not None

    @property
    def files(self):
        if not self.isDirectory:
            raise NotADirectoryError(f"'{self.name}' is not a Directory")
        return self.tree

    @property
    def sha1(self):
        return self.hash

    def getByName(self, name):
        for child in self.tree:
            if child.name == name:
                return child
        return None

    class Iter:
        def __init__(self, obj):
            self.files = obj.files
            self.index = 0
            self.end = len(self.files)

        def __next__(self):
            if self.index < self.end:
                ret = self.files[self.index]
                self.index += 1
                return ret
            else:
                raise StopIteration

    def __getitem__(self, name: str):
        if not isinstance(name, str):
            raise TypeError(f"The file must be a string, not '{name}' ({type(name)})")

        if not self.__contains__(name):
            raise FileNotFoundError(f"'{name}' is not found")

        return self.getByName(name)

    def __call__(self, relPath):
        return self.__getitem__(relPath)

    def __contains__(self, file: str):
        if not isinstance(file, str):
            raise TypeError(f"The key must be a string, not '{file}' ({type(file)})")

        for subFile in self.tree:
            if subFile.name == file:
                return True

        return False

    def __len__(self):
        return len(self.tree)

    def __iter__(self):
        return self.Iter(self)


class FileComparer2:
    def __init__(self, basePath: File, compareFunc=None):
        super().__init__()
        self.basePath = basePath

        def defaultCompareFunc(remote: SimpleFileObject, local: File, path: str):
            return remote.sha1 == local.sha1

        self.compareFunc = compareFunc if compareFunc is not None else defaultCompareFunc

        self.oldFiles = []
        self.oldFolders = []
        self.newFiles = []
        self.newFolders = []

    def findNewFiles(self, current: SimpleFileObject, template: File):
        """????????????????????????(?????????????????????)
        :param current: ??????????????????(??????)
        :param template: ??????????????????(??????)
        """

        for t in template:
            if t.name not in current:  # ???????????????
                self.addNewFile(SimpleFileObject.FromFile(t), t)
            else:  # ??????????????????????????????????????????
                corresponding = current(t.name)

                if t.isDirectory:
                    if corresponding.isFile:
                        # ??????????????????????????????
                        self.addOldFile(corresponding, template.relPath(self.basePath))
                        self.addNewFile(corresponding, t)
                    else:
                        self.findNewFiles(corresponding, t)
                else:
                    if corresponding.isFile:
                        # if corresponding.sha1 != t.sha1:  # ??????hash
                        if not self.compareFunc(corresponding, t, t.relPath(self.basePath)):
                            # ??????????????????????????????
                            self.addOldFile(corresponding, template.relPath(self.basePath))
                            self.addNewFile(corresponding, t)
                    else:
                        # ??????????????????????????????
                        self.addOldFile(corresponding, template.relPath(self.basePath))
                        self.addNewFile(corresponding, t)

    def findOldFiles(self, current: SimpleFileObject, template: File):
        """??????????????????????????????
        :param current: ??????????????????(??????)
        :param template: ??????????????????(??????)
        """

        for c in current:
            if c.name in template:
                corresponding = template(c.name)
                # ???????????????????????????????????????????????????
                if c.isDirectory and corresponding.isDirectory:
                    self.findOldFiles(c, corresponding)
                # ??????????????????findMissingFiles?????????????????????????????????????????????
            else:  # ????????????????????????????????????????????????????????????
                self.addOldFile(c, template.relPath(self.basePath))

    def addOldFile(self, file: SimpleFileObject, dir: str):
        """???????????????????????????/??????
        :param file: ???????????????(??????/??????)
        :param dir: file???????????????(??????/??????)
        """
        path = dir + '/' + file.name
        pathWithoutDotSlash = path[2:] if path.startswith('./') else path

        if file.isDirectory:
            for u in file:
                if u.isDirectory:
                    self.addOldFile(u, path)
                else:
                    newPath = path + '/' + u.name
                    self.oldFiles += [newPath[2:] if newPath.startswith('./') else newPath]

            self.oldFolders += [pathWithoutDotSlash]
        else:
            self.oldFiles += [pathWithoutDotSlash]

    def addNewFile(self, missing: SimpleFileObject, template: File):
        """???????????????????????????
        :param missing: ?????????????????????(??????/??????)
        :param template: ????????????(??????/??????)
        :return:
        """

        if missing.isDirectory != template.isDirectory:
            assert False, 'the types did not equal'

        if missing.isDirectory:
            folder = template.relPath(self.basePath)
            if folder not in self.newFolders and folder != '.':
                self.newFolders += [folder]
            for m in missing:
                mCorresponding = template(m.name)
                if m.isDirectory:
                    self.addNewFile(m, mCorresponding)
                else:
                    self.newFiles += [mCorresponding.relPath(self.basePath)]
        else:
            self.newFiles += [template.relPath(self.basePath)]

    def compareWithSimpleFileObject(self, current: File, template: SimpleFileObject):
        self.findNewFiles(template, current)
        self.findOldFiles(template, current)

    def compareWithList(self, current: File, template: list):
        template2 = {'name': '', 'tree': template}
        self.findNewFiles(SimpleFileObject.FromDict(template2), current)
        self.findOldFiles(SimpleFileObject.FromDict(template2), current)
