import argparse, collections, configparser, hashlib, os, re, sys, zlib
#import grp, pwd
from datetime import datetime
from fnmatch import fnmatch
from math import ceil
#gets argparse important, other imports like print working directory and os and system calls
#zlib for compression and decompression
#collections adds extra commands for our data types like strings and dicts


#RENAME ALL VARIABLES AND METHODS TO BE MORE DESCRIPTIVE



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
        case "ls-tree"      : cmd_ls_tree(args)
        case "checkout"     : cmd_checkout(args)
        case "show-ref"     : cmd_show_ref(args)
        case "tag"          : cmd_tag(args)
        case "rev-parse"    : cmd_rev_parse(args)
        case "ls-files"     : cmd_ls_files(args)
        case "check-ignore" : cmd_check_ignore(args)
        case "status"       : cmd_status(args)
        case "rm"           : cmd_rm(args)
        case "add"          : cmd_add(args)
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

def object_read(repo, sha):

    path = repo_file(repo, "objects", sha[0:2], sha[2:1])

    if not os.path.isfile(path):
        return None
    
    with open(path, "rb") as writer:
        raw = zlib.decompress(writer.read)

        #reads object type
        x = raw.find(b' ')
        format = raw[0:x]

        y = raw.find(b'\x00', x)
        size = int(raw[x:y].decode("ascii"))
        if size != len(raw)-y-1:
            raise Exception("Malformed Object {0}: bad length".format(sha))
        
        #constructor
        match format:
            case b'commit' : c=GitCommit
            case b'tree'  : c=GitTree
            case b'tag'   : c=GitTag
            case b'blob'  : c=GitBlob
            case _:
                raise Exception("Unknown type {0} for object {1}".format(format.decode("ascii"), sha))
            
        #call constructor and return object
        return c(raw[y+1:])


def object_writer(obj, repo = None):

    data = obj.serialize()

    result = obj.format + b' ' + str(len(data)).encode() + b'\x00' + data

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
def object_find(repo, name, format = None, follow = True):
    return name
#hi
#hi

#instance object git object match constructer super
#blob = contents of a fuke
class GitBlob(GitObject):
    format = b'blob'

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
    cat_file(repo, args.object, format = args.type.encode())

def cat_file(repo, obj, format = None):
    obj = object_read(repo, object_find(repo, obj, format = format))
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
def object_hash(fd, format, repo = None):

    data = fd.read()

    match format:
        case b'commit' : c=GitCommit(data)
        case b'tree'   : c=GitTree(data)
        case b'tag'    : c=GitTag(data)
        case b'blob'   : c=GitBlob(data)
        case _:
            raise Exception("Unknow Type %s!" % format)
    
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
    format = b'commit'

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
    assert commit.format == b'commit'

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


#all tree logic
#goes through trees using recursive functions
#extracts and reads from objcts and places them back in correct sorted order


class GitTree(GitObject):
    format = b'tree'

    def init(self):
        self.items = list()

    def deserialize(self, data):
        self.items = tree_parse_data_extractor(data)
    
    def serialize(self, repo):
        return tree_serialize(self)

class GitTreeLeaf(object):

    def __init__(self, mode, path, sha):
        self.mode = mode
        self.path = path
        self.sha = sha
    
def tree_parse_data_extractor(raw, start = 0):

    modeSpaceTerminator = raw.find(b' ', start)
    assert modeSpaceTerminator - start == 5 or modeSpaceTerminator - start == 6

    mode = raw[start:modeSpaceTerminator]
    if len(mode) == 5:
        mode = b" " + mode
    
    pathNullTerminator = raw.find(b'\x00', modeSpaceTerminator)
    path = raw[modeSpaceTerminator + 1:pathNullTerminator]

    read_sha = int.from_bytes(raw[pathNullTerminator + 1: pathNullTerminator + 21], "big")

    paddedSha = format(read_sha, "040x")

    return pathNullTerminator+21, GitTreeLeaf(mode, path.decode("utf8"), paddedSha)


def tree_parse(raw):

    position = 0
    max = len(raw)
    returnVals = list()

    while position < max:
        position, data = tree_parse_data_extractor(raw, position)
        returnVals.append(data)
    
    return returnVals

def tree_leaf_sort_key_conversion(leaf):

    if leaf.mode.startswith(b"10"):
        return leaf.path
    else:
        return leaf.path + "/"

def tree_serialize(object):

    object.items.sort(key = tree_leaf_sort_key_conversion)
    returnVal = b''
    for leaf in object.items:
        returnVal += leaf.mode
        returnVal += b' '
        returnVal += leaf.path.encode("utf8")
        returnVal += b'\x00'
        sha = int(leaf.sha, 16)
        returnVal += sha.to_bytes(20, byteorder = "big")

    return returnVal

#subparser LS-TREE (ls-tree [-r recursive] TREE)

argsp = argsubparser.add_parser("ls_tree", help = "Print A Tree Object.")
argsp.add_argument("-r",
                   dest= "recursive",
                   action= "store_true",
                   help= "Recurse Into Its Sub-Trees")
argsp.add_argument("tree",
                   help= "A Tree-Like Object")

def cmd_ls_tree(args):
    repo = repo_find()
    ls_tree(repo, args.tree, args.recursive)

