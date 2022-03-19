# ObjectStorageServiceUtility

> 此项目的状态文件与[文件更新助手实用小工具](https://github.com/updater-for-minecraft/Tool)的缓存文件格式不兼容！建议删除后重新上传

对象存储助手。利用服务商提供的对象存储命令行工具进行上传（理论上支持所有服务商）

具体作用是将本地文件同步到桶里，软件会自动计算出文件差异。然后仅上传或者删除有改动的文件

软件同步方式是：本地到对象存储的**单向同步**，不会删除桶里的现有文件（但还是建议提前做备份）

## 启动参数

```shell
ossu.exe [-h] [--config CONFIG] [--debug] [--dry-run] source-dir

# source-dir 要上传的目录
# -h --help 显示帮助信息
# --config CONFIG 显式指定一个配置文件，而非使用工作目录下的config.yml
# --debug 在执行每个命令行之前，打印变量展开后的命令行
# --dry-run 正常运行，正常输出，但是不会有实际效果（不会读写本地，远端的任何文件）
```

## 可用变量

有一些配置选项中可以使用内置的变量，变量会被替换成实际的参数值。如果要使用变量，只需要在变量名前面加上一个美元符号`$`即可（注意这里的变量只是个简单的文本替换，并不是环境变量，也并不支持使用环境变量）

除了内置变量，还可以使用自定义的变量，你可以把自定义的变量写在`variables.`下面，然后在后面的`commands.`命令行中使用这些变量，这可以代替不同命令行中相同的部分，减少手写的工作量

自定义的变量支持变量嵌套，也就是说你可以在一个变量里依赖另一个变量的值

---

这是可以允许使用参数的选项的列表，后面的值表示可以使用哪些参数

```yaml
state-file: source, workdir, variables
commands._workdir: source, workdir, variables
commands.download-state: source, workdir, variables
commands.upload-state: apath, source, workdir, variables
commands.delete-file: apath, rpath, source, workdir, variables
commands.delete-dir: apath, rpath, source, workdir, variables
commands.upload-file: apath, rpath, source, workdir, variables
commands.upload-dir: apath, rpath, source, workdir, variables
```

注意：variables变量不是代表一个名叫`variables`的变量，而是表示这里可以使用`variables.`选项下定义的所有变量

| 内置变量 | 描述                               |
| -------- | ---------------------------------- |
| source   | 启动参数中source所指向的目录       |
| workdir  | 对象存储文件上传助手当前的工作目录 |
| apath    | 绝对路径                           |
| rpath    | 相对路径                           |

## 配置参考

```yaml
# 状态文件的文件名，注意不能填写子路径（支持自定义变量）
# 状态文件：保存了桶里现有文件的结构，大小，校验等信息的文件
# 状态文件是用来计算本地与桶里的文件差异的（因此对象存储助手不会去实际遍历桶里的对象）
state-file: $state

# 开启后仅文件内容发生变动的文件会直接上传，跳过删除步骤
# 关闭后会先删除，再上传
overlay-mode: true

# 开启后对比文件时，优先对比修改时间，再对比内容校验
# 关闭后每次都会对比文件内容的校验
fast-comparison: true

# 开启后会将状态文件保存到本地，后续会从本地直接读取，而不会从桶里下载
# 关闭后则每次从桶里实时获取
use-local-state: true

# 执行commands选项下的命令行时使用的线程并发数
threads: 4

# 文件过滤器，是一个正则表达式
# 不匹配的文件会被忽略，不会被上传或者删除。留空则不启用
file-filter: 

# 自定义变量（注意这只是个简单的文本替换，并不是环境变量，也并不支持使用环境变量）
# 支持变量嵌套
variables:
  state: .state.json
  cli: coscli-windows.exe
  bucket: 'cos://sdfs-1254063044'

# 用来操作桶里文件的命令行
# 如果命令行为空则不执行任何操作
commands:
  # 手动指定命令行的工作目录
  # 如果为空则沿用对象存储助手的工作目录
  _workdir: 

  # 命令行stdout编码参数，一般使用utf-8
  _encoding: utf-8

  # 下载状态文件时使用的命令行
  download-state: $cli cp $bucket/$state $state

  # 上传缓存时使用的命令行
  upload-state: $cli cp "$apath" $bucket/$state

  # 删除桶里文件时使用的命令行
  delete-file: $cli rm "$bucket/$rpath" --force

  # 删除桶里目录时使用的命令行
  delete-dir: 

  # 上传文件到桶里时使用的命令行
  upload-file: $cli sync "$apath" "$bucket/$rpath"

  # 在桶里创建目录时使用的命令行
  make-dir: 
```
