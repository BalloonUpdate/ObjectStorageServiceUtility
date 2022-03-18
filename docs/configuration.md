# 配置参考

```yaml
# 状态文件的文件名，注意不能填写子路径（支持自定义变量）
# 状态文件：保存了桶里现有文件的结构，大小，校验等信息的文件
# 状态文件是用来计算本地与桶里的文件差异的（因此对象存储文件上传助手不会去实际遍历桶里的对象）
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
  # 如果为空则沿用对象存储文件上传助手的工作目录
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