def ls_tree(repo, reference, recursive = None, prefix = ""):
    
    sha = object_find(repo, reference, format = b"tree")
    object = object_read(repo, sha)

    for item in object.items:
        if len(item.mode) == 5:
            type = item.mode[0:1]
        else:
            type = item.mode[0:2]
        
        match type:
            case b'04': type = "tree"
            case b'10': type = "blob"
            case b'12': type = "blob"
            case b'16': type = "commit"
            case _: raise Exception("Unknown Tree Leaf Mode {}".format(item.mode))

    if not (recursive and type == "tree"):
        print("{0} {1} {2}\t{3}".format(
            "0" * (6 - len(item.mode)) + item.mode.decode("ascii").
            type,
            item.sha,
            os.path.join(prefix, item.path)))
    else:
        ls_tree(repo, item.sha, recursive, os.path.join(prefix, item.path))

#subparser CHECKOUT (checkout commit path), added path for simplicity and security
argsp = argsubparser.add_parser("checkout", help= "Checkout A Commit Inside Of The Directory.")
argsp.add_argument("commit",
                   help= "The Commit Or Tree To Checkout")
argsp.add_argument("path",
                   help= "The Empty Directory To Checkout On.")

def cmd_checkout(args):

    repo = repo_find()
    object = object_read(repo, object_find(repo, args.commit))

    if object.format == b'commit':
        object = object_read(repo, object.kvlm[b'tree'].decode("ascii"))
    
    if os.path.exists(args.path):
        if not os.path.isdir(args.path):
            raise Exception("Not A Directory {0}!".format(args.path))
        if os.listdir(args.path):
            raise Exception("Not Empty Directory {0}".format(args.path))
    else:
        os.makedirs(args.path)
    
    tree_checkout(repo, object, os.path.realpath(args.path))

def tree_checkout(repo, tree, path):
    for item in tree.path:
        object = object_read(repo, item.sha)
        dest = os.path.join(path, item.path)

        if object.format == b'tree':
            os.mkdir(dest)
            tree_checkout(repo, object, dest)
        elif object.format == b'blob':
            with open(dest, 'wb') as writer:
                writer.write(object.blobdata)

#refrences

#subparser SHOW-REF (show-ref )
argsp = argsubparser.add_parser("show-ref", help= "Lists Object Refernces.")

def cmd_show_ref(args):
    repo = repo_find()
    refrences = refrence_list(repo)
    show_refrences(repo, refrences, prefix= "refs")

def show_refrences(repo, refrences, with_hash= True, prefix= ""):

    for key, value in refrences.items:
        if type(value) == str:
            print("{0}{1}{2}".format(
                value + " " if with_hash else "",
                prefix + "/" if prefix else "",
                key))
        else:
            show_refrences(repo, value, with_hash= with_hash, prefix= "{0}{1}{2}".format(prefix, "/" if prefix else "", key))


def refrence_resolver(repo, refrence):
    
    path = repo_file(repo, refrence)

    if not os.path.isfile(path):
        return None
    
    with open(path, 'r') as reader:
        data = reader.read()[:-1]
    
    if data.startswith("ref: "):
        return refrence_resolver(repo, data[5:])
    else:
        return data

def refrence_list(repo, path= None):
    if not path:
        path = repo_dir(repo, "refs")
    
    returnVals = collections.OrderedDict()

    for item in sorted(os.listdir(path)):
        pathBin = os.path.join(path, item)
        if os.path.isdir(pathBin):
            returnVals[item] = refrence_list(repo, pathBin)
        else:
            returnVals[item] = refrence_resolver(repo, pathBin)

#user defined ref values
class GitTag(GitCommit):
    format = b'tag'

#subparser TAG (tag [-a create new] name object)
argsp = argsubparser.add_parser("tag", help= "List And Create New Tags.")
argsp.add_argument("-a",
                   action= "store_true",
                   dest= "create_tag_object",
                   help= "Optional Create A Tag Object.")
argsp.add_argument("name",
                   nargs= "?",
                   help= "The Tags Name.")
argsp.add_argument("object",
                   default= "HEAD",
                   nargs= "?",
                   help= "The Object The Tag Will Point Towards.")

def cmd_tag(args):
    repo = repo_find()

    if args.name:
        tag_create(repo, args.name, args.object, type= "object" if args.create_tag_object else "ref")
    else:
        refrences = refrence_list(repo)
        show_refrences(repo, refrences["tags"], with_hash= False)

def tag_create(repo, name, refernce, create_tag_object= False):
    sha = object_find(repo, refernce)

    if create_tag_object:
        tag = GitTag(repo)
        tag.kvlm = collections.OrderedDict()
        tag.kvlm[b'object'] = sha.encode()
        tag.kvlm[b'type'] = b'commit'
        tag.kvlm[b'tag'] = name.encode()
        tag.kvlm[b'tagger'] = b'Wyag <test>' #fix
        tag.kvlm[None] = b"A Tag Generated By Eseption's Wyag, Message Hardcoded."
        tag_sha = object_writer(tag)
        reference_create(repo, "tags/" + name, tag_sha)
    else:
        reference_create(repo, "tags/" + name, sha)

def reference_create(repo, reference_name, sha):
    with open(repo_file(repo, "refs/" + reference_name), 'w') as writer:
        writer.write(sha + "\n")


#fixed error in object_read, added tree and checkout, refs and tags