
import re
import subprocess

from file import File
from meta import commit, compile_time, version


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

def run_subprocess(command: str, cwd: str, check_return_code: bool) -> str:
    outputs = ''

    with subprocess.Popen(args=command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, cwd=cwd) as process:
        with process.stdout as stdout:
            while True:
                data = stdout.read()
                if len(data) == 0:
                    break
                outputs += data.decode()
        
        retcode = process.poll()

        if retcode is None:
            process.kill()
            retcode = process.poll()

        if check_return_code and retcode:
            raise subprocess.CalledProcessError(retcode, process.args, output=outputs, stderr=None)
    
    return outputs

def calculate_dir_structure(dir: File):
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
                'tree': calculate_dir_structure(f)
            })
    return structure

def filter_and_progressify(pattern: str, ls: list) -> tuple: 
    new_ls = [e for e in filter(lambda e: pattern == '' or re.fullmatch(pattern, e), ls)]
    total = len(new_ls)
    result = []
    index = 0
    for el in new_ls:
        result += [(index, total, el)]
        index += 1
    return result

def print_metadata():
    commit_sha = commit[:8] if len(commit) > 16 else commit
    commit_sha_in_short = commit_sha if len(commit) > 0 else 'dev'
    print(f'AppVersion: {version} ({commit_sha_in_short}), CompileTime: {compile_time}')

def filter_not_none(obj: dict):
    return { k: v for k, v in obj.items() if v is not None }