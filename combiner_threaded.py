import os
import ROOT
from ROOT import addressof
import numpy as np
import math
from datetime import datetime
import multiprocessing

def get_parser():
    import argparse
    argParser = argparse.ArgumentParser(description = "Argument parser")
    argParser.add_argument('filename',help='filename')
    argParser.add_argument('-Nthreads',           action='store',                    type=int,            default=-1,           help="How many CPU?"  )
    argParser.add_argument('-WP',           action='store',                    type=str,            default="",           help="ID workingpoint for preferred collection"  )
    return argParser

options = get_parser().parse_args()


now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print "Current Time = "+str(current_time)

if(options.Nthreads < 0):
    options.Nthreads = multiprocessing.cpu_count()
print "Threadcount = "+str(options.Nthreads)







# Get the IDs to do combination for
import IDconfig
activeIDlist = IDconfig.IDs_to_test
availableIDdict = IDconfig.getListOfAvailableIDs("std_tree.")


conditionstrings = []
IDlist = []
for key in activeIDlist:
    if key in availableIDdict:
        conditionstrings.append(availableIDdict[key])
        IDlist.append(key)
    else:
        print "Warning: unrecognized ID key: "+key
# Get a list of conditionstrings corresponding to activelist from available list
# that goes into the combiner function as IDlist









### Get the files
inputfile = ROOT.TFile.Open(options.filename)

std_tree = inputfile.tnpEleIDs.Get("fitter_tree")
lowpt_tree = inputfile.tnpLowPtEleIDs.Get("fitter_tree")




# IN case of duplicate entry (both std and lowpt) we need to decide which to keep, resolve by disabling either the std or the lowpt entry

#lowEvents = multiprocessing.Manager().list(range(lowpt_tree.GetEntries()))   # Manager: Server process managers are more flexible than using shared memory objects because they can be made to support arbitrary object types. Also, a single manager can be shared by processes on different computers over a network. They are, however, slower than using shared memory.
#lowEvents = multiprocessing.Array('i',range(lowpt_tree.GetEntries()))  # SynchronizedArray wrapper for shared memory

# lowEvents STRUCTURE:
# lowEvents for each IDtype requested in config file: lowEvents[i]: contains SynchronizedArrays of entry indices
# 'footer': lowEvents[-1]: contains 'false's in the beginnign, specifies whether this entry has been found as duplicate and resolved and thus may be skipped for next std entry comparisons
lowEvents = []
for i in range(len(conditionstrings)):
    lowEvents.append(multiprocessing.Array('i',range(lowpt_tree.GetEntries())))
# footer
lowEvents.append(multiprocessing.Array('i',[0]*lowpt_tree.GetEntries()))


stdEvents = []
for i in range(len(conditionstrings)):
    stdEvents.append(multiprocessing.Array('i',range(std_tree.GetEntries())))




def dR(eta_1, eta_2, phi_1, phi_2):
    phipart = phi_1-phi_2
    if( phipart < -math.pi):
        phipart += 2*math.pi
    elif( phipart > math.pi):
        phipart -= 2*math.pi
    return math.sqrt((eta_1-eta_2)**2 + (phipart)**2 )



# assert len(IDlist) == len(LowEvents) - 1
def findOverlapEntries(synclock, it0, it1, input_filename, lowEvents, stdEvents, IDconditionlist):
    assert len(IDconditionlist) == len(lowEvents) - 1 and len(lowEvents) - 1 == len(stdEvents), "array lens are incorrect"

    # Opened root files cannot be read by threads at the same time
    # each thread must open its own resource
    inputfile = ROOT.TFile.Open(input_filename)

    std_tree = inputfile.tnpEleIDs.Get("fitter_tree")
    lowpt_tree = inputfile.tnpLowPtEleIDs.Get("fitter_tree")

    for i in range(it0, it1, 1):
        std_tree.GetEntry(i)

        for j in range(lowpt_tree.GetEntries()):
            if(lowEvents[-1][j] > 0): # skip resolved events
                continue

            lowpt_tree.GetEntry(lowEvents[0][j])

            if std_tree.run == lowpt_tree.run and std_tree.event == lowpt_tree.event and dR(std_tree.tag_Ele_eta, lowpt_tree.tag_Ele_eta, std_tree.tag_Ele_phi, lowpt_tree.tag_Ele_phi) < 0.001 and abs(std_tree.tag_Ele_pt - lowpt_tree.tag_Ele_pt) < 0.001:
                # same event (because we have same tag)
                # check if probe is also same  --> same definition for removing overlap as in AN code
                if dR(std_tree.el_eta, lowpt_tree.el_eta, std_tree.el_phi, lowpt_tree.el_phi) < 0.1:
                    # same event, same tag, same probe -> we take standard as preference in overlaps
                    with synclock:
                        for id_i in range(len(IDconditionlist)):
                            if eval(IDconditionlist[id_i]) == 1:
                                lowEvents[id_i][j] = -1    # disable the lowpt entry for each ID case where the std is passing probe and takes preference
                            else:
                                stdEvents[id_i][i] = -1    # disable the std entry for each ID case where the std is failing probe (we'll resort to the lowpt entry instead)
                        lowEvents[-1][j] = 1   # resolved duplicate
                    break


