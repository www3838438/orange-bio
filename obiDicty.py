import sys, pprint, time, re
from mMisc import *
from itertools import *
import urllib
import orange
import socket


#utility functions - from Marko's mMisc.py

def splitN(origsize, maxchunk):
    """
    Splits an integer into chunks of given size. Each created chunk
    except possibly the last one is of maximum allowed size.
    Chunks are returned in list.
    """
    l = [maxchunk]*(origsize/maxchunk)
    a = origsize % maxchunk
    if a > 0: 
        l.append(a)
    return l

def split(l, maxchunk):
    """
    Splits list l into chunks of size maxchunk. Each created chunk
    except possibly the last one is of maximum allowed size.
    """
    sizes = splitN(len(l), maxchunk)
    out = []
    tillNow = 0
    for s in sizes:
        out.append(l[tillNow:tillNow+s])
        tillNow += s
    return out       

def lloc(l,n):
    """
    List location in list of list structure.
    Enable the use of negative locations:
    -1 is the last element, -2 second last...
    """
    if n < 0:
        return len(l[0])+n
    else:
        return n

def loc(l,n):
    """
    List location.
    Enable the use of negative locations:
    -1 is the last element, -2 second last...
    """
    if n < 0:
        return len(l)+n
    else:
        return n

def nth(l,n):
    """
    Returns only nth elemnt in a list.
    """
    n = lloc(l,n)
    return [ a[n] for a in l ]

def imnth(l, ns):
    """
    Return only columns as specified in ns. Returns an generator.
    """
    ns = [ lloc(l,n) for n in ns ]
    for a in l:
        yield [ a[n] for n in ns ]

def flatten(l,r=0):
    """
    Flatten a python structure into a list. Leave strings alone.
    """
    if type(l) == type("a"):
        return [ l ]
    try: #if enumerable then flatten it's elements
        rec = [ flatten(a,r=r+1) for a in l ]
        ret = []
        for a in rec:
            ret = ret + a
        return ret
    except:
        return [ l ]

def mxrange(lr):
    """
    Multiple xranges. Can be used to traverse matrices.
    This function is very slow due to unknown number of
    parameters.

    >>> mxrange([3,5]) 
    [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2)]
    >>> mxrange([[3,5,1],[9,0,-3]])
    [(3, 9), (3, 6), (3, 3), (4, 9), (4, 6), (4, 3)]
    """
    if len(lr) == 0:
        yield ()
    else:
        #it can work with single numbers
        index = lr[0]
        if type(1) == type(index):
            index = [ index ]
        for a in range(*index):
            for b in mxrange(lr[1:]):
                yield tuple([a] + list(b))

#end utility functions

socket.setdefaulttimeout(10)

verbose = 0

def median(l):
    if len(l) == 0:
        return None
    l = sorted(l)
    if len(l) % 2 == 1: #odd
        return l[len(l)/2]
    else: #even
        return (l[len(l)/2-1] + l[len(l)/2])/2.0


class HttpGetException(Exception): pass

def httpGet(address, *args, **kwargs):
    if verbose: 
        print address
    t1 = time.time()
    f = urllib.urlopen(address, *args, **kwargs)
    read = f.read()
    if verbose:
        print time.time() - t1
    return read

def txt2ll(s, separ=' ', lineSepar='\n'):
    return [ a.split(separ) for a in s.split(lineSepar) ]

class DBInterface(object):
 
    def __init__(self, address, *args, **kwargs):
        self.address = address
        self.args = args
        self.kwargs = kwargs

    def raw(self, request, tryN=3):
        if verbose:
            print "tryN", tryN

        if tryN == 0:
            return None

        try:
            return httpGet(self.address + request, *self.args, **self.kwargs)
        except IOError:
            return self.raw(request, tryN=tryN-1)

    def get(self, request):
        rawf = self.raw(request)
        if rawf == None:
            raise Exception("Connection error when contacting " + self.address + request)
        a = txt2ll(rawf, separ='\t')
        if a[-1][0] == "": #remove empty line on end
            a = a[:-1]
        return a

def _test():
    import doctest
    doctest.testmod()

