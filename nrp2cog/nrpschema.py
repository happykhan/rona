from marshmallow import Schema, fields, EXCLUDE, pre_load, validate
import datetime

collection_date_min = datetime.date(2020, 3, 28)

class BioMeta(Schema):
    postcode_regex = '([Gg][Ii][Rr] 0[Aa]{2})|((([A-Za-z][0-9]{1,2})|(([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})|(([A-Za-z][0-9][A-Za-z])|([A-Za-z][A-Ha-hJ-Yj-y][0-9][A-Za-z]?)))))'
    get_counties = ['BEDFORDSHIRE', 'BERKSHIRE', 'BRISTOL', 'BUCKINGHAMSHIRE',
         'CAMBRIDGESHIRE', 'CHESHIRE', 'CITY OF LONDON', 'CORNWALL',
          'COUNTY DURHAM', 'CUMBRIA', 'DERBYSHIRE', 'DEVON', 'DORSET', 'BIRMINGHAM',
           'EAST RIDING OF YORKSHIRE', 'EAST SUSSEX', 'ESSEX', 'GLOUCESTERSHIRE', 'GREATER LONDON', 'GREATER MANCHESTER',
           'HAMPSHIRE', 'HEREFORDSHIRE', 'HERTFORDSHIRE', 'ISLE OF WIGHT', 'KENT', 'LANCASHIRE', 'LEICESTERSHIRE',
           'LINCOLNSHIRE', 'MERSEYSIDE', 'NORFOLK', 'NORTH YORKSHIRE', 'NORTHAMPTONSHIRE', 'NORTHUMBERLAND', 'NOTTINGHAMSHIRE',
           'OXFORDSHIRE', 'RUTLAND', 'SHROPSHIRE','SOMERSET','SOUTH YORKSHIRE','STAFFORDSHIRE','SUFFOLK','SURREY',
           'TYNE AND WEAR','WARWICKSHIRE','WEST MIDLANDS','WEST SUSSEX','WEST YORKSHIRE','WILTSHIRE','WORCESTERSHIRE', 'MIDDLESEX']

    central_sample_id = fields.Str(data_key="COG Sample ID", required=True, validate=validate.Regexp("^NORW-[a-zA-Z0-9]{5,6}$"))
    biosample_source_id = fields.Str(data_key="NNUH Sample ID", required=True)
    adm1 = fields.Str(missing="UK-ENG")
    adm2 = fields.Str(data_key="County", validate=validate.OneOf(get_counties))
    source_age = fields.Integer(data_key="Age", validate=validate.Range(min=0, max=120))
    source_sex = fields.Str(data_key="Sex", validate=validate.OneOf(['M','F']))
    received_date = fields.Str()
    collection_date = fields.Date(data_key="Collection date", validate=lambda x: x > collection_date_min)
    sample_type_collected = fields.Str(data_key="Source", validate=validate.OneOf(["dry swab", "swab", "sputum", "aspirate"]))
    swab_site = fields.Str(data_key="Body site", validate=validate.OneOf(["nose", "throat", "nose-throat", "endotracheal", "rectal"]))
    collecting_org = fields.Str(data_key="Collecting organisation")
    library_name = fields.Str()
    library_seq_kit = fields.Str(missing='Nextera')
    library_seq_protocol = fields.Str(missing='Nextera LITE')
    library_layout_config = fields.Str(missing='PAIRED')
    library_selection = fields.Str(missing='PCR')
    library_source = fields.Str(missing='VIRAL_RNA')
    library_strategy = fields.Str(missing='AMPLICON')
    library_primers = fields.Integer(missing=3)
    library_protocol = fields.Str(missing='ARTICv2')
    run_name = fields.Str()
    previous_runs = fields.Str()
    instrument_make = fields.Str(missing='ILLUMINA')
    instrument_model = fields.Str(missing='NextSeq 500')
    adm2_private = fields.Str(data_key="Outer Postcode", validate=validate.Regexp(postcode_regex))
    date_sequenced = fields.Str()
    repeat_sample_id = fields.Str(data_key="Repeat Sample ID")
    is_surveillance = fields.Str(missing='Y')
    is_icu_patient = fields.Str(data_key="ICU admission", validate=validate.OneOf(['Y','N', 'Unknown']))
    ct_1_ct_value = fields.Str()
    ct_2_ct_value = fields.Str()

    @pre_load
    def clean_up(self, in_data, **kwargs):
        if in_data.get('Collecting organisaton'):
            in_data['Collecting organisation'] = in_data.get('Collecting organisaton')
        if in_data.get('Collecting organisaton')=='JPH':
            in_data['Collecting organisation'] = 'JPUH'
        
        for k,v in dict(in_data).items():
            if v in ['', 'to check', 'Not stated'] :
                in_data.pop(k)        
            elif k in ['County', 'Collecting organisation', 'Outer Postcode'] and v.upper() in ['NOT AVAILABLE', 'UNKNOWN', 'NA', 'NO ADDRESS', 'NO POST CODE', 'UNKOWN']:
                in_data.pop(k)
            elif k in ['Sex'] and v.upper() in ['U', 'N', 'UNKNOWN','UNKOWN']:
                in_data.pop(k)                
            elif k in ['ICU admission'] and v.upper() in ['U', 'UKNOWN', 'N/A']:       
                in_data.pop(k)         
            elif isinstance(v, str):
                    in_data[k] = v.strip()
        if in_data.get(''):
            in_data['ct_2_ct_value'] = str(in_data.get(''))
        if in_data.get('PCR Ct value',''):
            in_data['ct_1_ct_value'] = str(in_data.get('PCR Ct value'))
        if in_data.get('Sex','').lower() in ['male']:
            in_data['Sex'] = 'M'                    
        if in_data.get('Sex','').lower() in ['female']:
            in_data['Sex'] = 'F'                                
        if in_data.get('Source','').lower() in ['endotracheal aspirate', 'bronchial washings','bronchial washing']:
            in_data['Source'] = 'aspirate'
        if in_data.get("County"):
            in_data["County"] = in_data["County"].upper()
        if in_data.get("County", '').upper() in ['CAMBS', 'CAMBRIDESHIRE', 'CAMBRIDGE', 'CAMBRIDGSHIRE']:
            in_data["County"] = 'CAMBRIDGESHIRE'
        if in_data.get("County", '').upper() == 'LINC':
            in_data["County"] = 'LINCOLNSHIRE'
        if in_data.get("County", '').upper() == 'LONDON':
            in_data["County"] = 'GREATER LONDON'            
        if in_data.get("County", '').upper() == 'COLCHESTER':
            in_data["County"] = 'ESSEX'            
        if in_data.get("County", '').lower() == 'leicestshire':
            in_data["County"] = 'LEICESTERSHIRE'              
        if in_data.get("Source"):
            in_data["Source"] = in_data["Source"].lower()            
        if in_data.get('Body site'):
            if in_data.get('Body site').lower() in ['nose and throat', 'nose &throat', 'nose & troat', 'nose & throat', 'throat/nose', 'nose/throat']:
                in_data['Body site'] = 'nose-throat'
            elif in_data.get('Body site').lower() in ['lung', "tracheostomy"]:
                in_data['Body site'] = 'endotracheal'
            elif in_data.get('Body site').lower() in ['mouth', 'throat/swab']:
                in_data['Body site'] = 'throat'                
            else:
                in_data['Body site'] = in_data.get('Body site').lower()
        if in_data.get('ICU admission', '').lower() in ['yes']:
            in_data['ICU admission'] = 'Y'
        if in_data.get('ICU admission', '').lower() in ['no']:
            in_data['ICU admission'] = 'N'   
        if in_data.get('Collected by QIB'): 
            in_data["received_date"] = self.handle_dates(in_data['Collected by QIB'])
        if  in_data.get('Collection date'):
            in_data['Collection date'] = self.handle_dates(in_data['Collection date'])            
        elif not in_data.get("received_date"):
            in_data["received_date"] = datetime.datetime.now().strftime('%Y-%m-%d')
        return in_data

    def handle_dates(self, date_string):
        try:
            datetime.datetime.strptime(date_string, '%Y-%m-%d')
            # String is fine, return itself. 
            return date_string
        except ValueError:
            try:
                datetime_obj = datetime.datetime.strptime(date_string, '%d/%m/%Y')
                return datetime_obj.strftime('%Y-%m-%d')
            except ValueError:
                try:
                    datetime_obj = datetime.datetime.strptime(date_string, '%d.%m.%Y')
                    return datetime_obj.strftime('%Y-%m-%d')
                except ValueError:
                    raise


