# 软件原理

软件的原理，或者说工作流程分四个步骤：1. 下载状态文件 2. 然后计算本地和远程的文件差异 3. 更新差异文件 4. 上传状态文件

首先软件启动之后，会从`config.yml`读取配置信息，如果指定了`--config <file>`选项，则会从指定路径读取

然后第一步会更新状态文件，状态文件保存了桶里现有文件的结构，大小，校验等信息。软件会以状态文件的信息为准，而不会去遍历桶里的对象

+ 如果配置文件中开启了`use-local-state`选项，则会从当前工作目录读取`state-file`选项所指定的文件名作为状态文件，不会再从桶里去下载状态文件。这个文件默认名为`.state.json`
+ 如果配置文件中没有开启`use-local-state`选项，则会调用`commands.download-state`命令行，使用对象存储CLI工具来下载状态文件，不会再读取本地的状态文件

接着第二步开始计算远端文件和本地文件的差异，当发现两个同路径文件名时，会尝试对比校验

+ 如果此时开启了`fast-comparison`选项，则会先对比文件修改时间，如果一致，则被视为文件内容也是一致的。如果时间不一致，则计算文件的实际校验值（sha1算法），如果不一致，则添加到差异列表中
+ 如果此时没有开启`fast-comparison`选项，则直接计算文件校验值

最后第三步是更新远端文件（桶里的文件），刚刚计算好的差异信息包含以下四个列表：

1. 要删除的文件
2. 要删除的目录
3. 要创建的目录
4. 要上传的文件

首先使用`file-filter`选项依次过滤四个列表，`file-filter`是个正则表达式，如果未能匹配，则会从以上列表里移除对应的文件（相当于忽略文件，不做任何处理）

留下来的文件分两部分，一部分是新文件，一部分是旧文件（这里仅包括文件，不包括目录）

+ 如果此时开启了`overlay-mode`选项，同时存在于新文件列表和旧文件列表中的文件，会从旧文件列表里删除。说人话就是跳过删除步骤，直接上传新的文件以覆盖掉旧文件内容（这样执行效率更高）
+ 如果没有开启了`overlay-mode`选项，则先删除，再上传新

然后开始真正的同步文件过程：

+ 要删除的旧文件会调用`command.delete-file`命令行完成
+ 要删除的旧目录会调用`command.delete-dir`命令行完成
+ 要创建的新目录会调用`command.make-dir`命令行完成
+ 要上传的新文件会调用`command.upload-file`命令行完成

这个过程中，每个步骤都可以通过`threads`选项来进行多线程操作

最后，会调用`command.upload-state`命令行，来上传更新好的状态文件（即使打开了`use-local-state`选项也是一样）

---

在调用每一个`command.`节点下的命令行时，如果`commands._workdir`选项不为空，则会使用指定的工作目录调用命令行。如果为空则沿用**对象存储文件上传助手**的工作目录。每个命令行输出的stdout会使用`commands._encoding`选项进行解码字符串，这个选项一般设置为`utf-8`就好