import os
import sys
import re
import json
import time
import argparse
import subprocess
import yaml
from multiprocessing.pool import ThreadPool
from queue import Queue
from file import File
from file_comparer import FileComparer2, SimpleFileObject
from functions import calculate_dir_structure, filter_and_progressify, filter_not_none, print_metadata, replace_variables, run_subprocess
from meta import indev

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
    config_cache_file = config.get('cache-file', '.cache.json')
    config_overlay_mode = config.get('overlay-mode', False)
    config_fast_comparison = config.get('fast-comparison', False)
    config_use_local_cache = config.get('use-local-cache', False)
    config_threads = config.get('threads', 1)
    config_file_filter = config.get('file-filter', '')
    config_variables = filter_not_none(config.get('variables', {}))
    config_command = filter_not_none(config.get('commands', {}))
    config_workdir = config_command.get('_workdir', '')
    config_encoding = config_command.get('_encoding', 'utf-8')
    config_download_cache = config_command.get('download-cache', '')
    config_upload_cache = config_command.get('upload-cache', '')
    config_delete_file = config_command.get('delete-file', '')
    config_delete_dir = config_command.get('delete-dir', '')
    config_upload_file = config_command.get('upload-file', '')
    config_upload_dir = config_command.get('upload-dir', '')

    cache_file = File(replace_variables(config_cache_file, var={"source": arg_source, "workdir": workdir, **config_variables}))

    # 获取缓存
    if not config_use_local_cache:
        print('获取缓存')
        execute(config_download_cache, var={"source": arg_source, "workdir": workdir})
    else:
        print('加载本地缓存')

    # 加载缓存
    cache = json.loads(cache_file.content) if cache_file.exists and cache_file.isFile else []
    
    # if indev:
    #     cache = []

    # 计算文件差异
    print('计算文件差异（可能需要一些时间）')
    def cmpfunc(remote: SimpleFileObject, local: File, path: str):
        return (config_fast_comparison and remote.modified == local.modified) or remote.sha1 == local.sha1

    cper = FileComparer2(source_dir, cmpfunc)
    cper.compareWithList(source_dir, cache)

    # 输出差异结果
    print(f'旧文件: {len(cper.oldFiles)}, 旧目录: {len(cper.oldFolders)}, 新文件: {len(cper.newFiles)}, 新目录: {len(cper.newFolders)}')

    filter_fun = lambda e: not config_overlay_mode or e not in cper.newFiles
    for (index, total, f) in filter_and_progressify(config_file_filter, [e for e in filter(filter_fun, cper.oldFiles)]):
        print(f'删除文件 {index + 1}/{total} - {f}')
        execute(config_delete_file, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

    for (index, total, f) in filter_and_progressify(config_file_filter, cper.oldFolders):
        print(f'删除目录 {index + 1}/{total} - {f}')
        execute(config_delete_dir, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

    for (index, total, f) in filter_and_progressify(config_file_filter, cper.newFolders):
        print(f'建立目录 {index + 1}/{total} - {f}')
        execute(config_upload_dir, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

    # 准备任务
    task_pool = Queue(1000000000)
    thread_pool = ThreadPool(config_threads)

    for (index, total, f) in filter_and_progressify(config_file_filter, cper.newFiles):
        task_pool.put([
            total,
            f,
            config_upload_file, 
            {"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir}
        ])
        # execute(config_upload_file, var={"apath": (source_dir + f).path, "rpath": f, "source": arg_source, "workdir": workdir})

    finishes = 0
    def worker():
        nonlocal finishes
        while not task_pool.empty():
            task = task_pool.get(timeout=1)
            total, path, command_line, variables = task
            index = finishes
            finishes += 1
            print(f'上传文件 {index + 1}/{total} - {path}')
            execute(command_line, var=variables)

    # 提交任务
    start_time = time.time()
    ex = None
    def onError(e):
        thread_pool.terminate()
        nonlocal ex
        ex = e
    for i in range(0, config_threads):
        thread_pool.apply_async(worker, error_callback=onError)

    thread_pool.close()
    thread_pool.join()

    if ex is not None:
        raise ex

    if finishes > 0:
        spent = '{:.2f}'.format(time.time() - start_time)
        print(f'上传过程耗时 {spent}s')

    # 更新缓存
    if sum([len(cper.oldFolders), len(cper.oldFiles), len(cper.newFolders), len(cper.newFiles)]) > 0:
        print('更新缓存')
        cache_file.delete()
        cache_file.content = json.dumps(calculate_dir_structure(source_dir), ensure_ascii=False, indent=2)
        execute(config_upload_cache, var={"apath": config_cache_file, "source": arg_source, "workdir": workdir})
        print('缓存已更新')
        if not config_use_local_cache:
            cache_file.delete()
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
    