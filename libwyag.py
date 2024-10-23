import argparse, collections, configparser, hashlib, os, re, sys, zlib
#import grp, pwd
from datetime import datetime
from fnmatch import fnmatch
from math import ceil
#gets argparse important, other imports like print working directory and os and system calls
#zlib for compression and decompression
#collections adds extra commands for our data types like strings and dicts


#used to parse(enter data) through gits, git COMMAND where command is any valid git command 
argparser = argparse.ArgumentParser(description = "Default Parser")
argsubparser = argparser.add_subparsers(title= "Commands", dest = "command")
argsubparser.required = True

#all git commands parsed through our argparser
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "add"          : cmd_add(args)
        case "cat-file"     : cmd_cat_file(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
        case "commit"       : cmd_commit(args)
        case "hash-object"  : cmd_hash_object(args)
        case "init"         : cmd_init(args)
        case "log"          : cmd_log(args)
        case "ls-files"     : cmd_ls_files(args)
        case "ls-tree"      : cmd_ls_tree(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "rm"           : cmd_rm(args)
        case "show-ref"     : cmd_show_ref(args)
        case "status"       : cmd_status(args)
        case "tag"          : cmd_tag(args)
        case _              : print("Error: Command Input.")

#the git repo(vault)
class GitRepo (object):

    worktree = None
    git_dir = None
    config = None

    def __init__(self, path, force = False):
        self.worktree = path
        self.git_dir = os.path.join(path, ".git")

        #if command is forced or path is 
        if not (force or os.path.isdir(self.get_dir)):
            raise Exception("Not a Git Repo %s" % path)

        #reads .git/config configuration file
        self.config = configparser.ConfigParser()
        cf = repo_file(self, "config")


        #if config file and path to config exists
        if cf and os.path.exists(cf):
            self.config.read([cf])
        elif not force:
            raise Exception("Config File Missing")

        if not force:
            vers = int(self.config.ger("core", "repositoryformatversion"))
            if vers != 0:
                raise Exception("Unsupported repositoryformatversion %s" % vers)


#path building function
def repo_path(repo, *path):
    return os.path.join(repo.gitdir, *path)

def repo_file(repo, *path, mkdir = False):
    #same as repo path but can create path if absent

    #*path makes it so path is a variadic (super variable) able to act as a list of its valid typing
    if repo_dir(repo, *path[:-1], mkdir = mkdir):
        return repo_path(repo, *path)

def repo_dir(repo, *path, mkdir = False):

    path = repo_path(repo, *path)

    if os.path.exists(path):
        if (os.path.isdir(path)):
            return path
        else:
            raise Exception("Not a directory %s" % path)


    #activates creating path 
    if mkdir:
        os.makedirs(path)
        return path
    else:
        return None

#creates repo at path
def repo_create(path):
    repo = GitRepo(path, True)

    #makes repo if empty and is in directory
    if os.path.exists(repo.worktree):
        if not os.path.isdir(repo.worktree):
            raise Exception("%s is Not a Directory" % path)
        if os.path.exists(repo.gitdir) and os.listdir(repo.gitdir):
            raise Exception("%s is Not Empty" % path)
    else:
        os.makedirs(repo.worktree)

    #assert validity
    assert repo_dir(repo, "branches", mkdir = True)
    assert repo_dir(repo, "objects", mkdir = True)
    assert repo_dir(repo, "refs", "tags", mkdir = True)
    assert repo_dir(repo, "refs", "heads", mkdir = True)

    #.git/description
    with open(repo_file(repo, "description"), "w") as writer:
        writer.write("Unnamed Repo. Edit this file 'description' to name this repo.\n")
        
    #.git/HEAD
    with open(repo_file(repo, "HEAD"), "w") as writer:
        writer.write("ref: refs/heads/master\n")

    #writes config file
    with open(repo_file(repo, "config"), "w") as writer:
        config = repo_default_config()
        config.write(writer)

    return repo

#default config options
def repo_default_config():
    ret = configparser.ConfigParser()

    ret.add_section("core")
    ret.set("core", "repositoryformatversion", "0")
    ret.set("core", "filemode", "false")
    ret.set("core", "bare", "false")

    return ret

def repo_find(path = ".", required = True):
    path = os.path.realpath(path)

    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepo(path)

    #recursive finding
    parent = os.path.realpath(os.path.join(path, ".."))

    if (parent == path):

        if reqired:
            raise Exception("No Git Repo")
        else:
            return None


    return repo_find(parent, required)

argsp = argsubparser.add_parser("init", help = "Initialize a new, empty repository.")
argsp.add_argument("path", metavar = "directory", nargs = "?", default = ".", help = "Where to create the repository.")

def cmd_init(args):
    repo_create(args.path)