class CtMeta(Schema):
    ct_1_ct_value = fields.Float(validate=validate.Range(min=0, max=2000))
    ct_1_test_kit = fields.Str(validate=validate.OneOf(["ALTONA", "ABBOTT", "AUSDIAGNOSTICS", "BOSPHORE", "ROCHE", "INHOUSE", "SEEGENE", "VIASURE", "BD", "XPERT"]))
    ct_1_test_platform = fields.Str(validate=validate.OneOf(["ALTOSTAR_AM16", "ABBOTT_M2000", "APPLIED_BIO_7500", "ROCHE_COBAS", "ROCHE_FLOW", "ROCHE_LIGHTCYCLER", "ELITE_INGENIUS", "CEPHEID_XPERT", "QIASTAT_DX", "AUSDIAGNOSTICS", "INHOUSE", "ALTONA", "PANTHER", "SEEGENE_NIMBUS", "QIAGEN_ROTORGENE", "BD_MAX"]))
    ct_1_test_target = fields.Str(validate=validate.OneOf(["E", "N", "S", "RDRP", "ORF1AB", "ORF8", 'RDRP+N']))
    ct_2_ct_value = fields.Float(validate=validate.Range(min=0, max=2000))
    ct_2_test_kit = fields.Str(validate=validate.OneOf(["ALTONA", "ABBOTT", "AUSDIAGNOSTICS", "BOSPHORE", "ROCHE", "INHOUSE", "SEEGENE", "VIASURE", "BD", "XPERT"]))
    ct_2_test_platform = fields.Str(validate=validate.OneOf(["ALTOSTAR_AM16", "ABBOTT_M2000", "APPLIED_BIO_7500", "ROCHE_COBAS", "ROCHE_FLOW", "ROCHE_LIGHTCYCLER", "ELITE_INGENIUS", "CEPHEID_XPERT", "QIASTAT_DX", "AUSDIAGNOSTICS", "INHOUSE", "ALTONA", "PANTHER", "SEEGENE_NIMBUS", "QIAGEN_ROTORGENE", "BD_MAX"]))
    ct_2_test_target = fields.Str(validate=validate.OneOf(["E", "N", "S", "RDRP", "ORF1AB", "ORF8", "RDRP+N"]))

    @pre_load
    def clean_up(self, in_data, **kwargs):
        for k,v in dict(in_data).items():
            if v in ['', '-', 'Unknown', 'To check',  '#VALUE!', '-', 'N/A', "NEGATIVE", "negative", 'Not recorded', 'unknown', 'NOT STATED'] :
                in_data.pop(k)       
            elif isinstance(v, str):
                    in_data[k] = v.upper().strip()
        if in_data.get('ct_1_test_platform'):
            if in_data.get('ct_1_test_platform').upper() in ['HOLOGIC PANTHER']:
                in_data['ct_1_test_platform'] = 'PANTHER'               
            if in_data.get('ct_1_test_platform').upper() == 'ROCHE COBAS 8800':
                in_data['ct_1_test_platform'] = 'ROCHE_COBAS'   
            if in_data.get('ct_1_test_platform').upper() in  ['APPLIED BIOSYSTEMS QUANTSTUDIO 5', 'APPLIED BIOSYSTEMS QUANTSTUDIO 7']:
                in_data['ct_1_test_platform'] = 'APPLIED_BIO_7500'        
            if in_data.get('ct_1_test_platform').upper() == 'ROCHE LIGHTCYCLER LC480II':
                in_data['ct_1_test_platform'] = 'ROCHE_LIGHTCYCLER'           
            if in_data.get('ct_1_test_platform').upper() == 'CEPHEID GENEXPERT':
                in_data['ct_1_test_platform'] = 'CEPHEID_XPERT'                                                                         
        if in_data.get('ct_2_test_platform'):               
            if in_data.get('ct_2_test_platform').upper() == 'HOLOGIC PANTHER':
                in_data['ct_2_test_platform'] = 'PANTHER'                            
            if in_data.get('ct_2_test_platform').upper() == 'ROCHE COBAS 8800':
                in_data['ct_2_test_platform'] = 'ROCHE_COBAS'            
            if in_data.get('ct_2_test_platform').upper() == 'APPLIED BIOSYSTEMS QUANTSTUDIO 5':
                in_data['ct_2_test_platform'] = 'APPLIED_BIO_7500'                     
            if in_data.get('ct_2_test_platform').upper() == 'ROCHE LIGHTCYCLER LC480II':
                in_data['ct_2_test_platform'] = 'ROCHE_LIGHTCYCLER'
            if in_data.get('ct_2_test_platform').upper() == 'CEPHEID GENEXPERT':
                in_data['ct_2_test_platform'] = 'CEPHEID_XPERT'                

        if in_data.get('ct_2_test_kit'):
            if in_data['ct_2_test_kit'] == 'SARS-COV2, INFLUENZA + RSA (AUXDX) KIT':
                in_data['ct_2_test_kit'] = 'AUSDIAGNOSTICS'
            if in_data['ct_2_test_kit'] == 'REAL STAR SARS-COV-2 RT-PCR VERSION 1':
                in_data['ct_2_test_kit'] = 'ALTONA'              
            if in_data['ct_2_test_kit'] in ['SARS-COV2 TEST','APTIMA® SARS-COV-2 ASSAY', 'PANTHER FUSION® SARS-COV-2 ASSAY', '2019-NCOV CDC ASSAY']:
                in_data['ct_2_test_kit'] = 'ROCHE'  
            if in_data['ct_2_test_kit'] in ['XPERT® XPRESS SARS-COV-2 (CEPHEID) KIT']:
                in_data['ct_2_test_kit'] = 'XPERT'                                                                                     
        if in_data.get('ct_1_test_kit'):
            if in_data['ct_1_test_kit'] == 'SARS-COV2, INFLUENZA + RSA (AUXDX) KIT':
                in_data['ct_1_test_kit'] = 'AUSDIAGNOSTICS'       
            if in_data['ct_1_test_kit'] == 'REAL STAR SARS-COV-2 RT-PCR VERSION 1':
                in_data['ct_1_test_kit'] = 'ALTONA'         
            if in_data['ct_1_test_kit'] in ['SARS-COV2 TEST','APTIMA® SARS-COV-2 ASSAY', 'PANTHER FUSION® SARS-COV-2 ASSAY','2019-NCOV CDC ASSAY']:
                in_data['ct_1_test_kit'] = 'ROCHE'         
            if in_data['ct_1_test_kit'] in ['XPERT® XPRESS SARS-COV-2 (CEPHEID) KIT']:
                in_data['ct_1_test_kit'] = 'XPERT'                                                         
        if in_data.get('ct_2_test_target'):
            if in_data['ct_2_test_target'] in ['ORF2', 'S-GENE', 'S-GENE (COV2 SPECIFIC)']:
                in_data['ct_2_test_target'] = 'S'            
            if in_data['ct_2_test_target'] in ['ORF1AB REGION 1', 'ORF1AB REGION 2','ORF1', "ORF1A/B"]:
                in_data['ct_2_test_target'] = 'ORF1AB'      
            if in_data['ct_2_test_target'] in ['E GENE', 'E-GENE (BETA-CORONAVIRUS TARGET)']:
                in_data['ct_2_test_target'] = 'E'      
            if in_data['ct_2_test_target'] in ['N1', "N2"]:
                in_data['ct_2_test_target'] = 'N'                                                              
            if in_data['ct_2_test_target'] in ['RP']:
                in_data['ct_2_test_target'] = 'RDRP'                                
        if in_data.get('ct_1_test_target'):
            if in_data['ct_1_test_target'] in ['RP']:
                in_data['ct_1_test_target'] = 'RDRP'                
            if in_data['ct_1_test_target'] in ['ORF2', 'S-GENE', 'S-GENE (COV2 SPECIFIC)']:
                in_data['ct_1_test_target'] = 'S'    
            if in_data['ct_1_test_target'] in ['ORF1AB REGION 1','ORF1AB REGION 2', 'ORF1', "ORF1A/B"]:
                in_data['ct_1_test_target'] = 'ORF1AB'                         
            if in_data['ct_1_test_target'] in ['E GENE', 'E-GENE (BETA-CORONAVIRUS TARGET)']:
                in_data['ct_1_test_target'] = 'E'                
            if in_data['ct_1_test_target'] in ['N1', "N2"]:
                in_data['ct_1_test_target'] = 'N'                                              
        return in_data

class lineageMeta(Schema):
    uk_lineage = fields.Str(data_key='peroba_uk_lineage')
    lineage = fields.Str(data_key='peroba_lineage')
    phylotype = fields.Str(data_key='peroba_phylotype')
    special_lineage = fields.Str(data_key='peroba_special_lineage')

    @pre_load
    def clean_up(self, in_data, **kwargs):
        for k,v in dict(in_data).items():
            if v in [''] :
                in_data.pop(k)        
            elif isinstance(v, str):
                    in_data[k] = v.strip()
        return in_data