def splitTableOnColumn(ll,n):
    omap = {}
    n = lloc(ll,n)
    for l in ll:
        cell = omap.get(l[n], [])
        cell.append(l)
        omap[l[n]] = cell
    return omap

def neededColumns(legend, want):
    return [ legend.index(a) for a in want ]

def onlyColumns(ll, legend, want):
    return list(imnth(ll, neededColumns(legend, want)))

def ll2dic(ll, key=0, value=1):
    """
    Converts LL to map. Key is key position, value value position
    """
    names = nth(ll, lloc(ll, key))
    if len(names) == len(set(names)):
        return dict(list(imnth(ll, [ lloc(ll, key),  lloc(ll, value) ] )))
    else:
        raise Exception("all keys are not unique")

def dic2ll(dic):

    columns = sorted(dic.values()[0].keys())
    ll = []
    for key, d in dic.items():
        ll.append([ key ] + [ d[a] for a in columns ])
    return columns,ll

def allUnique(els):
    return len(els) == len(set(els))

def reverseDic(d):
    """
    Create a reverse dictionary if a unique reverse is possible.
    """
    if allUnique(d.values()):
        return dict([ (b,a) for a,b in d.items() ])

def chainLookup(a, dics, force=[]):
    """
    Goes through a list of dictionaries. On each step try to
    transform current key to value. The values becomes the key
    for next search If unsuccessfull, query the next
    dictionary with current key. Force last translation.
    """
    force = [ loc(dics, i) for i in force ]
    for i,dic in enumerate(dics):
        if i in force: #force specified translations
            a = dic[a]
        else:
            if a in dic:
                a = dic[a]
    return a

