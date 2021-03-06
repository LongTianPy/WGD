#!/usr/bin/python

# This script implements everything into one and multiprocess tasks that can be paralleled.

# IMPORT
# BUILT-IN MODULES
import argparse
import os
from os import listdir
from os.path import isfile, join
import multiprocessing as mp
import pandas as pd
from Bio import SeqIO
import sys
from functools import partial
# SCRIPTS
import prot_to_cds
import run_paml_yn00
import ks_correction
import convert1
import process_blast
import process_cluster_all
import run_muscle

# FUNCTIONS

# MAIN
def main(argv=None):
    if argv is None:
        argv = sys.argv
    args = get_parsed_args()
    working_dir = args.working_dir
    if not working_dir.endswith('/'):
        working_dir = working_dir + '/'
    else:
        working_dir = working_dir
    nucleotide_cds = args.nucleotide_cds
    out_prefix = args.output_pref
    identity = args.identity
    coverage = args.coverage
    # afa_file_list = Hong_wrapper(nucleotide_cds=nucleotide_cds, identity=identity, coverage=coverage, output_prefix=out_prefix,working_dir=working_dir)
    kS_df_total = pd.DataFrame()
    nucleotide_cds_trunc = nucleotide_cds+'_trunc'
    f = open("top10_list.txt","r")
    afa_file_list = [i.strip() for i in f.readlines()]
    f.close()
    print "Reverse translating proteins based on provided CDS and running CODEML."
    print "Runtime depends..."
    # cluster_file_list = [join(working_dir,f) for f in listdir(working_dir) if isfile(join(working_dir,f)) and f.endswith(".txt")]
    # afa_file_list = [cluster_file+'.afa' for cluster_file in cluster_file_list]
    for afa_file in afa_file_list:
        run = Andrew_wrapper(afa_file, nucleotide_cds_trunc)
        ks_df = ks_correction.correct_ks(run)
        ks_df.to_csv(afa_file+".csv")
        kS_df_total = kS_df_total.append(ks_df)
    # Draw histogram
    print "Correcting kS...\n"
    print "Plotting on canvas..."
    kS_df_total.to_csv(working_dir+"ks.csv")
    ks_correction.draw_histo(kS_df_total,working_dir)

# Arguments
def get_parsed_args():
    """
    Parse the command line arguments
    Parses command line arguments using the argparse package, which is a
    standard Python module starting with version 2.7.
    :return:
        args: An argparse.Namespace object containing all parsed the arguments
    """
    parser = argparse.ArgumentParser(
        description="Generate kS distrbution histogram to detect Whole Genome Duplication (WGD) events. "+
                    "Taking the full coding sequences of an organism as input.")
    parser.add_argument("-i", dest='nucleotide_cds', help="Full coding sequences of the organism of interest.")
    parser.add_argument("-o", dest='output_pref', help="Prefix for the MCL clustered files.")
    parser.add_argument("-d", dest='working_dir', default="./", help="Working directory to store intermediate files of each step. Default: ./ .")
    parser.add_argument("--identity", dest="identity", type=int, default=50, help="Threshold of percentage identity in BLAST result. Default: 50 .")
    parser.add_argument("--coverage", dest="coverage", type=int, default=30, help="Threshold of percentage alignment coverage in BLAST result. Default: 30 .")

    args = parser.parse_args()
    return args

# Individual wrappers
def Hong_wrapper(nucleotide_cds,output_prefix,identity,coverage,working_dir):
    protein_cds = nucleotide_cds+".protein"
    print "Translating CDS to proteins...\n"
    convert1.convert(nucleotide_cds)
    print "Self-blasting, this may take long...\n"
    process_blast.run_blast(protein_cds=protein_cds)
    mcl_out = protein_cds+".mcl_out"
    print "Clustering..."
    process_blast.process_blast_out(protein_cds=protein_cds,identity=identity,coverage=coverage)
    print "Matching clusters..."
    process_cluster_all.process_cluster(mcl_out=mcl_out, protein_cds=protein_cds, output_prefix=output_prefix,working_dir=working_dir)
    cluster_file_list = [join(working_dir,f) for f in listdir(working_dir) if isfile(join(working_dir,f)) and f.endswith(".txt")]
    print "Aligning proteins with MUSCLE, this may take long..."
    pool_size = 8
    pool = mp.Pool(processes=pool_size)
    pool.map(run_muscle.muscle, cluster_file_list)
    afa_file_list = [cluster_file+'.afa' for cluster_file in cluster_file_list]
    return afa_file_list

def Andrew_wrapper(prot_cluster_file, nucleotide_file):
    """
    This function contains Andrew's part
    :param prot_cluster_file: Sequences of clusters
    :param nucleotide_file: cds file
    :return:
    """
    prot_to_cds_out = prot_cluster_file+".phy"
    prot_to_cds.write_align(prot_align_file=prot_cluster_file, nuc_fasta_file=nucleotide_file, nuc_align_file=prot_to_cds_out)
    prot_to_cds_out_sub = prot_to_cds_out+"_sub" # Subtitute dot to 2 spaces
    pattern = 's/\./  /g'
    cmd = "sed '{0}' {1} > {2}".format(pattern, prot_to_cds_out, prot_to_cds_out_sub)
    os.system(cmd)
    run = run_paml_yn00.run_yn00(prot_to_cds_out_sub)
    return run

def Andrew_Long_wrapper(prot_cluter_file, nucleotide_file_trunc,kS_total):
    try:
        run = Andrew_wrapper(prot_cluter_file,nucleotide_file_trunc)
        ks_df = ks_correction.correct_ks(run)
        kS_df_total = kS_df_total.append(ks_df)
    except:
        pass




if __name__ == "__main__":
    main()






