"""
lightsub submits rapid sequences to COG server 

Need Ocarina to run

### CHANGE LOG ### 
2020-09-02 Nabil-Fareed Alikhan <nabil@happykhan.com>
    * Initial build - split from dirty scripts
"""

import meta
from climbfiles import ClimbFiles
import logging 
import os 
import time
import argparse
import csv 

epi = "Licence: " + meta.__licence__ +  " by " +meta.__author__ + " <" +meta.__author_email__ + ">"
logging.basicConfig()
log = logging.getLogger()

def upload_files(sample_dict, output_dir, climb_file_server, climb_username, nanopore=False):
    run_name = args.runname
    # Upload files to FTP. 
    output_dir_bams = os.path.join(output_dir, 'ncovIllumina_sequenceAnalysis_trimPrimerSequences')
    output_dir_consensus = os.path.join(output_dir, 'ncovIllumina_sequenceAnalysis_makeConsensus')
    if args.ont:
        output_dir_bams = os.path.join(output_dir, "articNcovNanopore_sequenceAnalysisMedaka_articMinIONMedaka")
        output_dir_consensus = os.path.join(output_dir, "articNcovNanopore_sequenceAnalysisMedaka_articMinIONMedaka")
    climb_server_conn = ClimbFiles(climb_file_server, climb_username)
    climb_server_conn.create_climb_dir('upload')
    climb_run_directory = os.path.join('upload', run_name)
    climb_server_conn.create_climb_dir(climb_run_directory)
    for sample_name, sample in sample_dict.items():
        bam_path = os.path.join(output_dir_bams,  sample['bam'])
        fasta_path =  os.path.join(output_dir_consensus, sample['fasta'])   
        climb_sample_directory = os.path.join(climb_run_directory, sample_name)
        climb_server_conn.create_climb_dir(climb_sample_directory)        
        climb_server_conn.put_file(fasta_path, climb_sample_directory)
        climb_server_conn.put_file(bam_path, climb_sample_directory)

    return sample_dict

def create_library_command(library_name, sample_names, output_dir):
    """
    ocarina put library --library-name "CV083_24_M1" \
                --library-seq-kit "LSK-109 EXP-NBD104 EXP-NBD114" \
                --library-seq-protocol "LIGATION" \
                --library-layout-config "SINGLE" \
                --biosamples ALDP-981059 ALDP-9805A6 ALDP-97FE36 ALDP-97FFAC ALDP-97FEDC ALDP-97F883 ALDP-98243E ALDP-982683 ALDP-98150F ALDP-9819F4 ALDP-981A00 ALDP-980C74 ALDP-98104A ALDP-980588 ALDP-9802AF ALDP-97FEBE ALDP-97FF06 ALDP-97FA32 ALDP-9823F5 ALDP-9826CF ALDP-98152D ALDP-9819E5 ALDP-981C64 \
                --apply-all-library VIRAL_RNA PCR AMPLICON Artic-V3 3
    """
    biosamples = ' '.join(sample_names)
    out = open(os.path.join(output_dir, 'temp.library.sh'), 'w')
    out.write(f'ocarina put library --library-name "{library_name}"  --library-layout-config "PAIRED"  --library-seq-protocol "NEXTERA LITE" --biosamples {biosamples}  --apply-all-library VIRAL_RNA PCR AMPLICON Artic-V3 3 --library-seq-kit "NEXTERA" ')


def create_run_command(library_name, run_name, output_dir):
    """
    ocarina put sequencing --library-name "CV082_24_M1" \
                   --run-name "20200829_1510_X1_FAN42982_f5423095" \
                   --instrument-make "OXFORD_NANOPORE" \
                   --instrument-model "GridION" \
                   --flowcell-type "FLO-MIN106" \
                   --flowcell-id "FA041769" \
                   --start-time "2020-09-02 01:06"
    """    
    out = open(os.path.join(output_dir, 'temp.run.sh'), 'w')
    out.write(f'ocarina put sequencing --library-name "{library_name}"  --run-name "{run_name}"  --instrument-make "ILLUMINA"  --instrument-model NEXTSEQ')

def get_samples(datadir, prefix='E'):
    all_samples = {} 
    qc_file =  [x for x in os.listdir(datadir) if x.startswith('NORW') and x.endswith('qc.csv')][0]
    qc_file_path = os.path.join(datadir, qc_file)
    upload_path = os.path.join(datadir , 'uploadlist')
    upload = []  
    if os.path.exists(upload_path):
        upload = [x.strip() for x in open(upload_path).readlines()]
    for record in csv.DictReader(open(qc_file_path)):
        record['sample_name'] = record['sample_name'].split('_')[0]
        yes = False 
        if upload:
            if record['sample_name'] in upload:
                yes = True
        else:
            yes =  True 

        if record['sample_name'].startswith(prefix) and yes:
            all_samples[record['sample_name']] = record        
        if record['sample_name'].startswith('MILK') and yes:
            all_samples[record['sample_name']] = record
        if record['sample_name'].startswith('ALDP') and yes:
            all_samples[record['sample_name']] = record
        if record['sample_name'].startswith('QEUH') and yes:
            all_samples[record['sample_name']] = record            
        if record['sample_name'].startswith('CAMC') and yes:
            all_samples[record['sample_name']] = record                        
        if record['sample_name'].startswith('RAND') and yes:
            all_samples[record['sample_name']] = record     
            

    return all_samples, qc_file.split('.')[0]

def main(args):
    sample_dict, library_name = get_samples(args.datadir, args.prefix)
    upload_files(sample_dict, args.datadir, args.climb_server, args.climb_user, args.ont)
    if not os.path.exists(args.output_dir):
        os.mkdir(args.output_dir)
    create_library_command(library_name, sample_dict.keys(), args.output_dir)
    create_run_command(library_name, args.runname, args.output_dir)


if __name__ == '__main__':
    start_time = time.time()
    log.setLevel(logging.INFO)
    desc = __doc__.split('\n\n')[0].strip()
    parser = argparse.ArgumentParser(description=desc,epilog=epi)
    parser.add_argument ('-v', '--verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s ' + meta.__version__)
    parser.add_argument('datadir', action='store', help='Location of ARTIC pipeline output')
    parser.add_argument('runname', action='store', help='Sequencing run name, must be unique')
    parser.add_argument('--output_dir', action='store_true', default="majora_scripts", help='output_directory')
    parser.add_argument('--ont', action='store_true', default=False, help='Is the output directory from nanopore')
    parser.add_argument('--climb_server', action='store_true', default="bham.covid19.climb.ac.uk", help='Climb server')
    parser.add_argument('--climb_user', action='store_true', default='climb-covid19-alikhann', help='Climb username')
    parser.add_argument('--prefix', action='store', default='QEUH', help='Prefix to search for')

    args = parser.parse_args()
    if args.verbose: 
        log.setLevel(logging.DEBUG)
        log.debug( "Executing @ %s\n"  %time.asctime())    
    main(args)
    if args.verbose: 
        log.debug("Ended @ %s\n"  %time.asctime())
        log.debug('total time in minutes: %d\n' %((time.time() - start_time) / 60.0))
