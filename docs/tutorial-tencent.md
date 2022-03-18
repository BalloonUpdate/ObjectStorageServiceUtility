# 使用教程（腾讯云）

1. 在[腾讯云文档中心](https://cloud.tencent.com/document/product/436/63144)下载对象存储命令行工具COSCLI，并按[腾讯云文档](https://cloud.tencent.com/document/product/436/63144#.E9.85.8D.E7.BD.AE.E5.8F.82.E6.95.B0)中的步骤配置好Secret ID和Secret Key等参数
2. 新建一个文件夹，用来存放我们的文件，名字随意（我这里就叫folder了）
3. 将对象存储命令行工具可执行文件复制到folder目录里
4. 下载**对象存储文件上传助手**的可执行文件`ossu-0.0.0.exe`到folder目录里（0.0.0请替换成实际版本号）
5. 下载**对象存储文件上传助手**的配置文件`config.tencent.yml`到folder目录里并命名为`config.yml`
6. 用文本编辑器打开配置文件`config.yml`并按下面的步骤进行配置
  + 修改`variables.cli`的值为在第1步中你所下载的命令行工具可执行文件的名称
  + 修改`variables.bucket`的值为`cos://sdfs-12566044`（`sdfs-12566044`为你要上传的桶名）
    + 如果你要上传到子目录，可以写成`cos://sdfs-12566044/subdir`的形式（末尾不要带`/`）
  + 其它选项不需要修改，保存并关闭配置文件
7. 在当前目录打开终端，使用命令`ossu-0.0.0.exe <source-dir>`来将本地`source-dir`目录下的所有内容上传到桶`cos://sdfs-12566044`下（会覆盖同名文件）。`source-dir`就是要进行上传的目录
7. 上传完成后就可以关闭终端了。建议将上传命令写到一个批处理文件`.bat / .cmd`或者一个shell脚本`.sh`中，这样就不用每次都手打指令了