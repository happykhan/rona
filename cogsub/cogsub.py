"""
cogsub submits metadata and sequences to COG server 

Requires login for google sheets

### CHANGE LOG ### 
2020-08-17 Nabil-Fareed Alikhan <nabil@happykhan.com>
    * Initial build - split from dirty scripts
"""
from __future__ import print_function
import pickle
import os.path
import time
import argparse
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
import meta
import sys
import json 
import logging
import pprint
from marshmallow import EXCLUDE
from cogschemas import Cogmeta, CtMeta, RunMeta, LibraryBiosampleMeta, LibraryHeaderMeta
from climbfiles import ClimbFiles
from majora_util import majora_sample_exists, majora_add_samples, majora_add_run, majora_add_library
from collections import Counter

epi = "Licence: " + meta.__licence__ +  " by " +meta.__author__ + " <" +meta.__author_email__ + ">"
logging.basicConfig()
log = logging.getLogger()


def most_frequent(List): 
    occurence_count = Counter(List) 
    return occurence_count.most_common(1)[0][0] 

def get_google_metadata(valid_samples, run_name, library_name, sheet_name):
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('cogsub/credentials.json', scope)
    client = gspread.authorize(creds)

    sheet = client.open(sheet_name).sheet1
    column_position = sheet.row_values(1)
    row_position = sheet.col_values(1)    
    all_values = sheet.get_all_records()
    records_to_upload = []
    run_to_upload = {} 
    library_to_upload = {}
    maybe_blacklist = []
    cells_to_update = []
    blank_cells_to_update = []
    force = False
    library_names = []
    in_run_but_not_in_sheet = list(set(valid_samples) - set([x['central_sample_id'] for x in all_values]))
    if in_run_but_not_in_sheet:
        logging.error('missing records in metadata sheet' + '\n'.join(in_run_but_not_in_sheet))
    for x in all_values:
        
        if x.get('central_sample_id', 'burnburnburn') in valid_samples:
            for k,v in dict(x).items():
                if v == '':
                    x.pop(k)
            # Fetch required fieldnames
            # Check if run_name is consistent & library name is consistent 
            library_names.append(library_name)
            if not x.get('run_name'):
                x['run_name'] = run_name
                blank_cells_to_update.append(gspread.models.Cell(row=row_position.index(x['central_sample_id'])+1, col=column_position.index('run_name')+1, value=run_name))

            if x['run_name'] != run_name:
                logging.error('RUN NAME NOT CORRECT FOR ' + x['central_sample_id'] + ' Should be ' + run_name)
                maybe_blacklist.append(x['central_sample_id'])
                cells_to_update.append(gspread.models.Cell(row=row_position.index(x['central_sample_id'])+1, col=column_position.index('run_name')+1, value=run_name))

            if not x.get('library_name'):
                x['library_name'] = library_name
                blank_cells_to_update.append(gspread.models.Cell(row=row_position.index(x['central_sample_id'])+1, col=column_position.index('library_name')+1, value=library_name))                
            if x['library_name'] != library_name:
                logging.error('Library NAME NOT CORRECT FOR ' + x['central_sample_id'] + ' Should be ' + library_name)
                maybe_blacklist.append(x['central_sample_id'])
                cells_to_update.append(gspread.models.Cell(row=row_position.index(x['central_sample_id'])+1, col=column_position.index('library_name')+1, value=library_name))                
            record = Cogmeta(unknown = EXCLUDE).load(x)
            # Get CT info
            up_record = Cogmeta().dump(record)
            ct_values = CtMeta(unknown=EXCLUDE).load(x)

            up_record['metrics'] = dict(ct=dict(records={}))
            if len(up_record.get('patient_group', '')) > 4: 
                #if up_record['patient_group'] != up_record['central_sample_id']:
                up_record['biosample_source_id'] = up_record['patient_group']
            up_record['metrics']['ct']['records']['1'] = dict(ct_value=ct_values.get('ct_1_ct_value', 0), test_kit=ct_values.get('ct_1_test_kit'), test_platform=ct_values.get('ct_1_test_platform'), test_target=ct_values.get('ct_1_test_target'))
            up_record['metrics']['ct']['records']['2'] = dict(ct_value=ct_values.get('ct_2_ct_value', 0), test_kit=ct_values.get('ct_2_test_kit'), test_platform=ct_values.get('ct_2_test_platform'), test_target=ct_values.get('ct_2_test_target'))
            records_to_upload.append(up_record)
            run_data = RunMeta(unknown = EXCLUDE).dump(x)
            library_sample_data = LibraryBiosampleMeta(unknown = EXCLUDE).dump(x)
            library_data = LibraryHeaderMeta(unknown = EXCLUDE).dump(x)
            # Handle libraries 
            if library_to_upload.get(library_data['library_name']):
                library_to_upload[library_data['library_name']]['biosamples'].append(library_sample_data)
                run_exists = False
                for existing_run in library_to_upload[library_data['library_name']]['runs']:
                    if run_data['run_name'] == existing_run['run_name']:
                        run_exists = True
                if not run_exists:
                    library_to_upload[library_data['library_name']]['runs'].append(run_data)
            else:
                library_to_upload[library_data['library_name']] = library_data
                library_to_upload[library_data['library_name']]['biosamples'] = [library_sample_data]
                library_to_upload[library_data['library_name']]['runs'] = [run_data]

    logging.warning('You may wish to blacklist:\n' + '\n'.join(maybe_blacklist))            
    if len(run_to_upload) > 1:
        print('Multiple runs in this directory')
    run_to_upload = dict(library_name = most_frequent(library_names), runs = list(run_to_upload.values()))
    if force:
        if cells_to_update:
            print('Updating values')
            sheet.update_cells(cells_to_update)
    if blank_cells_to_update:
            print('Updating values')
            sheet.update_cells(blank_cells_to_update)        
    return records_to_upload, library_to_upload