class DatabaseConnection(object):

    """
    Type is object id
    """
    
    aoidPairs = txt2ll("""time extractions.developmental_time_point
sample biological_samples.sample
growthCond biological_samples.growth_condition
treatment biological_samples.treatment
replicate biological_sample_replicates.replicate
techReplicate chips.replicate
platform chips.chip_platform
isTimeSeries biological_sample_replicates.is_time_series""")

    obidPairs = txt2ll("""norms normalizations
samples biological_samples
replicates biological_sample_replicates
analysis analysis
experiments experiments
extractions extractions
chips chips""")

    def __init__(self, address):
        self.db = DBInterface(address)
        self.preload()

    def preload(self):

        # aoids are mappings from annotation name to annotation id
        self.aoids = ll2dic(self.__annotationTypes(), 1, 0)
        self.saoids = ll2dic(self.aoidPairs, 0, 1)
        self.aoidsr = reverseDic(self.aoids)
        self.saoidsr = reverseDic(self.saoids)

        # obids are mappings from object id to annotation id
        self.obids = ll2dic(self.__objects(), 1, 0)
        self.sobids = ll2dic(self.obidPairs, 0, 1)
        self.obidsr = reverseDic(self.obids)
        self.sobidsr = reverseDic(self.sobids)

    def aoidt(self, s):
        return chainLookup(s, [self.saoids, self.aoids], force=[-1])

    def obidt(self, s):
        return chainLookup(s, [self.sobids, self.obids], force=[-1])
 
    def aoidtr(self, s, **kwargs):
        return chainLookup(s, [self.aoidsr, self.saoidsr], **kwargs)

    def obidtr(self, s):
        return chainLookup(s, [self.obidsr, self.sobidsr])

    def pq(self, q):
        """
        Prepare query. 
        ||| separator between conditions, 
        *** denotes equivalence
        """
        o =  "|||".join([ self.aoidt(a) + "***" + b for a,b in q.items()])
        return o

    def downloadMulti(self, command, ids):
        """
        Results in the same order as in ids. 
        #TODO - buffer?
        """
        sids = split(ids,100)

        for i,sidp in enumerate(sids):
            res = self.db.get(command.replace("$MULTI$", ",".join(sidp)))

            legend = res[0]
            res = res[1:]

            #split on different values of the first column - first attribute
            antss = splitTableOnColumn(res, 0)
    
            #put results in order
            tl = []
            for ci in sidp:
                yield antss[ci], legend

    def geneInfo(self):
        res,legend = self.sq("action=gene_info")
        return res, legend

    def annotationOptions(self, aoid=None, onlyDiff=False, **kwargs):
        """
        Returns annotation options for given query. Returns all possible annotations
        if the query is omitted.
        """
        params = ""
        if len(kwargs) > 0: params += "&query=" + self.pq(kwargs)
        if aoid: params += "&annotation_object_id=" + str(aoid)
        res,legend = self.sq("action=get_annotation_options%s" % (params))
        res = onlyColumns(res, legend, ['annotation_object_id', 'value' ])

        #join columns with the annotation object id
        joined = {}
        for key,v in res:
            key = self.aoidtr(key)
            cur = joined.get(key, [])
            cur.append(v)
            joined[key] = cur

        if onlyDiff:
            joined = dict([ (a,b) for a,b in joined.items() if len(b)>1 ])

        return dict([ (a, sorted(b)) for a,b in joined.items() ])

    def sq(self, s1):
        res = self.db.get(s1)
        return res[1:],res[0]

    def annotation(self, type, id):
        return list(self.annotations(type, [ id ]))[0]

    def meaningfulAnnot(self, name):
        if name in self.saoids:
            return True
        else:
            return False

    def keepOnlyMeaningful(self, annot):
        """
        Keep only meaningful annotations
        """
        if type(annot) == type({}):
            return dict( [ (a,b) for a,b in annot.items() \
                if self.meaningfulAnnot(a) ] )
        else:
            return [ [ a,b ] for a,b in annot \
                if self.meaningfulAnnot(a) ]


    def annotations(self, type, ids, all=False):
        antss = self.downloadMulti( \
            "action=get_annotations&ids=$MULTI$&object_id=%s" \
            % (self.obidt(type)), ids)

        for ants in antss:
            res, legend = ants
            res2 = onlyColumns(res, legend, ['name', 'value'])
            res2 = [ [ self.aoidtr(a),b ] for a,b in res2 ]
            if not all:
                res2 = self.keepOnlyMeaningful(res2)
            yield res2

    def search(self, type, **kwargs):
        """
        Break search for multiple values of one attribute to independant searches.
        
        List of searchable annotation types: self.saoids.keys()

        example usage:
        search("norms", platform='minichip', sample='abcC3-') 
            finds all ids of normalized entries where platform is minchip and 
            sample is abcC3-
        search("norms", platform='minichip', sample=[ 'abcC3-', 'abcG15-']) 
            finds all ids of normalized entries where platform is minichip and 
            sample is abcC3- or those where platform is minichip and sample
            is abcG15-
        """
        
        #search for all combinations of values - this is slow!

        l = []
        for k,v in kwargs.items():
            if not issequencens(v):
                v = [ v ]
            l.append((k,v))

        ares = []

        for r in mxrange([ len(v) for k,v in l ]):
            dico = {}
            for i,a in enumerate(r):
                dico[l[i][0]] = l[i][1][a]

            res,_ = self.sq("action=search&object_id=%s&query=%s" \
                % (self.obidt(type), self.pq(dico)))
            ares += res

        return sorted(set(nth(ares, 0)))

    def chipN(self, id, columns=["spot_id", 'M']):
        res,legend = self.sq("action=get_normalized_data&ids=%s" % (id))
        #res2 = onlyColumns(res, legend, ["spot_id", 'M', 'A'])
        res2 = onlyColumns(res, legend, columns)
        return res2

    def chipR(self, id):
        res,legend = self.sq("action=get_raw_data&ids=%s" % (id))
        #TODO remove unneeded columns
        res2 = res
        return res2
  
    def chipNs(self, ids):
        for id in ids:
            yield self.chipN(id)

    def chipRs(self, id):
        for id in ids:
            yield self.chipR(id)
   
    def spotId(self):
        res,legend = self.sq("action=spot_id_mapping")
        res2 = onlyColumns(res, legend, ["spot_id", 'ddb', 'genename'])
        return res2

    def annotationTypes(self):
        """
        Returns all annotation types.
        """
        return self.aoids.keys()

    def objects(self):
        """
        Returns all objects.
        """
        return self.obids.keys()

    def __annotationTypes(self):
        """
        Returns list of [ annotation_object_id, name ]
        """
        res, legend = self.sq("action=get_annotation_types")
        res2 = onlyColumns(res, legend, ["annotation_object_id", 'name'])
        return res2

    def __objects(self):
        res, legend = self.sq("action=get_objects")
        res2 = onlyColumns(res, legend, ["object_id", 'object_name'])
        return res2

    def spotMap(self):
        spotids = self.spotId()
        spotmap = [ (a[0],a[1]) for a in spotids ]

        spotmapd = {}

        for a,b in spotmap:
            if a in spotmapd:
                spotmapd[a] = spotmapd[a] + "-" + b
            else:
                spotmapd[a] = b

        return spotmapd

    def allAnnotationVals(self, annots):
        """
        All annotation valuess for given annotations
        in a dict of { name: set of possible values } pairs.
        """
        av = {}
        for a in annots:
            for name,val in a:
                cvals = av.get(name, set([]))
                cvals.add(val)
                av[name] = cvals
        return av

    def dictionarize(self, ids, fn, *args, **kwargs):
        return dict(zip(ids, list(fn(*args, **kwargs))))

    def groupAnnotations(self, annotations, prefix="", join=[], separate=None):
        """
        Groups annotations by joining annotation options in 'join' to
        the same group while keeping annotations with different values
        of options in 'separate' apart. If separate is None, use 
        all annotation types not in join as separate.

        Returns list of tuples. Each tuple describes a group and contains:
            1. [ (name, chipid) ] - a list of tuples containing group element 
                name and it's chip id.
            2. dictionary of joined annotations of group elements.

        """

        # Separate and join are not a regular expressions (because of group sorting).

        ignore=['.*']

        #If separate is None, use all annotation types not in join as separate.
        if separate == None:
            separate = sorted(set(self.saoids.keys())-set(join))

        annotationsIn = dict(annotations)

        if len(annotationsIn) == 0:
            return None

        #join should be top most specification
        topMost = [ self.aoidtr(a) for a in self.aoids.keys() ]

        def forceTopMost(l):
            for a in l:
                if a not in topMost:
                    raise Exception(a + " not top most annotation type." )
        forceTopMost(join)

        #check separate input #TODO

        #all possible annotations
        annots = self.allAnnotationVals(annotationsIn.values())

        ignoreNot = separate + join

        def isIgnored(a):
            for exp in ignoreNot:
                if re.match(exp, a):
                    return False
            for exp in ignore:
                if re.match(exp, a):
                    return True
            return False
    
        def ok(x):
            a,b = x
            if len(b) <= 1:
                return False
            if isIgnored(a):
                return False
            return True

        diffannots = dict(filter(ok, annots.items()))
        #print "DIFF ANNOTS", diffannots

        """
        Need to group
        those which have everything the same except of join while
        ignoring annotation which match meaningless + ignore.
        """
    
        def validAnnot(x):
            try: 
                fkdllfkd = self.aoidt(x)
                return True
            except:
                return False

        allowDiffSet = set(filter(validAnnot, join))
        danames = set(diffannots.keys())
        reallyDiff = danames & allowDiffSet
        leaveKeys = danames - reallyDiff

        #remove all non-neccessary keys form the annotation dictionary
        #and form tem in groups afterwards

        def dictWithOnly(dic, keys):
            """
            Returns a shallow copy of the dictionary with
            key not in keys removed.
            """
            odic = {}
            for a,b in dic.items():
                if a in keys:
                     odic[a] = b
            return odic

        candidates = dict([ (id, dictWithOnly(dict(d),leaveKeys) ) \
            for id,d in annotationsIn.items() ])

        def groupDicts(ldics):
            """
            Group same dictionaries together. Returns indices
            of original dictionaries
            """
            ldics = dict([(id,frozenset(d.items())) for id,d in ldics.items() ])
            
            dd = {}
            for i,d in ldics.items():
                group = dd.get(d, [])
                group.append(i)
                dd[d] = group

            return dd.values()

        groups = groupDicts(candidates)

        def joinedAnnotation(group):
            return self.allAnnotationVals([ annotationsIn[v] for v in group ])

        def csorted(l):
            """
            Return sorted list of string , but choose sorting type first:
            if all are integer, sort in integers and then return string
            """
            try:
                l = [ int(a) for a in l ]
            except:
                pass
            return [ str(a) for a in sorted(l) ]


        #sort the groups by their annotations
        def compareGroups(g1, g2):
            """
            Compare groups by consequtive comparison of annotatition values.
            Consider those in "separate" first.
            """

            #separated need to be top most!
            allannot = sorted(set(g1.keys()) - set(separate))
            allannot = separate + allannot

            for compnow in allannot:
                #try sorting values in lists as integers
                c = cmp(csorted(g1[compnow]), csorted(g2[compnow]))
                if c != 0:
                    return c

            return 0

        groups = sorted(groups, key=joinedAnnotation, cmp=compareGroups)

        """
        At this point the groups going to the same example table
        are already made. Now we need to control value order, example
        order and table order for those groups.

        Important decisions:
        - example order: by spot id
        - attribute order: ([1,2,3],[1,2]) -> [1,1],[1,2],[2,1],...
        - table order - comparison of annotation valeues
        """

        #respect specified order!
        differentialNames = [ a for a in join if a in reallyDiff ]
        differentialVals = [ csorted(diffannots[a]) for a in differentialNames ]

        def difV(li):
            """
            Returns differential values for tuples of indices (input list).
            (i,j) returns the i-th value for first differential name, 
            and j-th values for second differential name.
            """
            #print "difV", li, [ differentialVals[i][v] for i,v in enumerate(li) ]
            return [ differentialVals[i][v] for i,v in enumerate(li) ]

        def nameInds(values, inds):
            """
            Create attribute name for given values. If there are multiple 
            repetitions of the same value, enumerate them.
            """
            def aux(i,a):
                name = '_'.join([ n + '=' + v for n,v in values ])
                if len(inds) > 1:
                    name += "_" +  str(i)
                return name

            return [ aux(i,a) for i,a in enumerate(inds) ]
 
        def extractNeeded(annotations, needValues):
            """
            Returns indices (input list) of annotation with all values as 
            specified in needValues.
            """
            ok = []
            for i,an in enumerate(annotations):
                sl = sum([ an[nam] != val for nam,val in needValues ])
                if sl == 0: 
                    ok.append(i)
            return ok

        exampleTables = []

        for group in groups:

            lens = [ len(a) for a in differentialVals ]
            groupnames = []
            groupids = []

            for valsi in mxrange([ b for b in lens ]):

                gannots = [ ll2dic(annotationsIn[g]) for g in group ]

                needValues = zip(differentialNames, difV(valsi))
                inds = extractNeeded(gannots, needValues)

                groupids = groupids + [ group[a] for a in inds ]
                groupnames = groupnames + nameInds(needValues, inds)

            #Add every annotation. If there are multiple annotation values
            #for the same annotation, add all annotation values.
            
            ca = joinedAnnotation(group)
            #ca = dict( [(a,csorted(b)) for a,b in ca.items()] )

            exampleTables.append((zip(groupnames, groupids), ca))

        return exampleTables

    def exampleTables(self, chipsm, groups, spotmap={}, annotations=None):
        """
        Create example tables from chip readings, spot mappings and 
        group specifications.

        groups are input from "groupAnnotations" function. 
        spotmap is a dictionary of { spotid: gene }
        """

        if annotations != None:
            annotations = dict(annotations)

        exampleTables = []

        ids = flatten([ nth(g[0], 1) for g in groups ])

        #where to put n-th occurance of some spot id
        def outPositionMap(ids):
            """
            Where to put n-th occurance of some spot id.
            Input: list of lists of ids.
            Output: map of id,repetition -> position
            """
            
            amap = {}

            for lids in ids:

                repeats = {}
                for id in lids:
                    rep = repeats.get(id, 0)
                    repeats[id] = rep+1
                    key = (id, rep)
                    amap[key] = amap.get(key, 0) + 1

            return dict( [ (k,i) for i,k in enumerate(sorted(amap.keys())) ] )

        posMap = outPositionMap([ nth(c,0) for c in chipsm.values() ])
        npos = len(posMap.values())

        ddb = [ "" for a in range(npos) ] 

        for k,ind in posMap.items():
            ddb[ind] = spotmap.get(k[0], "#"+k[0]) 

        for group in groups:

            groupnames = []
            groupvals = []

            pairs = group[0]

            annotc = None
            if len(group) > 1:
                annotc = group[1]

            for name,chipid in pairs:

                vals = [ None ] * npos

                repeats = {}
                putinds = []
                for id,v in chipsm[chipid]:
                    rep = repeats.get(id, 0)
                    repeats[id] = rep+1
                    key = (id, rep)
                    putind = posMap[key]
                    putinds.append(putind)
                    vals[putind] = v

                groupnames.append(name)
                groupvals.append(vals)

            et = createExampleTable(groupnames, groupvals, ddb)

            if annotations:
                annotc = self.allAnnotationVals( [annotations[v] for v in nth(pairs,1) ] )

            setattr(et, "annot", annotc)
            exampleTables.append(et)
    
        return exampleTables

    def getData(self, type="norms", join=["time"], separate=None, average=median, **kwargs):
        """
        Returns a list of examples tables for a given search query and post-processing
        instructions.
        Parameters: 
            average: function used for combining multiple reading of the same spot on
                a chip.
            join: a list of annotation types which can be different in a single example
                table. Chips are grouped in groups, which can contain chips which have
                same annotations.
            separate: annotation types by which we consider groups as separate ones.
                If blank, take all those not in join.

        Defaults: Median averaging. Join by time.
        """
        #returns ids of elements that match the search function
        ids = self.search(type, **kwargs)

        #downloads annotations
        read = self.dictionarize(ids, self.annotations, type, ids)
        
        #make annotatio groups
        etsa = self.groupAnnotations(read, join=join, separate=separate )
        if type == "norms":
            fun = self.chipNs
        else:
            fun = self.chipRs

        #here could user intervent. till now downloads were small

        #donwload chip data
        chipd = self.dictionarize(ids, fun, ids)

        #create example tables grouped according to user's wishes
        ets = self.exampleTables(chipd, etsa, spotmap=self.spotMap())

        #if average function is given, use it to join same spotids
        if average != None:
            etsa = []
            for et in ets:
                eta = averageAttributes(et, fn=average)
                eta.annot = et.annot
                etsa.append(eta)
            ets = etsa

        return ets

