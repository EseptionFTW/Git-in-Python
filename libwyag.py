import argparse, collections, configparser, hashlib, os, re, sys, zlib
#import grp, pwd
from datetime import datetime
from fnmatch import fnmatch
from math import ceil
#gets argparse important, other imports like print working directory and os and system calls
#zlib for compression and decompression
#collections adds extra commands for our data types like strings and dicts


#used to parse(enter data) through gits, git COMMAND where command is any valid git command 
argparser = argparse.ArgumentParser(description = "Python Git Clone - Default Parser")
argsubparser = argparser.add_subparsers(title= "Commands", dest = "command")
argsubparser.required = True

#all git commands parsed through our argparser
def main(argv=sys.argv[1:]):
    args = argparser.parse_args(argv)
    match args.command:
        case "init"         : cmd_init(args)
        case "cat-file"     : cmd_cat_file(args)
        case "hash-object"  : cmd_hash_object(args)
        case "log"          : cmd_log(args)
        case "commit"       : cmd_commit(args)
        case "add"          : cmd_add(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "checkout"     : cmd_checkout(args)
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
    gitdir = None
    config = None

    def __init__(self, path, force = False):
        self.worktree = path
        self.gitdir = os.path.join(path, ".git")

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

    #assert validity, creates folders
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
    print(path)
    if os.path.isdir(os.path.join(path, ".git")):
        return GitRepo(path)

    #recursive finding
    parent = os.path.realpath(os.path.join(path, ".."))

    if (parent == path):

        if required:
            raise Exception("No Git Repo")
        else:
            return None

    return repo_find(parent, required)

#SUBPARSER INIT
argsp = argsubparser.add_parser("init", help = "Initialize a new, empty repository.")
argsp.add_argument("path", 
                metavar = "directory", 
                nargs = "?", 
                default = ".", 
                help = "Where to create the repository.")

def cmd_init(args):
    repo_create(args.path)

#serialization and de-s are just adding and taking data
#who cares how sha works it just turns things into numbers and back again using bytes and stuff
#0x00 null 0x20 20 bytes ect, unidrectional encoding to make sure 

#the files that self update their own path
class GitObject (object):

    def __init__(self, data = None):
        if data != None:
            self.deserialize(data)
        else:
            self.init()
    
    #is implimented by sublassess always
    def serialize(self, repo):
        raise Exception ("Error Serialization Unimplimented")
    def deserialize(self, data):
        raise Exception ("Error Deserialization Unimplimented")
    
    #default just passes
    def init(self):
        pass

#fmt = format
def object_read(repo, sha):

    path = repo_find(repo, "objects", sha[0:2], sha[2:1])

    if not os.path.isfile(path):
        return None
    
    with open(path, "rb") as writer:
        raw = zlib.decompress(writer.read)

        #reads object type
        x = raw.find(b' ')
        fmt = raw[0:x]

        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed Object {0}: bad length".format(sha))
        
        #constructor
        match fmt:
            case b'commit' : c=GitCommit
            case b'tree'  : c=GitTree
            case b'tag'   : c=GitTag
            case b'blob'  : c=GitBlob
            case _:
                raise Exception("Unknown type {0} for object {1}".format(fmt.decode("ascii"), sha))
            
        #call constructor and return object
        return c(raw[y+1:])


def object_writer(obj, repo = None):

    data = obj.serialize()

    result = obj.fmt + b' ' + str(len(data)).encode() + b'\x00' + data

    sha = hashlib.sha1(result).hexdigest()

    if repo:

        #derive path
        path = repo_file(repo, "objects", sha[0:2], sha[2:], mkdir = True)

        if not os.path.exists(path):
            with open(path, 'wb') as writer:
                #compress and write
                writer.write(zlib.compress(result))
    
    return sha

#finds object name
def object_find(repo, name, fmt = None, follow = True):
    return name
#hi
#hi

#instance object git object match constructer super
#blob = contents of a fuke
class GitBlob(GitObject):
    fmt = b'blob'

    def serialize(self):
        return self.blobdata
    
    def deserialize(self, data):
        self.blobdata = data

#SUBPARSER CAT-FILE (cat-file type object)
argsp = argsubparser.add_parser("cat-file", help= "Provides contents of repository objects")
argsp.add_argument("type",
                   metavar= "type",
                   choices= ["blob", "commit", "tag", "tree"],
                   help= "Specify Type")
argsp.add_argument("object",
                   metavar= "object",
                   help= "The Object To Display")

#finds file and displays contents
def cmd_cat_file(args):
    repo = repo_find()
    cat_file(repo, args.object, fmt = args.type.encode())

def cat_file(repo, obj, fmt = None):
    obj = object_read(repo, object_find(repo, obj, fmt = fmt))
    sys.stdout.buffer.write(obj.serialize())

#SUBPARSER HASH-OBJECT (hash-object [-w what is written] [-t the type] file)
argsp = argsubparser.add_parser("hash-object", help= "Compute Object ID, Optionally Creats A Blob From File")
#-t type
argsp.add_argument("-t",
                   metavar= "type",
                   dest= "type",
                   choices= ["blob", "commit", "tag", "tree"],
                   default= "blob",
                   help= "Specify Type")
#-w write
argsp.add_argument("-w",
                   dest= "write",
                   action= "store_true",
                   help= "Writes The Object Into Database")
argsp.add_argument("path",
                   help= "Read Object Frim <file>")

def cmd_hash_object(args):
    if args.write:
        repo = repo_find()
    else:
        repo = None
    
    with open(args.path, 'rb') as fdir:
        sha = object_hash(fdir, args.type.encode(), repo)
        print(sha)

#actually pases data 
def object_hash(fd, fmt, repo = None):

    data = fd.read()

    match fmt:
        case b'commit' : c=GitCommit(data)
        case b'tree'   : c=GitTree(data)
        case b'tag'    : c=GitTag(data)
        case b'blob'   : c=GitBlob(data)
        case _:
            raise Exception("Unknow Type %s!" % fmt)
    
    return object_writer(obj, repo)

#these are lose objects
#no packfiles implimented .git/objects/pack
#bigger but more complex object bundles

#commits are big when uncompressed so we compress them

#commit format parser
#KEY-VALUE-LIST-MESSAGE
def kvlm_parse(raw, start = 0, dict= None):
    
    #make sure order stays cosistent very important since location is (basically) the same as object value
    if not dict:
        dict = collections.OrderedDict()
    
    #recursive function reading key/value pair

    #search for space and new line
    space = raw.find(b' ', start)
    nline = raw.find(b'\n', start)

    #base case
    #if new line or no space then assume blank line
    #if blank line rest of data is message
    #store in dict as none with key then return
    if (space < 0) or (nline < space):
        assert nline == start
        dict[None] = raw[start+1:]
        return dict
    
    #recursive
    key = raw[start:space]

    #finds end of value
    #loops until finds \n not followed by a space
    end = start
    while True:
        end = raw.find(b'\n', end+1)
        if raw[end+1] != ord(' '): break
    
    value = raw[space+1:end].replace(b'\n', b'\n')

    #dont override existing data
    if key in dict:
        if type(dict[key]) == list:
            dict[key].append(value)
        else:
            dict[key] = [ dict[key], value ]
    else:
        dict[key] = value
    
    return kvlm_parse(raw, start=end+1, dict=dict)

def kvlm_serialize(kvlm):
    
    ret = b''

    #output fields
    for k in kvlm.keys():
        #skip message
        if k == None: continue
        val = kvlm[k]

        #become list
        if type(val) != list:
            val = [ val ]
        
        for v in val:
            ret += k + b' ' + (v.replace(b'\n', b'\n')) + b'\n'
        
        #append message
        ret += b'\n' + kvlm[None] + b'\n'

    return ret

class GitCommit(GitObject):
    fmt = b'commit'

    def deserialize(self, data):
        self.kvlm = kvlm_parse(data)
    
    def serialize(self):
        return kvlm_serialize(self.kvlm)
    
    def init(self):
        self.kvlm = dict()

#simple log command using GraphViz in dot to make a graph structre of commits, paste raw data into external website to see
#https://dreampuf.github.io/GraphvizOnline
argsp = argsubparser.add_parser("log", help= "Displays the history of a given commit.")
argsp.add_argument("commit",
                   default= "HEAD",
                   nargs= "?",
                   help= "Commit to start at.")

def cmd_log(args):
    repo = repo_find()

    print("digraph wyaglog{")
    print(" node[shape=rect]")
    log_graphviz(repo, object_find(repo, args.commit), set())
    print("}")

def log_graphviz(repo, sha, seen):

    if sha in seen:
        return
    seen.add(sha)

    commit = object_read(repo, sha)
    short_hash = sha[0:8]
    message = commit.kvlm[None].decode("utf8").strip()
    message = message.replace("\\", "\\\\")
    message = message.replace("\"", "\\\"")

    #keep only the first line
    if "\n" in message:
        message = message[:message.index("\n")]
    
    print("  c_{0} [label=\"{1}: {2}\"]".format(sha, sha[0:7], message))
    assert commit.fmt == b'commit'

    #base case for initial commit graph
    if b'parent' in commit.kvlm.keys():
        return
    
    #graph traversal looking at all seen nodes of commit and logging them
    parents = commit.kvlm[b'parent']

    if type(parents) != list:
        parents = [ parents ]
    
    for p in parents:
        p = p.decode("ascii")
        print(" c_{0} -> c_{1};".format(sha, p))
        log_graphviz(repo, p, seen)

