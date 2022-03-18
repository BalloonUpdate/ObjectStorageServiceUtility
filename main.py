import os
import sys
import json
import time
import argparse
import subprocess
import yaml
from file import File
from file_comparer import FileComparer2, SimpleFileObject
from functions import calculate_dir_structure, filter_not_none, filter_files, print_metadata, replace_variables, run_subprocess, with_progress
from meta import indev
from parallelly_execute import parallelly_execute

def main():
    def execute(command: str, var: dict = {}, check: bool = True):
        if command == '':
            return
        vars = { **var, **config_variables }
        command = replace_variables(command, vars)
        cwd = replace_variables(config_workdir, vars) if config_workdir != '' else None
        if arg_debug:
            print('> ' + command)
        
        if arg_dry_run:
            return

        run_subprocess(command, cwd, config_encoding, check_return_code=check)

    # 解析参数
    parser = argparse.ArgumentParser(description='file comparer')
    parser.add_argument('source-dir', type=str, help='specify source directory to upload')
    parser.add_argument('--config', type=str, default='config.yml', help='specify a other config file')
    parser.add_argument('--debug', action='store_true', help='show command line before executing')
    parser.add_argument('--dry-run', action='store_true', help='run but do not execute any commands actually')
    args = vars(parser.parse_args())

    arg_config = args['config']
    arg_source = args['source-dir'][:-1] if args['source-dir'].endswith('/') else args['source-dir']
    arg_debug = args['debug']
    arg_dry_run = args['dry_run']

    # 检查参数
    workdir = os.getcwd()
    source_dir = File(arg_source)
    config_file = File(arg_config)

    if config_file == '' or not config_file.exists or not config_file.isFile:
        raise Exception(f'配置文件 {arg_config} 找不到或者不是一个文件')

    if arg_source == '' or not source_dir.exists or not source_dir.isDirectory:
        raise Exception(f'源路径 {arg_source} 找不到或者不是一个目录')

    # 读取配置文件
    config = filter_not_none(yaml.safe_load(config_file.content))
    config_state_file = config.get('state-file', '.state.json')
    config_overlay_mode = config.get('overlay-mode', False)
    config_fast_comparison = config.get('fast-comparison', False)
    config_use_local_state = config.get('use-local-state', False)
    config_threads = config.get('threads', 1)
    config_file_filter = config.get('file-filter', '')
    config_variables = filter_not_none(config.get('variables', {}))
    config_command = filter_not_none(config.get('commands', {}))
    config_workdir = config_command.get('_workdir', '')
    config_encoding = config_command.get('_encoding', 'utf-8')
    config_download_state = config_command.get('download-state', '')
    config_upload_state = config_command.get('upload-state', '')
    config_delete_file = config_command.get('delete-file', '')
    config_delete_dir = config_command.get('delete-dir', '')
    config_upload_file = config_command.get('upload-file', '')
    config_upload_dir = config_command.get('make-dir', '')

    state_file = File(replace_variables(config_state_file, var={"source": arg_source, "workdir": workdir, **config_variables}))

    # 获取缓存
    if not config_use_local_state:
        print('获取缓存')
        execute(config_download_state, var={"source": arg_source, "workdir": workdir})
    else:
        print('加载本地缓存')

    # 加载缓存
    state = json.loads(state_file.content) if state_file.exists and state_file.isFile else []
    
    # if indev:
    #     state = []

    # 计算文件差异
    print('计算文件差异（可能需要一些时间）')
    def cmpfunc(remote: SimpleFileObject, local: File, path: str):
        return (config_fast_comparison and remote.modified == local.modified) or remote.sha1 == local.sha1

    cper = FileComparer2(source_dir, cmpfunc)
    cper.compareWithList(source_dir, state)

    # 输出差异结果
    print(f'旧文件: {len(cper.oldFiles)}, 旧目录: {len(cper.oldFolders)}, 新文件: {len(cper.newFiles)}, 新目录: {len(cper.newFolders)}')

    # 删除文件
    filter_fun = lambda e: not config_overlay_mode or e not in cper.newFiles
    def worker1(index, total, res):
        path = res
        variables = {"apath": (source_dir + path).path, "rpath": path, "source": arg_source, "workdir": workdir}
        print(f'删除文件 {index + 1}/{total} - {path}')
        execute(config_delete_file, var=variables)
    parallelly_execute(filter_files(config_file_filter, [e for e in filter(filter_fun, cper.oldFiles)]), config_threads, worker1)

    # 删除目录
    def worker2(index, total, res):
        path = res
        variables = {"apath": (source_dir + path).path, "rpath": path, "source": arg_source, "workdir": workdir}
        print(f'删除目录 {index + 1}/{total} - {path}')
        execute(config_delete_dir, var=variables)
    parallelly_execute(filter_files(config_file_filter, cper.oldFolders), config_threads, worker2)

    # 创建目录
    start_time = time.time()
    def worker3(index, total, res):
        path = res
        variables = {"apath": (source_dir + path).path, "rpath": path, "source": arg_source, "workdir": workdir}
        print(f'建立目录 {index + 1}/{total} - {path}')
        execute(config_upload_dir, var=variables)
    parallelly_execute(filter_files(config_file_filter, cper.newFolders), config_threads, worker3)

    # 上传文件
    def worker4(index, total, res):
        path = res
        variables = {"apath": (source_dir + path).path, "rpath": path, "source": arg_source, "workdir": workdir}
        print(f'上传文件 {index + 1}/{total} - {path}')
        execute(config_upload_file, var=variables)
    result = parallelly_execute(filter_files(config_file_filter, cper.newFiles), config_threads, worker4)
    if result > 0:
        spent = '{:.2f}'.format(time.time() - start_time)
        print(f'上传过程耗时 {spent}s')

    # 更新缓存
    if sum([len(cper.oldFolders), len(cper.oldFiles), len(cper.newFolders), len(cper.newFiles)]) > 0:
        print('更新缓存')
        state_file.delete()
        state_file.content = json.dumps(calculate_dir_structure(source_dir), ensure_ascii=False, indent=2)
        execute(config_upload_state, var={"apath": config_state_file, "source": arg_source, "workdir": workdir})
        print('缓存已更新')
        if not config_use_local_state:
            state_file.delete()
    else:
        print('缓存无需更新')

    print('Done')

if __name__ == "__main__":
    if not indev:
        print_metadata()
    try:
        main()
    except subprocess.CalledProcessError as e:
        print(f'\n命令执行失败。子进程返回码为: {e.returncode}\n原始命令行: {e.cmd}\n子进程输出 ==>\n{e.output}')
        sys.exit(e.returncode)
    