def createExampleTable(names, vals, ddb, cname="DDB"):
    """
    Create an ExampleTable for this group. Attributes are those in
    names. 

    """
    attributes = [ orange.FloatVariable(n, numberOfDecimals=3) \
        for n in names ]
    domain = orange.Domain(attributes, False)
    ddbv = orange.StringVariable(cname)
    id = orange.newmetaid()
    domain.addmeta(id, ddbv)

    examples = []
    for v,d in izip(izip(*vals), ddb):
        ex = orange.Example(domain, [ floatOrUnknown(a) for a in v ])
        ex[cname] = d
        examples.append(ex)

    return orange.ExampleTable(domain,examples)


def averageAttributes(data, joinc="DDB", fn=median):
    """
    Averages attributes with the same "join" parameter using
    specified function. Builds a now dataset. Order of
    "join" parameter stays the same with regard to first
    appearance.
    """

    valueso = []
    valuess = set(valueso)

    attributes = [ a for a in data.domain.attributes ]
    domain = data.domain

    #accumulate values
    valuesddb = dict( [ (at,{}) for at in attributes ])

    for ex in data:
        #join attribute - ddb
        j = str(ex[joinc])

        if j not in valuess:
            valueso.append(j)
            valuess.add(j)

        for a in attributes:
            val = ex[a]
            l = valuesddb[a].get(j, [])
            if not val.isSpecial():
                l.append(val.native())
            valuesddb[a][j] = l

    #print "len valueso", len(valueso)
    #print sorted(set([ str(ex[join]) for ex in data ]))

    #apply function fn to each attribute

    #print valuesddb[valuesddb.keys()[0]]

    for a in attributes:
        for n,v in valuesddb[a].items():
            valuesddb[a][n] = floatOrUnknown(fn(v))

    #create a new example table reusing the domain
    examples = []
    for v in valueso:
        example = orange.Example(domain, \
            [ valuesddb[a][v] for a in attributes ] )
        example[joinc] = v
        examples.append(example)

    return orange.ExampleTable(domain, examples)

def floatOrUnknown(a):
    """
    Converts an element to float if possible.
    If now, output "?".
    """
    try:
        return float(a)
    except:
        return "?"
