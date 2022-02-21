# ObjectStorageHelper

对象存储同步助手

## variables available

| 内置变量 | 描述                         |
| -------- | ---------------------------- |
| source   | 程序参数中source所指向的目录 |
| workdir  | 程序当前工作目录             |
| apath    | 绝对路径                     |
| rpath    | 相对路径                     |

```
cache-file: source, workdir
command-workdir: 所有对应指令自身可用的变量
command.download-cache: source, workdir
command.upload-cache: apath, source, workdir
command.delete-file: apath, rpath, source, workdir
command.delete-dir: apath, rpath, source, workdir
command.upload-file: apath, rpath, source, workdir
command.upload-dir: apath, rpath, source, workdir