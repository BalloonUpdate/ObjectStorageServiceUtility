# ObjectStorageServiceUtility

对象存储同步助手

## variables available

| 内置变量  | 描述                         |
| --------- | ---------------------------- |
| source    | 程序参数中source所指向的目录 |
| workdir   | 程序当前工作目录             |
| apath     | 绝对路径                     |
| rpath     | 相对路径                     |
| variables | variables中定义的变量        |

```
cache-file: source, workdir, variables
commands._workdir: [apath], [rpath], source, workdir, variables
commands.download-cache: source, workdir, variables
commands.upload-cache: apath, source, workdir, variables
commands.delete-file: apath, rpath, source, workdir, variables
commands.delete-dir: apath, rpath, source, workdir, variables
commands.upload-file: apath, rpath, source, workdir, variables
commands.upload-dir: apath, rpath, source, workdir, variables
```