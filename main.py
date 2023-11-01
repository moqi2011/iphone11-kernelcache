import json
import os.path
import shutil
import subprocess
from datetime import datetime

import requests
import argparse
import pathlib

DEVICE_IDENTIFIER = "iPhone12,1"
GITHUB_TOKEN = open("GITHUB_TOKEN", "r").read().strip()
OWNER = "moqi2011"
REPO = "iphone11-kernelcache"


def get_firmwares():
    res = requests.get(url=f"https://api.ipsw.me/v4/device/{DEVICE_IDENTIFIER}?type=ipsw")
    firmwares = res.json().get("firmwares")
    # orderby releasedate
    firmwares.sort(key=lambda o: datetime.strptime(o.get("releasedate"), "%Y-%m-%dT%H:%M:%SZ"))
    return firmwares


def gen_download_cmd(_):
    firmwares = get_firmwares()
    cmds = []
    for firmware in firmwares:
        version = firmware.get("version")
        url = firmware.get("url")
        if os.path.exists(f"kernelcache/{version}/kernelcache.release.{DEVICE_IDENTIFIER}"):
            continue
        cmd = f'ipsw extract --kernel --remote {url} --output kernelcache/{version}'
        cmds.append(cmd)
    print("\n".join(cmds))


def mock():
    firmwares = get_firmwares()
    for f in firmwares:
        dir_ = pathlib.Path(f"./kernelcache/{f.get('version')}/{f.get('buildid')}__{f.get('identifier')}")
        dir_.mkdir(parents=True, exist_ok=True)
        open(dir_.joinpath(f"kernelcache.release.{DEVICE_IDENTIFIER}"), "w")
        open(dir_.joinpath(f"kernelcache.research.{DEVICE_IDENTIFIER}"), "w")


def rename_and_clean(_):
    del_dirs = set()
    for root, dirs, files in os.walk(".", topdown=False):
        for name in files:
            if name.startswith("kernelcache.re") and name.endswith(DEVICE_IDENTIFIER):
                path1 = os.path.join(root, name)
                path0 = path1.split("/")
                # ./kernelcache/13.0/17A577__iPhone12,1/kernelcache.release.iPhone12,1
                if DEVICE_IDENTIFIER not in path0[-2]:
                    #
                    continue
                del_dirs.add("/".join(path0[:-1]))
                del path0[-2]
                path2 = "/".join(path0)
                os.rename(path1, path2)
    for del_dir in del_dirs:
        shutil.rmtree(del_dir, ignore_errors=True)


def gen_upload_cmd(_):
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {GITHUB_TOKEN}',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    # https://docs.github.com/en/rest/releases/releases?apiVersion=2022-11-28#get-the-latest-release
    response = requests.get(f'https://api.github.com/repos/{OWNER}/{REPO}/releases/latest', headers=headers)
    jo = response.json()
    upload_url = jo.get("upload_url")
    if upload_url.endswith("{?name,label}"):
        upload_url = upload_url[:-len("{?name,label}")]

    response = requests.get(jo.get("assets_url"), headers=headers)
    exists_assets_names = []
    for assets in response.json():
        exists_assets_names.append(assets.get("name"))
    cmds = []
    for root, dirs, files in os.walk(".", topdown=False):
        for name in files:
            if name.startswith("kernelcache.re") and name.endswith(DEVICE_IDENTIFIER):
                path1 = os.path.join(root, name)
                path0 = path1.split("/")
                assets_name = "_".join(path0[-2:])
                # "iPhone12,1" to "iPhone12.1"
                assets_name = assets_name.replace(",", ".")
                if assets_name in exists_assets_names:
                    continue
                # https://docs.github.com/en/rest/releases/assets?apiVersion=2022-11-28#upload-a-release-asset
                cmd = f"""\
curl -L \
-X POST \
-H "Accept: application/vnd.github+json" \
-H "Authorization: Bearer {GITHUB_TOKEN}" \
-H "X-GitHub-Api-Version: 2022-11-28" \
-H "Content-Type: application/octet-stream" \
"{upload_url}?name={assets_name}" \
--data-binary "@{path1}" """
                cmds.append(cmd)
    print("\n".join(cmds))


def ver_to_int(ver: str):
    def fill_zero(s, n):
        return "000000"[0:n - len(s)] + s

    ver_s0 = ver.split(".")
    ver_s1 = ["00", "00", "00"]
    for i in range(len(ver_s0)):
        ver_s1[i] = fill_zero(ver_s0[i], 2)

    return int("".join(ver_s1))


def get_kernel_version():
    version_map = {}
    for root, dirs, files in os.walk(".", topdown=False):
        for name in files:
            if name.startswith("kernelcache.release") and name.endswith(DEVICE_IDENTIFIER):
                path1 = os.path.join(root, name)
                path0 = path1.split("/")
                system_version = path0[-2]
                kernel_version = subprocess.check_output(["ipsw", "kernel", "version", path1])
                version_map[system_version] = kernel_version.decode().split("\n")[0].strip()
    return version_map


def gen_kernel_version_table(_):
    version_map = get_kernel_version()
    version_list = list(version_map.keys())
    version_list.sort(key=ver_to_int)
    table_rows = []
    for system_version in version_list:
        kernel_version = version_map[system_version]
        row = f"| {system_version} | {kernel_version} |"
        table_rows.append(row)

    open("kernel_version_table", "w").write("\n".join(table_rows))


if __name__ == '__main__':
    # https://docs.python.org/zh-cn/3/library/argparse.html
    parser = argparse.ArgumentParser(description='')

    subparsers = parser.add_subparsers(required=True)

    parser_subparsers = subparsers.add_parser('gen_download_cmd')
    parser_subparsers.set_defaults(func=gen_download_cmd)

    parser_subparsers = subparsers.add_parser('rename_and_clean')
    parser_subparsers.set_defaults(func=rename_and_clean)

    parser_subparsers = subparsers.add_parser('gen_upload_cmd')
    parser_subparsers.set_defaults(func=gen_upload_cmd)

    parser_subparsers = subparsers.add_parser('gen_kernel_version_table')
    parser_subparsers.set_defaults(func=gen_kernel_version_table)

    args = parser.parse_args()
    args.func(args)