def load_config(config="majora.json"):
    config_dict = json.load(open(config))
    return config_dict

def main(args, dry=False):
    # Load from config
    config = load_config(args.majora_token)
    output_dir = args.datadir
    run_name = args.runname
    library_name = 'NORW-' + run_name.split('_')[0]
    majora_server = config['majora_server']
    majora_username = config['majora_username']
    majora_token = config['majora_token']
    climb_file_server = config['climb_file_server']
    climb_username = config['climb_username'] 
    sheet_name = args.sheet_name
    force_sample_only = args.force_sample_only
    logging.debug(f'Dry run is {dry}')
    output_dir_bams = os.path.join(output_dir, 'ncovIllumina_sequenceAnalysis_readMapping')
    output_dir_consensus = os.path.join(output_dir, 'ncovIllumina_sequenceAnalysis_makeConsensus')
    found_samples = []
    climb_server_conn = ClimbFiles(climb_file_server, climb_username)
    # Does the run dir exist? 
    climb_run_directory = os.path.join('upload', run_name)
    climb_server_conn.create_climb_dir(climb_run_directory)
    # OPTIONAL. fetch upload list - in case only a subsample of results should be uploaded. 
    output_dir_uploadlist = os.path.join(output_dir, 'uploadlist')
    output_dir_blacklist = os.path.join(output_dir, 'blacklist')
    uploadlist = None
    blacklist = None
    if os.path.exists(output_dir_uploadlist):
        uploadlist = [x.strip() for x in open(output_dir_uploadlist).readlines()]
    if os.path.exists(output_dir_blacklist):
        blacklist = [x.strip() for x in open(output_dir_blacklist).readlines()]
    for x in os.listdir(output_dir_bams):
        if x.startswith('E') and x.endswith('sorted.bam'):
            sample_name = x.split('_')[0]
            if uploadlist: 
                if not 'NORW-' + sample_name in uploadlist:
                    continue
            if blacklist:
                if 'NORW-' + sample_name in blacklist:
                    logging.info('Skipping ' + sample_name)
                    continue
            sample_name = x.split('_')[0]
            #sample_folder = os.path.join(run_path , 'NORW-' + sample_name)
            #if os.path.exists(sample_folder):
            #    os.mkdir(sample_folder)
            sample_name = x.split('_')[0]
            bam_file = os.path.join(output_dir_bams, x)
            
            # Locate fasta file 
            fasta_file = [x for x in os.listdir(output_dir_consensus) if x.startswith(sample_name)]
            if len(fasta_file) == 1:
                fa_file_path = os.path.join(output_dir_consensus, fasta_file[0])
                # TODO make sure the sample name is valid 
                climb_sample_directory = os.path.join(climb_run_directory, 'NORW-' + sample_name)
                climb_server_conn.create_climb_dir(climb_sample_directory)
                climb_server_conn.put_file(fa_file_path, climb_sample_directory)
                climb_server_conn.put_file(bam_file, climb_sample_directory)
                found_samples.append('NORW-' + sample_name)
            elif len(fasta_file) == 0:
                logging.error('No fasta file!')
            else:
                logging.error('Multiple fasta file!')

    # Connect to google sheet. Fetch & validate metadata
    logging.debug(f'Found {len(found_samples)} samples')
    records_to_upload, library_to_upload = get_google_metadata(found_samples, run_name, library_name, sheet_name=sheet_name)

    # Connect to majora cog and sync metadata. 
    logging.debug(f'Submitting biosamples to majora ' + run_name)
    samples_dont_exist = [] 
    if force_sample_only:
        majora_add_samples(records_to_upload, majora_username, majora_token, majora_server, dry)
    else:
        for biosample in records_to_upload:
            if not majora_sample_exists(biosample['central_sample_id'], majora_username, majora_token, majora_server, dry=False):
                samples_dont_exist.append(biosample['central_sample_id'] )
        if majora_add_samples(records_to_upload, majora_username, majora_token, majora_server, dry):
            logging.debug(f'Submitted biosamples to majora')