Nentries = std_tree.GetEntries()
synclock = multiprocessing.Lock()
proc = {}

for i in range(options.Nthreads):
    it0 = 0 + i * (Nentries) / options.Nthreads 
    it1 = 0 + (i+1) * (Nentries) / options.Nthreads 
    proc[i] = multiprocessing.Process(target=findOverlapEntries, args=(synclock, it0, it1, options.filename, lowEvents, stdEvents, conditionstrings))
    proc[i].start()

for i in range(options.Nthreads):
    proc[i].join()



now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print "Current Time = "+str(current_time)



# New trees
def setupAndSaveNewTrees(it0, it1, IDlist, input_filename, stdEvents, lowEvents):
    inputfile = ROOT.TFile.Open(input_filename)

    std_tree = inputfile.tnpEleIDs.Get("fitter_tree")
    lowpt_tree = inputfile.tnpLowPtEleIDs.Get("fitter_tree")

    for i_id in range(it0, it1, 1):
        outfile = ROOT.TFile.Open("combiner_temp-"+IDlist[i_id]+".root", "RECREATE")
        wpname = "beIdCo" if IDlist[i_id] == "" else "afIdCo_"+IDlist[i_id]

        comb_tree = ROOT.TTree("fitter_tree","tnpCombinedEle_StdPref_"+wpname+"_IDs")

        # Setup branches:
        from array import array

        BranchAddresses = {}

        def addbranch(name):
            #globals()[name] = array('f', [0])
            BranchAddresses[name] = array('f', [0])
            comb_tree.Branch(name, BranchAddresses[name], name+'/F')


        addbranch("probeType")

        # Features from Standard
        std_branches = std_tree.GetListOfBranches()
        for i in range(std_branches.GetEntries()):
            addbranch(std_branches[i].GetName())

        # Extra features from LowPt:
        lowpt_branches = lowpt_tree.GetListOfBranches()
        for i in range(lowpt_branches.GetEntries()):
            for j in range(std_branches.GetEntries()):
                if lowpt_branches[i].GetName() == std_branches[j].GetName(): break
            else: #nobreak
                addbranch(lowpt_branches[i].GetName())


        # fill new tree with passing and non-matched std events (where lowpt did not take priority)
        for i in range(len(stdEvents[i_id])):
            if(stdEvents[i_id][i] == -1):  # skip
                continue
            std_tree.GetEntry(stdEvents[i_id][i])

            for j in range(std_branches.GetEntries()):
                BranchAddresses[std_branches[j].GetName()][0] = eval("std_tree." + std_branches[j].GetName())
            BranchAddresses['probeType'][0] = 1.0
                
            comb_tree.Fill()


        # fill remaining (non-overlapping) lowpt events 
        for i in range(len(lowEvents[i_id])):
            if(lowEvents[i_id][i] == -1):  # overlapping event, skip
                continue
            lowpt_tree.GetEntry(lowEvents[i_id][i])

            for j in range(lowpt_branches.GetEntries()):
                BranchAddresses[lowpt_branches[j].GetName()][0] = eval("lowpt_tree." + lowpt_branches[j].GetName())
            BranchAddresses['probeType'][0] = 2.0

            comb_tree.Fill()


        # Write the new tree
        newdir = ROOT.TDirectoryFile("tnpCombinedEleIDs_temp","tnpCombinedEleIDs_temp")
        newdir.WriteObject(comb_tree,"fitter_tree")

        outfile.Close()


# FIXME: OPTIMIZTE NUMBER OF THREADS HERE
proc = {}
for i in range(len(IDlist)):
    it0 = i
    it1 = i+1
    proc[i] = multiprocessing.Process(target=setupAndSaveNewTrees, args=(it0, it1, IDlist, options.filename, stdEvents, lowEvents))
    proc[i].start()

for i in range(options.Nthreads):
    proc[i].join()


readfiles = []
for id_i in range(len(IDlist)):
    readfiles.append(ROOT.TFile.Open("combiner_temp-"+IDlist[id_i]+".root"))




# Write the new trees
for id_i in range(len(IDlist)):
    outfile = ROOT.TFile.Open(options.filename, "UPDATE")
    wpname = "beIdCo" if IDlist[id_i] == "" else "afIdCo_"+IDlist[id_i]
    savetree = readfiles[id_i].tnpCombinedEleIDs_temp.Get("fitter_tree").CloneTree()
    newdir = ROOT.TDirectoryFile("tnpCombinedEle_StdPref_"+wpname+"_IDs","tnpCombinedEle_StdPref_"+wpname+"_IDs")
    newdir.WriteObject(savetree,"fitter_tree")
    outfile.Close()

#for id_i in range(len(IDlist)):
#    os.remove("./combiner_temp-"+IDlist[id_i]+".root")


now = datetime.now()
current_time = now.strftime("%H:%M:%S")
print "Current Time = "+str(current_time)