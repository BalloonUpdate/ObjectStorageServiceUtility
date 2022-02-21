import os
import sys
import re
import json
import argparse
import subprocess
from file import File
from file_comparer import FileComparer2, SimpleFileObject
from meta import commit, compile_time, version, indev

def replace_variables(text: str, var: dict = {}):
    for i in range(0, 1000):
        replaced = False
        for k in var.keys():
            new = text.replace(f'${k}', var[k])
            if new != text:
                replaced = True
            text = new
        if not replaced:
            break
    return text

def execute(command: str, var: dict = {}, check: bool = True):
    if command == '':
        return
    vars = { **var, **config_variables }
    command = replace_variables(command, vars)
    cwd = replace_variables(config_command_workdir, vars) if config_command_workdir != '' else None
    if arg_debug:
        print('> ' + command)
    if config_test_mode:
        return
    subprocess.run(command, check=check, shell=True, cwd=cwd, capture_output=not arg_detail)

def dir_hash(dir: File):
    structure = []
    for f in dir:
        if f.isFile:
            structure.append({
                'name': f.name,
                'length': f.length,
                'hash': f.sha1,
                'modified': f.modified
            })
        if f.isDirectory:
            structure.append({
                'name': f.name,
                'tree': dir_hash(f)
            })
    return structure

def filter_and_progressify(ls: list) -> tuple: 
    new_ls = [e for e in filter(lambda e: config_pattern == '' or re.fullmatch(config_pattern, e), ls)]
    total = len(new_ls)
    result = []
    index = 0
    for el in new_ls:
        result += [(index, total, el)]
        index += 1
    return result

# 开始运行（输出元数据）
if not indev:
    commit_sha = commit[:8] if len(commit) > 16 else commit
    print('应用版本: ' + version + (f' ({commit_sha})' if len(commit) > 0 else ''))
    print('编译时间: ' + compile_time)
    print()

parser = argparse.ArgumentParser(description='file comparer')
parser.add_argument('--config', type=str, default='config.json', help='specify a other config.json')
parser.add_argument('--source', type=str, required=True, help='specify source directory to upload')
parser.add_argument('--detail', action='store_true', help='show the detail of command execution')
parser.add_argument('--debug', action='store_true', help='show command text before execute')
args = parser.parse_args()

arg_config = args.config
arg_source = args.source[:-1] if args.source.endswith('/') else args.source
arg_detail = args.detail
arg_debug = args.debug

workdir = os.getcwd()
source_dir = File(arg_source)
config_file = File(arg_config)

if config_file == '' or not config_file.exists or not config_file.isFile:
    raise Exception(f'配置文件 {arg_config} 找不到或者不是一个文件')

if arg_source == '' or not source_dir.exists or not source_dir.isDirectory:
    raise Exception(f'源路径 {arg_source} 找不到或者不是一个目录')

config = json.loads(config_file.content)
config_cache_file = config['cache-file']
config_overlay_mode = config['overlay-mode']
config_command_workdir = config['command-workdir']
config_pattern = config['pattern']
config_test_mode = config['test-mode']
config_check_modified = config['check-modified-time']
config_variables = config['variables']
config_download_cache = config['command']['download-cache']
config_upload_cache = config['command']['upload-cache']
config_delete_file = config['command']['delete-file']
config_delete_dir = config['command']['delete-dir']
config_upload_file = config['command']['upload-file']
config_upload_dir = config['command']['upload-dir']

cache_file = File(replace_variables(config_cache_file, var={"source": arg_source, "workdir": workdir}))

if config_cache_file == '':
    raise Exception(f'配置文件中的 cache-file 不能为空')

# 获取缓存
print('获取缓存')
execute(config_download_cache, var={"source": arg_source, "workdir": workdir}, check=False)

# 加载缓存
cache = json.loads(cache_file.content) if cache_file.exists and cache_file.isFile else []
cache_file.delete()

# 计算文件差异
print('计算文件差异')
def cmpfunc(remote: SimpleFileObject, local: File, path: str):
    return (config_check_modified and remote.modified == local.modified) or remote.sha1 == local.sha1

cper = FileComparer2(source_dir, cmpfunc)
cper.compareWithList(source_dir, cache)

# 输出差异结果
print(f'旧文件: {len(cper.oldFiles)}, 旧目录: {len(cper.oldFolders)}, 新文件: {len(cper.newFiles)}, 新目录: {len(cper.newFolders)}')

filter_fun = lambda e: not config_overlay_mode or e not in cper.newFiles
for (index, total, f) in filter_and_progressify([e for e in filter(filter_fun, cper.oldFiles)]):
    print(f'删除文件 {index + 1}/{total} - {f}')
    execute(config_delete_file, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

for (index, total, f) in filter_and_progressify(cper.oldFolders):
    print(f'删除目录 {index + 1}/{total} - {f}')
    execute(config_delete_dir, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

for (index, total, f) in filter_and_progressify(cper.newFolders):
    print(f'建立目录 {index + 1}/{total} - {f}')
    execute(config_upload_dir, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

for (index, total, f) in filter_and_progressify(cper.newFiles):
    print(f'上传文件 {index + 1}/{total} - {f}')
    execute(config_upload_file, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

# 更新缓存
if sum([len(cper.oldFolders), len(cper.oldFiles), len(cper.newFolders), len(cper.newFiles)]) > 0:
    print('更新缓存')
    cache_file.delete()
    cache_file.content = json.dumps(dir_hash(source_dir), ensure_ascii=False, indent=4)
    execute(config_upload_cache, var={"apath": config_cache_file, "source": arg_source, "workdir": workdir})
    cache_file.delete()
    print('缓存已更新')
else:
    print('缓存无需更新')

print('Done')