#            if len(samples_dont_exist) > 0 :
            logging.debug(f'Submitting library and run to majora')
            for lib_val in library_to_upload.values():
                clean_lib_val = lib_val.copy()
                #clean_lib_val['biosamples'] = [x for x in clean_lib_val['biosamples'] if x['central_sample_id'] in samples_dont_exist]
                # You shouldn't touch libraries for existing samples i.e we only submit new runs. 
                if len(clean_lib_val['biosamples']) > 0 : 
                    run_to_upload = dict(library_name=lib_val['library_name'], runs = clean_lib_val.pop('runs'))
                    
                    majora_add_library(clean_lib_val, majora_username, majora_token, majora_server, dry=dry)
                    majora_add_run(run_to_upload, majora_username, majora_token, majora_server, dry=dry)
        else:
            logging.error('failed to submit samples')

   
if __name__ == '__main__':
    start_time = time.time()
    log.setLevel(logging.INFO)
    desc = __doc__.split('\n\n')[0].strip()
    parser = argparse.ArgumentParser(description=desc,epilog=epi)
    parser.add_argument ('-v', '--verbose', action='store_true', default=False, help='verbose output')
    parser.add_argument('--version', action='version', version='%(prog)s ' + meta.__version__)
    parser.add_argument('datadir', action='store', help='Location of ARTIC pipeline output')
    parser.add_argument('runname', action='store', help='Sequencing run name, must be unique')
    parser.add_argument('--gcredentials', action='store', default='credentials.json')
    parser.add_argument('--sheet_name', action='store', default='SARCOV2-Metadata')
    parser.add_argument('--majora_token', action='store', default='majora.json')
    parser.add_argument('--force_sample_only', action='store_true', default=False)
    parser.add_argument('--maindata', action='store', default='SARCOV2-Metadata')
    args = parser.parse_args()
    if args.verbose: 
        log.setLevel(logging.DEBUG)
        log.debug( "Executing @ %s\n"  %time.asctime())    
    main(args)
    if args.verbose: 
        log.debug("Ended @ %s\n"  %time.asctime())
        log.debug('total time in minutes: %d\n' %((time.time() - start_time) / 60.0))
