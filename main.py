import json
import argparse
import subprocess
from file import File
from file_comparer import FileComparer2, SimpleFileObject

def execute(command: str, var: dict = {}, check: bool = True):
    # global commands_out
    if command != '':
        for k in var.keys():
            command = command.replace(f'${k}', var[k])
        for k in config_variables:
            command = command.replace(f'${k}', config_variables[k])
        print('> ' + command)
        subprocess.run(command, check=check, shell=True, capture_output=True)
        # commands_out += command + '\n'

def dir_hash(dir: File):
    structure = []
    for f in dir:
        if f.isFile:
            structure.append({
                'name': f.name,
                'length': f.length,
                'hash': f.sha1,
                'modified': f.modifiedTime
            })
        if f.isDirectory:
            structure.append({
                'name': f.name,
                'tree': dir_hash(f)
            })
    return structure

parser = argparse.ArgumentParser(description='file comparer')
parser.add_argument('--config', type=str, default='config.json')
parser.add_argument('--source', type=str, required=True)
args = parser.parse_args()

arg_config = args.config
arg_source = args.source

source_dir = File(arg_source)
config_file = File(arg_config)

if config_file == '' or not config_file.exists or not config_file.isFile:
    raise Exception(f'配置文件 {arg_config} 找不到或者不是一个文件')

if arg_source == '' or not source_dir.exists or not source_dir.isDirectory:
    raise Exception(f'源路径 {arg_source} 找不到或者不是一个目录')

config = json.loads(config_file.content)
config_cache_file = config['cache-file']
config_variables = config['variables']
config_download_cache = config['command']['download-cache']
config_upload_cache = config['command']['upload-cache']
config_delete_file = config['command']['delete-file']
config_delete_dir = config['command']['delete-dir']
config_upload_file = config['command']['upload-file']
config_upload_dir = config['command']['upload-dir']

cache_file = File(config_cache_file)

# commands_out = ''

if config_cache_file == '':
    raise Exception(f'配置文件中的 cache-file 不能为空')

# 获取缓存
print('获取缓存')
execute(config_download_cache, check=False)

# 加载缓存
cache = json.loads(cache_file.content) if cache_file.exists and cache_file.isFile else []
cache_file.delete()

# 计算文件差异
print('计算文件差异')
comparer = FileComparer2(source_dir, lambda remote, local, path: remote.sha1 == File(local).sha1)
comparer.compareWithList(source_dir, cache)

# 输出差异结果
print(f'旧文件: {len(comparer.oldFiles)}')
print(f'旧目录: {len(comparer.oldFolders)}')
print(f'新文件: {len(comparer.newFiles)}')
print(f'新目录: {len(comparer.newFolders)}')

# 删除旧文件
print('删除旧文件')
for f in comparer.oldFiles:
    path = (source_dir + f).relPath()
    execute(config_delete_file, var={"path": path})

# 删除旧目录
print('删除旧目录')
for f in comparer.oldFolders:
    path = (source_dir + f).relPath()
    execute(config_delete_dir, var={"path": path})

# 建立新目录
print('建立新目录')
for f in comparer.newFolders:
    path = (source_dir + f).relPath()
    execute(config_upload_dir, var={"path": path})

# 上传新文件
print('上传新文件')
for f in comparer.newFiles:
    path = (source_dir + f).relPath()
    execute(config_upload_file, var={"path": path})

# 更新缓存
if sum([len(comparer.oldFolders), len(comparer.oldFiles), len(comparer.newFolders), len(comparer.newFiles)]) > 0:
    print('更新缓存')
    cache_file.delete()
    cache_file.content = json.dumps(dir_hash(source_dir), ensure_ascii=False, indent=4)
    execute(config_upload_cache, var={"path": config_cache_file})
    cache_file.delete()
else:
    print('缓存无需更新')

# with open(File('out.bat').path, mode='w+', encoding='gb2312') as f:
    # f.write(f'@echo off\n{commands_out}\npause')

print('Done')