


IDs_to_test = ["","CBVeto", "CBLoose", "CBMedium", "CBTight", "noisoCBVeto", "noisoCBLoose", "noisoCBMedium", "noisoCBTight"]
'''
Possible options to add are the dict keys in the function below
'''




def getListOfAvailableIDs(treename):
    IDlist = {}
    IDlist[""] = "True"
    IDlist['CBVeto'] = treename+"passingCutBasedVeto94XV2"
    IDlist['CBLoose'] = treename+"passingCutBasedLoose94XV2"
    IDlist['CBMedium'] = treename+"passingCutBasedMedium94XV2"
    IDlist['CBTight'] = treename+"passingCutBasedTight94XV2"


    # CutBased ID with no iso
    def getCutBasedMembersNoIso(wp):
        membersNoIso = ["MinPtCut","GsfEleSCEtaMultiRangeCut","GsfEleMissingHitsCut","GsfEleHadronicOverEMEnergyScaledCut","GsfEleFull5x5SigmaIEtaIEtaCut","GsfEleEInverseMinusPInverseCut","GsfEleDPhiInCut","GsfEleDEtaInSeedCut","GsfEleConversionVetoCut"] # "GsfEleRelPFIsoScaledCut"

        for i in range(len(membersNoIso)):
            membersNoIso[i] = "passingCutBased"+wp+"94XV2"+membersNoIso[i]
        return membersNoIso

    def getCutBasedCondinitionStringNoIso(treename, wp):
        membersNoIso = getCutBasedMembersNoIso(wp)

        conditionstring = ""
        for i in range(len(membersNoIso) - 1):
            conditionstring += treename + membersNoIso[i] + " and "
        conditionstring += treename + membersNoIso[-1]
        return conditionstring

    IDlist['noisoCBVeto'] = getCutBasedCondinitionStringNoIso(treename, "Veto")
    IDlist['noisoCBLoose'] = getCutBasedCondinitionStringNoIso(treename, "Loose")
    IDlist['noisoCBMedium'] = getCutBasedCondinitionStringNoIso(treename, "Medium")
    IDlist['noisoCBTight'] = getCutBasedCondinitionStringNoIso(treename, "Tight")



    IDlist['isoMVA80'] = treename+"passingMVA94Xwp80iso"
    IDlist['isoMVA90'] = treename+"passingMVA94Xwp90iso"
    IDlist['isoMVALoose'] = treename+"passingMVA94XwpLooseiso"
    IDlist['noisoMVA80'] = treename+"passingMVA94Xwp80noisoV2"
    IDlist['noisoMVA90'] = treename+"passingMVA94Xwp90noisoV2"
    IDlist['noisoMVALoose'] = treename+"passingMVA94XwpLoosenoisoV2"

    return IDlist


'''
options are:
CBVeto, CBLoose, CDMediom, CBTight
noisoCBVeto, noisoCBLoose, noisoCDMedium, noisoCBTight
isoMVA80, isoMVA90, isoMVALoose
noisoMVA80, noisoMVA90, noisoMVALoose
'''
