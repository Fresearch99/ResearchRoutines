# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 10/5/2020
METHOD: Imports Full Text Claim Extractions from Alice_Training_Claim_Text_Extraction
        and build NLP classification for patent claims, use for import to classification
        routine
    VERSION 2: Restrict to pure Alice Rejections;
        use optimization results from Alice NLP validation;
        balance control panel based on relative frequency of filing year + uspc class
    VERSION 3: Save visualization; Word Cloud creation for model data
    VERSION 4: Include main classes of Alice cases
    VERSION 5: Control for app_id and pgpub_number, include linearSVC
    VERSION 6: use app_id as integer, allow for various models to be trained
        Subversion 6.1: oversampling in control training data
        Subversion 6.2: Use more default settings for NLP model building
    VERSION 7: Include possibility of using PatentsViews Claim texts for training
                and drop non-unique claim text
        Subversion 7.1: Import new set of claim extraction data
        Subversion 7.2: Request method with length check and no streaming
        Subversion 7.3: Method Building for variations of Bilski, Mayo, Myriad, and Alice => not useful, Alice - 705 dominate
        Subsubverison 7.3.1: Update url & dataset names and submission routine to Google Cloud
        Subversion 7.4: Include in main NLP model for one ucsp class specifically (705 only)
        Subversion 7.5 (DATE 3/11/2022): Use PatentsView Pre-grant Application claim publication for training
"""


r'''
# Execution on hpc.haastech.org
#!/usr/bin/bash
#BSUB -n 1
#BSUB -e batch_output_directory/%J.err
#BSUB -o batch_output_directory/%J.out
# cd run _folder
# execute program
source activate py38
/apps/anaconda3/bin/python Alice_NLP_classification_model_build_v7.5.py

#----------------------------
bsub <Alice_NLP_classification_model_build_v7.5.sh

r'''



#######################################################
#   Load Environment
#######################################################

import pandas as pd
import numpy as np
import re
import os

#-----------------------------------
#!!! For local execution, change working directory to where the ''Alice_Claim_Extraction_v' + str(INPUT_VERSION)' is located
#local_dir = r'G:\My Drive\Preliminary Research\Alice and Innovation Project\Alice Claim and NLP Modeling'
#os.chdir(local_dir)
#-----------------------------------

import pickle

import requests
from io import BytesIO
import zipfile

import multiprocessing as mp

import wordcloud
import matplotlib.pyplot as plt

# Set seed
RANDOM_SEED = 42

# Version
VERSION = 7.5

# Input verison of Alice_Training_Claim_Text_Extraction
INPUT_VERSION = 8

# how many classes should be included in the training dataset
TOP_NCLASSES = 4

# Number or cores
CORES = mp.cpu_count()

r'''
pd.set_option('display.max_rows', 400)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 100)
r'''
#####################################
# Training Data Import              #
#####################################
def training_data_import(nclasses=4,
                         home_directory=os.getcwd(),
                         specified_uspc_class=['705'],
                         use_specified_uspc_class=False,
                         text_source='Alice_Claim_Extraction_v' + str(INPUT_VERSION),
                         replacement=False,
                         PatentsView_Control_claims=False
                         ):
    r'''
    METHOD: Import data for model training and validations

    INPUT:  - nclasses: int, the top n uspc classes of Alice treated claims to be used
            - Home directory containing text source subfolder with results from
                full text claim extraction (Alice_Training_Claim_Text_Extraction_v4.py)
            - text_source: tDirectory of full text claim extraction
            - specified_uspc_class: if specify uspc class for data selection, use this list of strings
            - use_specified_uspc_class: bool if should restrict to one particular class (overrides nclasses)
            - replacement: bool on whether to use drawing with replacement from control claims,
            - PatentsView_Control_claims: bool if the PatentsView claim should be used as control
    OUTPUT: - training_data: df with application ID, full text, and binary treated variable
            - mainclasses: list of integers of main classes for classification
    r'''
    # => See for coercion and typing decision Alice_Training_Claim_Text_Extraction_v6
    # home_directory = r'C:\Users\domin\Google Drive\Preliminary Research\Alice and Innovation Project\Alice Claim and NLP Modeling\Environment Data'
    #############################
    # Import files              #
    #############################


    #===================================================
    # Load Claims
    # home_directory = r'C:\Users\domin\Google Drive\Preliminary Research\Alice and Innovation Project\Alice Claim and NLP Modeling\Environment Data'
    # os.chdir(home_directory)

    # text_source = r"C:\Users\domin\Desktop\Alice_Claim_Extraction_v8"
    text_documents = os.listdir(text_source)

    Alice_claims_files = [f for f in text_documents if \
                          bool(re.search('_Alice_v' + str(INPUT_VERSION), f)) & \
                          ~bool(re.search('Bilski', f)) &  \
                          ~bool(re.search('ControlPatents', f))]

    Alice_claims = pd.DataFrame()
    for claim_file in Alice_claims_files:
        Alice_claims = pd.concat([Alice_claims, pd.read_csv(text_source + '//' + claim_file,
                                                                            encoding='utf-8',
                                                                            low_memory=False)], \
                                 axis = 0, ignore_index = True)

    r'''
    intersecting = pd.merge(Alice_claims_7[['app_id', 'pgpub_number', 'claim_text']],
                             Alice_claims_6[['app_id', 'pgpub_number', 'claim_text']],
                             how='inner')

    Alice_claims_6 = Alice_claims
    Alice_claims_7 = Alice_claims
    alice_rejections[alice_condition].app_id
    Alice_claims_7[~(Alice_claims_7.app_id.isin(list(Alice_claims_6.app_id))) &
                   (Alice_claims_7.app_id.isin(list(alice_rejections[alice_condition].app_id)))]['pgpub_date'].value_counts()

    Alice_claims_6[~(Alice_claims_6.app_id.isin(list(Alice_claims_7.app_id))) &
                   (Alice_claims_6.app_id.isin(list(alice_rejections[alice_condition].app_id)))]['pgpub_date'].value_counts()


    #2013-10-17    179
    #2013-05-02    123
    #2013-08-01    121
    #2013-05-23    120
    #2013-12-05    119

    not_found_search_ids = list(Alice_claims_6[~(Alice_claims_6.app_id.isin(list(Alice_claims_7.app_id))) &
                                               (Alice_claims_6.app_id.isin(list(alice_rejections[alice_condition].app_id))) &
                                               (Alice_claims_6.pgpub_date=='2013-05-02')].app_id)

    set(alice_rejections.app_id_int)
    set(not_found_search_ids).difference(set(alice_rejections.app_id_int))



    found_in_7 = list(Alice_claims_7[Alice_claims_7.app_id.isin(list(alice_rejections[alice_condition].app_id))].app_id.unique())
    Alice_claims_6[~Alice_claims_6.app_id.isin(list(Alice_claims_7.app_id))]
    found_in_6 = Alice_claims_6[Alice_claims_6.app_id.isin(list(alice_rejections[alice_condition].app_id))].app_id.unique()

    Alice_claims_7[Alice_claims_7.app_id.astype(int)==app_id_search]
    Alice_claims_6[Alice_claims_6.app_id.astype(int)==app_id_search]

    set(found_in_6).difference(set(found_in_7))
    len(Alice_claims_7) - len(intersecting)
    Alice_claims_7[~Alice_claims_7.app_id.isin(list(intersecting.app_id))]
    r'''
    #home_directory = r"C:\Users\domin\Desktop"
    #os.chdir(home_directory)
    #========================================
    # Import rejections, office action, and application data from USPTO

    #----------------------------------
    # Application Data
    #----------------------------------
    # !!! only the 2017 vintage has the application status codes that are easy to use in this verison (office action dataset also ends in 2017)
    if ('application_data_2017.csv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        application_data = pd.read_csv('application_data_2017.csv', low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from economic research dataset

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://bulkdata.uspto.gov/data/patent/pair/economics/2017/application_data.csv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'application_data_2017.csv'
        z.extract(z.infolist()[0])

        application_data = pd.read_csv(z.open(z.infolist()[0]), low_memory=False)

    #----------------------------------
    # Rejection Data
    #----------------------------------
    if ('rejections_uspto_research_2017.csv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        rejections = pd.read_csv('rejections_uspto_research_2017.csv', low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load rejection and office data

        for request_attempt in range(5):
            r = requests.get(r"https://bulkdata.uspto.gov/data/patent/office/actions/bigdata/2017/rejections.csv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'rejections_uspto_research_2017.csv'
        z.extract(z.infolist()[0])

        #z = zipfile.ZipFile(BytesIO(r.content))
        #z.extractall()

        rejections = pd.read_csv(z.open(z.infolist()[0]), low_memory=False)

    #----------------------------------
    # Office Actions Data
    #----------------------------------
    if ('office_actions_uspto_research_2017.csv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        office_actions = pd.read_csv('office_actions_uspto_research_2017.csv', low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load rejection and office data

        for request_attempt in range(5):
            r = requests.get(r"https://bulkdata.uspto.gov/data/patent/office/actions/bigdata/2017/office_actions.csv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'office_actions_uspto_research_2017.csv'
        z.extract(z.infolist()[0])

        #z = zipfile.ZipFile(BytesIO(r.content))
        #z.extractall()

        office_actions = pd.read_csv(z.open(z.infolist()[0]), low_memory=False)


    #####################################
    # Construct training dataset        #
    #####################################

    office_actions['ifw_number'] = office_actions.ifw_number.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    rejections['ifw_number'] = rejections.ifw_number.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    rejections['app_id'] = pd.to_numeric(rejections.app_id, downcast = 'integer', errors = 'coerce')
    office_actions['app_id'] = pd.to_numeric(office_actions.app_id, downcast = 'integer', errors = 'coerce')
    # => See Alice_Training_Claim_Text_Extraction_v6: all relevant ids are integer

    # Office action data
    alice_rejections = pd.merge(office_actions,
                                rejections[rejections.alice_in == 1],
                                how = 'inner',
                                on = ['ifw_number', 'app_id']) # => app_id not needed, but avoids duplicates columns

    print('\t\t Number of Alice Rejections Raw %.0f' % len(alice_rejections), flush=True)
    #====================================
    # Limit to cases with clear Alice identification
    #====================================
    # Source: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3024621
    #         https://www.uspto.gov/sites/default/files/documents/Variable%20tables_v20171120.pdf
    # - Exclude mismatches between paragraph and action sentence
    # - Exclude rejection based on lack of novelty, 102
    # - Exclude rejection based on obviousness, 103
    # - Exclude rejections based on does not meet requirements
    #   regarding the adequacy of the disclosure of the invention, 112
    # - Exclude double patenting rejections
    alice_condition = (alice_rejections.rejection_fp_mismatch != 1) & \
        (alice_rejections.rejection_102 != 1) & \
        (alice_rejections.rejection_103 != 1) & \
        (alice_rejections.rejection_112 != 1) & \
        (alice_rejections.rejection_dp != 1)

    print('\t\t Number of Alice Rejections with no other injections %.0f' % len(alice_rejections[alice_condition]), flush=True)
    print('\t\t Number of unique application ids with Alice Rejections with no other injections %.0f' % len(alice_rejections[alice_condition].app_id.unique()), flush=True)

    r'''
    # See what classes there are for the different rejection classes

    cleaned_rejections = alice_rejections[alice_condition]
    cleaned_rejections[
        (cleaned_rejections.alice_in==1) & \
        (cleaned_rejections.bilski_in==0) & \
        (cleaned_rejections.mayo_in==0) & \
        (cleaned_rejections.myriad_in==0)
        #].uspc_class.value_counts(normalize=True).cumsum().head(10)
        ].uspc_class.value_counts().head(10)
        #].art_unit.astype(str).apply(lambda x: x[0:2]).value_counts().head(10)


    705    0.576761
    463    0.690235
    702    0.750433
    000    0.790482
    709    0.812979
    701    0.834611
    434    0.855377
    716    0.869592
    708    0.881582
    704    0.893078

    705    4666
    463     918
    702     487
    000     324
    709     182
    701     175
    434     168
    716     115
    708      97
    704      93

    cleaned_rejections[
        (cleaned_rejections.alice_in==1) |
        (cleaned_rejections.bilski_in==1) |
        (cleaned_rejections.mayo_in==1)
        #].uspc_class.value_counts(normalize=True).cumsum().head(10)
        ].uspc_class.value_counts(normalize=True).head(10)
        #].uspc_class.value_counts().head(10)
        #].art_unit.astype(str).apply(lambda x: x[0:2]).value_counts().head(10)

    705    0.469460 => DATA PROCESSING: FINANCIAL, BUSINESS PRACTICE, MANAGEMENT, OR COST/PRICE DETERMINATION
    463    0.557959 => AMUSEMENT DEVICES: GAMES
    702    0.611257 => DATA PROCESSING: MEASURING, CALIBRATING, OR TESTING
    435    0.662203 => CHEMISTRY: MOLECULAR BIOLOGY AND MICROBIOLOGY
    000    0.696679
    716    0.726722 => COMPUTER-AIDED DESIGN AND ANALYSIS OF CIRCUITS AND SEMICONDUCTOR MASKS
    701    0.751154 => DATA PROCESSING: VEHICLES, NAVIGATION, AND RELATIVE LOCATION
    709    0.772962 => ELECTRICAL COMPUTERS AND DIGITAL PROCESSING SYSTEMS: MULTICOMPUTER DATA TRANSFERRING
    382    0.793593 => IMAGE ANALYSIS
    434    0.810153 => EDUCATION AND DEMONSTRATION

    705    0.469460
    463    0.088499
    702    0.053298
    435    0.050946
    000    0.034477
    716    0.030043
    701    0.024432
    709    0.021808
    382    0.020632
    434    0.016560

    705    5188
    463     978
    702     589
    435     563
    000     381
    716     332
    701     270
    709     241
    382     228
    434     183

    cleaned_rejections[
        (cleaned_rejections.alice_in==0) & \
        (cleaned_rejections.bilski_in==1) & \
        (cleaned_rejections.mayo_in==0) & \
        (cleaned_rejections.myriad_in==0)
        #].uspc_class.value_counts(normalize=True).cumsum().head(10)
        ].uspc_class.value_counts().head(10)
    705    0.150071
    716    0.253454
    382    0.337303
    435    0.421153
    701    0.463554
    713    0.504050
    370    0.543592
    708    0.578847
    702    0.614102
    273    0.644116

    705    315
    716    217
    382    176
    435    176
    701     89
    713     85
    370     83
    708     74
    702     74
    273     63

    cleaned_rejections[
        (cleaned_rejections.alice_in==0) & \
        (cleaned_rejections.bilski_in==0) & \
        (cleaned_rejections.mayo_in==1) & \
        (cleaned_rejections.myriad_in==0)
        #].uspc_class.value_counts(normalize=True).cumsum().head(10)
        ].uspc_class.value_counts().head(10)
    435    0.377030
    705    0.617169
    424    0.729698
    514    0.799304
    702    0.831787
    000    0.864269
    436    0.888631
    506    0.906032
    600    0.918794
    463    0.929234

    435    325
    705    207
    424     97
    514     60
    702     28
    000     28
    436     21
    506     15
    600     11
    463      9

    cleaned_rejections[
        (cleaned_rejections.alice_in==0) & \
        (cleaned_rejections.bilski_in==0) & \
        (cleaned_rejections.mayo_in==0) & \
        (cleaned_rejections.myriad_in==1)
       # ].uspc_class.value_counts().head(10)
        ].uspc_class.value_counts(normalize=True).cumsum().head(10)
    435    0.387363
    424    0.568681
    536    0.695055
    514    0.810440
    530    0.859890
    800    0.909341
    426    0.925824
    000    0.939560
    506    0.950549
    382    0.958791

    435    141
    424     66
    536     46
    514     42
    530     18
    800     18
    426      6
    000      5
    506      4
    382      3

    cleaned_rejections[
        (cleaned_rejections.myriad_in==1) |
        (cleaned_rejections.mayo_in==1)
        #].uspc_class.value_counts(normalize=True).cumsum().head(10)
        ].uspc_class.value_counts().head(10)
        #].art_unit.astype(str).apply(lambda x: x[0:2]).value_counts().head(10)

    435    466
    705    209
    424    163
    514    102
    536     52
    000     33
    702     30
    436     22
    530     22
    800     22

    cleaned_rejections.alice_in.value_counts()
    0    76900
    1     8090
    cleaned_rejections.bilski_in.value_counts()
    0    82891
    1     2099
    cleaned_rejections.mayo_in.value_counts()
    0    84128
    1      862

    # => Alice is dominating, other cases don't contribute too much to
    # => Class 705 dominates
    r'''
    #====================================
    r'''
    # In version 5, a lot of IDs are still missing, search here why
    Alice_claims['app_id'] = pd.to_numeric(Alice_claims.app_id, downcast = 'integer', errors = 'coerce')


    no_claim_extracted = list(np.setdiff1d(list(alice_rejections[alice_condition]['app_id']), list(Alice_claims['app_id'])))
    application_data['app_id'] = pd.to_numeric(application_data.application_number,
                                                   downcast = 'integer', errors = 'coerce')
    application_data[application_data.app_id.isin(no_claim_extracted)].earliest_pgpub_date.isnull().value_counts()
    #False    308
    #True     194
    application_data[application_data.app_id.isin(no_claim_extracted)].earliest_pgpub_date.value_counts()
    #2009-11-12    14
    #2009-12-31    12
    #2009-12-03    12
    #2009-12-10    12
    #2009-08-20    10
    # => Look at the early december 2009 publication, using the Alice_Training_Claim_Text_Extraction for expalantion
    sublist_not_found = application_data[(application_data.app_id.isin(no_claim_extracted)) & (application_data.earliest_pgpub_date=='2009-12-03')].app_id
    str_sublist = [str(s).strip() for s in sublist_not_found]
    int_sublist = [int(s) for s in sublist_not_found]
    len(np.setdiff1d(list(sublist_not_found), list(doc_number)))
    len(np.setdiff1d(list(str_sublist), list(doc_number)))
    len(np.setdiff1d(list(int_sublist), list(doc_number)))
    # => Issue with decimal, but this is not the reason why it can't be found. Reitterate Alice_Training
    r'''
    # Merge with claim fulltext
    alice_text_rejections = pd.merge(alice_rejections[alice_condition],
                                     Alice_claims,
                                     how = 'inner',
                                     on = 'app_id')


    # Filter out observations with claims being mentioned as rejected
    alice_text_rejections['affected_claim'] = alice_text_rejections.apply(lambda row: str(row['claim_int']).split('.')[0] in row['claim_numbers'].split(','), axis = 1)
    #alice_text_rejections['affected_claim2'] = alice_text_rejections.\
    #    apply(lambda row: str(row['claim_int']).split('.')[0].strip() in [str(s).strip() for s in row['claim_numbers'].split(',')], axis = 1)
    #alice_text_rejections[alice_text_rejections['affected_claim']!=alice_text_rejections['affected_claim2']]
    # => same result without stripping
    
    #alice_text_rejections[alice_text_rejections['affected_claim']==False]

    alice_treated = alice_text_rejections[alice_text_rejections['affected_claim']].copy()
    alice_treated = alice_treated.drop(['rejection_101','alice_in', 'bilski_in', 'mayo_in',
                                        'myriad_in', 'dep_reference', 'affected_claim',
                                        'uspc_class', 'uspc_subclass'], axis = 1)

    print('\t\t Number of Alice Treated independent claims %.0f' % len(alice_treated), flush=True)
    print('\t\t Number of unique application ids with Alice Treated independent claims %.0f' % len(alice_treated.app_id.unique()), flush=True)
    #--------------------------------------
    # Merge with application data
    application_data['app_id'] = pd.to_numeric(application_data.application_number,
                                                   downcast = 'integer', errors = 'coerce')


    alice_application_treated = pd.merge(alice_treated,
                                         application_data,
                                         how = 'inner',
                                         on = 'app_id')


    #----------------------------------------
    # Control for pg-publication number to be correct
    alice_application_treated['pgpub_number'] = alice_application_treated.pgpub_number.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    alice_application_treated['earliest_pgpub_number_cleaned'] = alice_application_treated.earliest_pgpub_number.astype(str). \
        apply(lambda x: re.sub(r'^US', '', x)).apply(lambda x: re.sub(r'[a-zA-Z]{1,1}\d{0,1}$', '', x))

    publication_condition = (alice_application_treated.pgpub_number == alice_application_treated.earliest_pgpub_number_cleaned) | \
                            (alice_application_treated.pgpub_number == '')

    alice_application_treated = alice_application_treated[publication_condition]
    # alice_application_treated[~publication_condition][['pgpub_number', 'earliest_pgpub_number_cleaned']]
    print('\t\t Number of treated claims from the right pre-grant publication document %.0f' % len(alice_application_treated), flush=True)
    #----------------------------------------

    #--------------------------------------
    alice_application_treated['appl_status_code'] = pd.to_numeric(alice_application_treated.appl_status_code,
                                                                  errors='coerce', downcast='integer')
    alice_application_treated.appl_status_code.value_counts().head(10)
    # 150.0  => Patented Case
    # 161.0  => Abandoned -- Failure to Respond to an Office Action
    # 124.0  => On Appeal -- Awaiting Decision by the Board of Appeals
    # 41.0   => Non Final Action Mailed
    # 163.0  => Abandoned --
    # 61.0   => Final Rejection Mailed
    # 30.0   => Docketed New Case - Ready for Examination
    # 93.0   => Notice of Allowance Mailed -- Application Received in Office of Publications
    # 71.0   => Response to Non-Final Office Action Entered and Forwarded to Examiner
    # 120.0  => Notice of Appeal Filed

    # Filter for out final rejections and abandonment
    type_condition = (alice_application_treated['appl_status_code'].isin([161, 163, 61]))

    alice_application_treated = alice_application_treated[type_condition]
    print('\t\t Number of treated claims from abandoned application status %.0f' % len(alice_application_treated), flush=True)

    #--------------------------------------
    # Restrict to reasonable dates
    alice_application_treated['filing_date_dt'] = pd.to_datetime(alice_application_treated.filing_date, errors='coerce')
    alice_application_treated['mail_dt_dt'] = pd.to_datetime(alice_application_treated.mail_dt, errors='coerce')
    alice_application_treated['appl_status_date_dt'] = pd.to_datetime(alice_application_treated.appl_status_date, errors='coerce')
    alice_application_treated['earliest_pgpub_date_dt'] = pd.to_datetime(alice_application_treated.earliest_pgpub_date, errors='coerce')

    date_condition = (alice_application_treated['mail_dt_dt'] > alice_application_treated['filing_date_dt']) & \
                        (alice_application_treated['appl_status_date_dt'] > alice_application_treated['mail_dt_dt']) & \
                            (alice_application_treated['earliest_pgpub_date_dt'] > alice_application_treated['filing_date_dt'])

    alice_application_treated = alice_application_treated[date_condition]
    print('\t\t Number of treated claims purged for illogical dates %.0f' % len(alice_application_treated), flush=True)
    #-----------------------------
    # Remove cancelled claims
    cancelled_condition = alice_application_treated.claim_text.\
            apply(lambda x: not(bool(re.search(r'canceled', re.sub('[^A-Za-z]','', x))) & bool(len(re.sub('[^A-Za-z]','', x)) < 20)))

    alice_application_treated = alice_application_treated[cancelled_condition]
    # alice_application_treated.claim_text.value_counts().head(10)
    print('\t\t Number of uncancelled treated claims %.0f' % len(alice_application_treated), flush=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    if PatentsView_Control_claims==True:
        print('\t Use for control claim construction the PatentsView claim texts', flush=True)
        #======================================
        # Control Claims using Application Extraction
        #======================================

        # Load Control claims
        text_documents = os.listdir(text_source)
        Alice_PatentsView_control_claims_files = [f for f in text_documents if \
                                                  bool(re.search('_Alice_v' + str(INPUT_VERSION), f)) & \
                                                      bool(re.search('ControlPatents', f)) & \
                                                        ~bool(re.search('Bilski', f)) &  \
                                                          ~bool(re.search('PatentsView_PregrantApp', f))]

        Alice_PatentsView_control_claims = pd.DataFrame()
        for claim_file in Alice_PatentsView_control_claims_files:
            Alice_PatentsView_control_claims = pd.concat([Alice_PatentsView_control_claims,
                                                          pd.read_csv(text_source + '//' + claim_file,
                                                                      encoding='utf-8',
                                                                      low_memory=False)], \
                                             axis = 0, ignore_index = True)

        # Use patent number that are integers for utility patents
        Alice_PatentsView_control_claims['patent_num'] = pd.to_numeric(Alice_PatentsView_control_claims.patent_id, \
                                                                       downcast = 'integer', errors = 'coerce')
        application_data['patent_num'] = pd.to_numeric(application_data.patent_number, \
                                                       downcast = 'integer', errors = 'coerce')

        alice_PatentsView_text_controls = pd.merge(application_data,
                                                   Alice_PatentsView_control_claims,
                                                   how = 'inner',
                                                   on = 'patent_num')

        # Already controlled for being patented cases and no office actions being associated
        #------------------------------------
        # Rename claim text
        alice_text_controls = alice_PatentsView_text_controls.rename(columns={'text':'claim_text'})
        #cancelled_condition = alice_PatentsView_text_controls.claim_text.\
        #    apply(lambda x: not(bool(re.search(r'canceled', re.sub('[^A-Za-z]','', x))) & bool(len(re.sub('[^A-Za-z]','', x)) < 20)))
        # cancelled_condition.value_counts()
        # True    1228449

        # alice_text_controls.claim_text.value_counts().head(10)
        print('\t\t Number of control claims from PatentsView %.0f' % len(alice_PatentsView_text_controls), flush=True)

        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    else:
        print('\t Use for control claim construction the application claim texts', flush=True)

        # Load Control claims
        text_documents = os.listdir(text_source)
        Alice_ApplicationFile_control_claims_files = [f for f in text_documents if \
                                                      bool(re.search('_Alice_v' + str(INPUT_VERSION), f)) & \
                                                          bool(re.search('ControlPatents', f)) & \
                                                            ~bool(re.search('Bilski', f)) &  \
                                                              bool(re.search('PatentsView_PregrantApp', f))]

        Alice_ApplicationFile_control_claims = pd.DataFrame()
        for claim_file in Alice_ApplicationFile_control_claims_files:
            Alice_ApplicationFile_control_claims = pd.concat([Alice_ApplicationFile_control_claims,
                                                              pd.read_csv(text_source + '//' + claim_file,
                                                                          encoding='utf-8',
                                                                          low_memory=False)], \
                                                             axis = 0, ignore_index = True)


        Alice_ApplicationFile_control_claims['app_id'] = pd.to_numeric(Alice_ApplicationFile_control_claims.app_id, \
                                                       downcast = 'integer', errors = 'coerce')

        alice_ApplicationFile_text_controls = pd.merge(application_data,
                                                       Alice_ApplicationFile_control_claims,
                                                       how = 'inner',
                                                       on = 'app_id')

        # Already controlled for being patented cases and no office actions being associated
        print('\t\t Number of raw control claims from Application Files %.0f' % len(alice_ApplicationFile_text_controls), flush=True)
        #------------------------------------
        # Remove cancelled claims
        cancelled_condition = alice_ApplicationFile_text_controls.claim_text.\
            apply(lambda x: not(bool(re.search(r'canceled', re.sub('[^A-Za-z]','', x))) & bool(len(re.sub('[^A-Za-z]','', x)) < 20)))
        # cancelled_condition_2 = alice_ApplicationFile_text_controls.claim_text.apply(lambda x: not(bool(re.search(r'(canceled)', x))))
        alice_ApplicationFile_text_controls = alice_ApplicationFile_text_controls[cancelled_condition]
        # alice_text_controls.claim_text.value_counts().head(10)
        print('\t\t Number of uncancelled control claims from Application Files %.0f' % len(alice_ApplicationFile_text_controls), flush=True)
        #------------------------------------
        # Control for pg-publication number to be correct
        alice_ApplicationFile_text_controls['pgpub_number'] = alice_ApplicationFile_text_controls.pgpub_number.astype(str).\
            apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
        alice_ApplicationFile_text_controls['earliest_pgpub_number_cleaned'] = alice_ApplicationFile_text_controls.earliest_pgpub_number.astype(str). \
            apply(lambda x: re.sub(r'^US', '', x)).apply(lambda x: re.sub(r'[a-zA-Z]{1,1}\d{0,1}$', '', x))

        publication_control_patent_condition = (alice_ApplicationFile_text_controls.pgpub_number == alice_ApplicationFile_text_controls.earliest_pgpub_number_cleaned) | \
                                                (alice_ApplicationFile_text_controls.pgpub_number == '')

        alice_text_controls = alice_ApplicationFile_text_controls[publication_control_patent_condition]

        # drop for later claim id
        alice_text_controls = alice_text_controls.drop(['claim_num'], axis=1)
        print('\t\t Number of control claims with right pgpub file from Application Files %.0f' % len(alice_text_controls), flush=True)

    #======================================
    # Sample balancing
    #======================================

    #=======================================
    # !!!Drop non-unique entries
    #alice_application_treated['unique_claim_id'] = alice_application_treated.apply(lambda x: str(x['app_id']) + '_' + str(x['claim_int']), axis=1)
    #alice_application_treated.unique_claim_id.value_counts().head(10)
    #alice_text_controls = alice_text_controls.rename(columns={'claim_number':'claim_int'})
    #alice_text_controls['unique_claim_id'] = alice_text_controls.apply(lambda x: str(x['app_id']) + '_' + str(x['claim_int']), axis=1)
    #alice_text_controls.unique_claim_id.value_counts().head(10)

    alice_application_treated = alice_application_treated.drop_duplicates(['claim_text', 'app_id', 'earliest_pgpub_number'])
    alice_text_controls = alice_text_controls.drop_duplicates(['claim_text', 'app_id', 'earliest_pgpub_number'])
    print(' \t Alice unique treated claims before class selections: \n' + str(len(alice_application_treated)), flush=True)
    print(' \t Unique control claims before class selections: \n' + str(len(alice_text_controls)), flush=True)

    #=======================================
    #--------------------------------------
    # Restrict to same classes as controls
    #alice_application_treated['uspc_class_int'] = pd.to_numeric(alice_application_treated.uspc_class,
    #                                                            downcast = 'integer',
    #                                                            errors = 'coerce')

    alice_application_treated['uspc_class_str'] = alice_application_treated.uspc_class.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    alice_application_treated.uspc_class_str.value_counts().head(10)
    # Source: https://www.uspto.gov/web/patents/classification/selectnumwithtitle.htm
    # 705    => Data processing: financial, business practice, management, or cost/price determination
    # 463    => Amusement devices: games
    # 702    => Data processing: measuring, calibrating, or testing
    # 434    => Education and demonstration
    # 709    => Electrical computers and digital processing systems: multicomputer data transferring
    # 273    => Amusement devices: games
    # 716    => Computer-aided design and analysis of circuits and semiconductor masks
    # 703    => Data processing: structural design, modeling, simulation, and emulation
    # 435    => Chemistry: molecular biology and microbiology
    # 701    => Data processing: vehicles, navigation, and relative location

    print('\t\t Count of Alice classes\n' +
          str(alice_application_treated.uspc_class_str.value_counts().head(10)), flush=True)
    # 705    3824
    # 463     459
    # 702     212
    # 434     142
    # 703      45
    # 435      34
    # 709      31
    # 716      31
    # 708      29
    # 701      27

    print('\t\t Cumsum of Alice classes\n' +
          str(alice_application_treated.uspc_class_str.value_counts(normalize=True).head(10).cumsum()), flush=True)
    #705    0.737226
    #463    0.830657
    #702    0.873410
    #434    0.901564
    #703    0.908863
    #435    0.915954
    #716    0.922419
    #709    0.928884
    #708    0.934932
    #273    0.940563
    #!!!! => Restruct to 4 main classes which make up more than 90% of all cases

    #alice_text_controls['uspc_class_int'] = pd.to_numeric(alice_text_controls.uspc_class,
    #                                                      downcast = 'integer',
    #                                                      errors = 'coerce')

    alice_text_controls['uspc_class_str'] = alice_text_controls.uspc_class.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    alice_text_controls.uspc_class_str.value_counts().head(10)
    #370    61631
    #455    48859
    #382    37367
    #514    35774
    #345    34247
    #348    31830
    #709    29951
    #375    27731
    #701    27329
    #424    27293

    #----------------------------------------
    #!!! Select control and treated patents from top n main classes or specific given classes
    if use_specified_uspc_class==True:
        main_classes = list(set(specified_uspc_class))
    else:
        main_classes = list(set(alice_application_treated.uspc_class_str.value_counts(). \
                                nlargest(nclasses).reset_index()['index']))
    print('\t USPC main classes for patent: \n' + str(main_classes), flush=True)

    # application_data[application_data['filing_date_dt'] > alice_decision_date]['uspc_class'].isnull().value_counts()
    #False    1543458
    #True      172360
    # => For application data, USPC classes are still relevant!!

    #alice_text_treated = alice_application_treated[alice_application_treated.uspc_class_int.isin(main_classes)].copy()
    #alice_text_controls = alice_text_controls[alice_text_controls.uspc_class_int.isin(main_classes)].copy()

    alice_text_treated = alice_application_treated[alice_application_treated.uspc_class_str.isin(main_classes)].copy()
    alice_text_controls = alice_text_controls[alice_text_controls.uspc_class_str.isin(main_classes)].copy()
    print('\t\t Number of treated claims in main class %.0f and control claims %.0f' % (len(alice_text_treated), len(alice_text_controls)), flush=True)

    #--------------------------------------
    # similar dates
    #alice_text_treated['filing_date_dt'] = pd.to_datetime(alice_text_treated.filing_date, errors='coerce') => alread coerced above
    alice_text_controls['filing_date_dt'] = pd.to_datetime(alice_text_controls.filing_date, errors='coerce')
    alice_text_controls['appl_status_date_dt'] = pd.to_datetime(alice_text_controls.appl_status_date, errors='coerce')
    alice_text_controls['patent_issue_date_dt'] = pd.to_datetime(alice_text_controls.patent_issue_date, errors='coerce')

    # Restrict control patents to those granted after the Alice decision
    alice_decision_date = np.datetime64('2014-06-19')

    timed_alice_text_controls = alice_text_controls[alice_text_controls.patent_issue_date_dt > alice_decision_date].copy()
    print('\t\t Number of control claims issued after the Alice decision %.0f' % len(timed_alice_text_controls), flush=True)
    print(' \t Control USPC Classes count: \n' + str(timed_alice_text_controls.uspc_class_str.value_counts()), flush=True)
    print(' \t Control Filing years count: \n' + str(timed_alice_text_controls.filing_date_dt.dt.year.value_counts()), flush=True)

    #=======================================
    # Resample to match uspc and filing year distribution as the treated claims
    alice_text_treated['filing_data_year'] = alice_text_treated.filing_date_dt.dt.year
    alice_groups = alice_text_treated.groupby(['uspc_class_str', 'filing_data_year']).size().reset_index(name='count')

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print(' \t Alice USPC Classes count: \n' + str(alice_text_treated.uspc_class_str.value_counts(normalize=True)), flush=True)
    print(' \t Alice Filing years count: \n' + str(alice_text_treated.filing_date_dt.dt.year.value_counts(normalize=True)), flush=True)
    print(' \t Alice year and type counts: \n' + str(alice_groups), flush=True)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    # Create relative frequency by filing year and uspc class
    alice_groups['relative_freq'] = alice_groups['count'] / alice_groups['count'].agg(sum)

    timed_alice_text_controls['filing_data_year'] = timed_alice_text_controls.filing_date_dt.dt.year
    timed_alice_text_controls = pd.merge(timed_alice_text_controls,
                                        alice_groups,
                                        on=['uspc_class_str', 'filing_data_year'],
                                        how='inner')

    #timed_alice_text_controls.loc[timed_alice_text_controls.relative_freq.isnull(), 'relative_freq'] = 0

    # resample control patents by weight, allower for replace to have more balance in set
    # !!! allow for oversampling !!!!
    sample_length = len(alice_text_treated)
    balance_alice_text_controls = timed_alice_text_controls.sample(n=sample_length,
                                                                   weights=timed_alice_text_controls.relative_freq,
                                                                   random_state=RANDOM_SEED,
                                                                   replace=replacement)

    balance_alice_text_controls[['uspc_class_str']].value_counts(normalize=True)
    alice_text_treated[['uspc_class_str']].value_counts(normalize=True)

    balance_alice_text_controls[['filing_data_year']].value_counts(normalize=True)
    alice_text_treated[['filing_data_year']].value_counts(normalize=True)


    balance_alice_text_controls = balance_alice_text_controls.rename(columns={'claim_number':'claim_int'})
    balance_alice_text_controls['unique_claim_id'] = balance_alice_text_controls.apply(lambda x: str(x['app_id']) + '_' + str(x['claim_int']), axis=1)
    #balance_alice_text_controls.app_id.value_counts(normalize=True).head(10)
    #14035403.0    0.009633
    #13443303.0    0.009167
    #13970410.0    0.007147
    #13883926.0    0.006526
    #14056440.0    0.005283
    #13794259.0    0.005283
    #13644219.0    0.004195
    #14069107.0    0.003884
    #13788010.0    0.003884
    #13475494.0    0.003729

    print(' \t Unique App_id + Claim Number repetitions in balanced controls: \n' +
        str(balance_alice_text_controls.unique_claim_id.value_counts().head(10)), flush=True)
    #13765327.0_1     13
    #14081072.0_1     13
    #14107814.0_19    12
    #14021118.0_15    11
    #13788010.0_2     11
    #14029360.0_10    11
    #14025197.0_13    11
    #13763226.0_34    10
    #13536908.0_15    10
    #13749268.0_1     10
    #balance_alice_text_controls.app_id.value_counts(normalize=True).head(10).cumsum()
    # 0.062461
    # Compared with case without redrawing of 0.021442
    # => Oversampling only overweights some cases by a factor of around 3,
    #       With individual claims being overweighted by a factor of around 10
    #    that seems still okay

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print(' \t Alice USPC Classes control group: \n' + str(balance_alice_text_controls[['uspc_class_str']].value_counts(normalize=True)), flush=True)
    print(' \t Alice USPC Classes treated group: \n' + str(alice_text_treated[['uspc_class_str']].value_counts(normalize=True)), flush=True)

    print(' \t Alice Filing years control group: \n' + str(balance_alice_text_controls[['filing_data_year']].value_counts(normalize=True)), flush=True)
    print(' \t Alice Filing years treated group: \n' + str(alice_text_treated[['filing_data_year']].value_counts(normalize=True)), flush=True)

    print(' \t Count Alice USPC Classes control group: \n' + str(balance_alice_text_controls[['uspc_class_str']].value_counts()), flush=True)
    print(' \t Count Alice USPC Classes treated group: \n' + str(alice_text_treated[['uspc_class_str']].value_counts()), flush=True)

    print(' \t Count Alice Filing years control group: \n' + str(balance_alice_text_controls[['filing_data_year']].value_counts()), flush=True)
    print(' \t Count Alice Filing years treated group: \n' + str(alice_text_treated[['filing_data_year']].value_counts()), flush=True)


    print(' \t Alice year and type counts for balanced control group: \n' +
          str(balance_alice_text_controls.groupby(['uspc_class_str', 'filing_data_year']).size().reset_index(name='count')), flush=True)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #alice_control_groups = balance_alice_text_controls.groupby(['uspc_class_int', 'filing_data_year']).size().reset_index(name='count')
    #alice_control_groups['relative_freq'] = alice_control_groups['count'] / alice_control_groups['count'].agg(sum)

    #control_distr = pd.merge(alice_groups, alice_control_groups, on=['uspc_class_int', 'filing_data_year'])


    #=======================================
    # Construct dataframe with treated and untreated claims

    treated_claims_text = alice_text_treated[['app_id', 'claim_text']].copy()
    treated_claims_text['treated'] = 1

    control_claims_text = balance_alice_text_controls[['app_id', 'claim_text']].copy()
    control_claims_text['treated'] = 0

    training_data = pd.concat([treated_claims_text, control_claims_text], \
                              axis = 0, ignore_index = True)

    # Cleaning the entries and remove digits from the beginning
    training_data['claim_text'] = training_data.apply(lambda row: \
                                                      re.sub(r'^\d{1,3}\.{0,1}\s', \
                                                             '', row['claim_text']), \
                                                          axis = 1)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print(' \t Alice treated data length: ' + str(len(alice_text_treated)), flush=True)
    print(' \t Unbalanced Control data length: ' + str(len(timed_alice_text_controls)), flush=True)
    print(' \t Training data length: ' + str(len(training_data)), flush=True)

    # Looking for specific words
    # list(training_data.claim_text[training_data.claim_text.apply(lambda x: bool(re.search('plurality', x)))])[1]

    return(training_data, main_classes)


######################################
#   Sklearn Model Building
######################################

#=====================================
# Package Loading
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.feature_extraction.text import TfidfTransformer
from nltk.corpus import stopwords
from gensim.parsing.preprocessing import preprocess_string
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

#------------------------------------------
# source: https://scikit-learn.org/stable/modules/svm.html#svm-classification
from sklearn.svm import SVC

from sklearn.preprocessing import Normalizer
# from sklearn.preprocessing import FunctionTransformer

from sklearn.pipeline import Pipeline

from sklearn.metrics import matthews_corrcoef, confusion_matrix, classification_report
from sklearn.metrics import f1_score, precision_score, recall_score, accuracy_score
from sklearn.metrics import precision_recall_curve, roc_curve, auc, average_precision_score
from sklearn.metrics import plot_confusion_matrix
# from sklearn.metrics import plot_precision_recall_curve, plot_roc_curve

from sklearn.model_selection import RandomizedSearchCV

# Model saving
import joblib

# Output of report
import json
# For word cloud
#from gensim.models import TfidfModel
#from gensim.corpora import Dictionary
#------------------------------------------
# Source: https://towardsdatascience.com/multi-class-text-classification-model-comparison-and-selection-5eb066197568
#         https://medium.com/wisio/a-gentle-introduction-to-doc2vec-db3e8c0cce5e
from gensim.models.doc2vec import Doc2Vec, TaggedDocument

#-----------------------------------------
# Doc2Vec Support Class
# source: https://medium.com/swlh/a-text-classification-approach-using-vector-space-modelling-doc2vec-pca-74fb6fd73760
#         https://stackoverflow.com/questions/50278744/pipeline-and-gridsearch-for-doc2vec
from sklearn.base import BaseEstimator


#====================================
# Tokenizer and Stopword
def tokenizer(text):
    tokens = word_tokenize(text)
    stems = []
    for item in tokens:
        if (len(item) > 2):
            stems.append(PorterStemmer().stem(item))
    return stems

#-----------------------------------
# Create Stopwords list
stop_words = set(stopwords.words("english"))

# Add preprocessed stopwords to fit tokenization
add_stopword = []
for item in stop_words:
    add_stopword.extend(tokenizer(item))
add_stopword = set(add_stopword)

stop_words.update(add_stopword)

#------------------------------------
# Custom tokenizer
def custom_tokenizer(text):
    return [w for w in tokenizer(text) if ~bool(w in stop_words)]

# custom_tokenizer(test_text)
# preprocess_string(test_text)
# test_text = 'A patent is a form of intellectual property that gives its owner the legal right to exclude others from making, using, or selling an invention for a limited period of years in exchange for publishing an enabling public disclosure of the invention. In most countries, patent rights fall under private law and the patent holder must sue someone infringing the patent in order to enforce his or her rights. In some industries patents are an essential form of competitive advantage; in others they are irrelevant.'
# set(custom_tokenizer(test_text)) - set(preprocess_string(test_text))
# set(preprocess_string(test_text))- set(custom_tokenizer(test_text))

#=================================================
# Helper function for output validation
#=================================================
def _validation_output(model, model_name, output_version, output_directory, X_test, y_test):
    '''Internal function generating validation outputs for model, return dict with scores'''

    print('Model Validation for: ' + str(model_name))
    print('Confusion Matrix :')
    cm = confusion_matrix(y_test, model.predict(X_test), labels=[0,1], normalize='true')
    print(cm)
    disp = plot_confusion_matrix(model, X_test, y_test,
                                 display_labels=['Alice valid', 'Alice invalid'],
                                 cmap=plt.cm.Blues,
                                 normalize='true')
    disp.ax_.set_title("Normalized confusion matrix")
    # plt.show()
    plt.savefig(output_directory + '//' + model_name + '_Model_Confusion_Matrix_plot_'+str(output_version)+'.jpg',
                bbox_inches='tight',
                optimize=True)

    #************************************************
    mcc = matthews_corrcoef(y_test, model.predict(X_test))
    print('MCC : %.2f' % mcc)
    f1_s = f1_score(y_test, model.predict(X_test), average='binary')
    print('F1 Score : %.2f' % f1_s)
    precision_s = precision_score(y_test, model.predict(X_test), average='binary')
    print('Precision Score : %.2f' % precision_s)
    recall_s = recall_score(y_test, model.predict(X_test), average='binary')
    print('Recall Score : %.2f' % precision_s)
    accuracy_s = accuracy_score(y_test, model.predict(X_test))
    print('Accuracy Score : %.2f' % accuracy_s)

    #------------------------------
    # Score dictionary for output
    score_dict = {'Precision Score': precision_s,
                  'Recall Score': recall_s,
                  'Accuracy Score': accuracy_s,
                  'F1 Score': f1_s,
                  'MCC': mcc}
    #------------------------------

    print('Report: ')
    print(classification_report(y_test, model.predict(X_test)))

    # Update report with MCC and F1 Score:
    report = classification_report(y_test, model.predict(X_test), output_dict=True)
    report.update(score_dict)

    #------------------------------------
    # Save updated reports
    with open(output_directory + '//' + model_name + '_Model_report_dict_' + str(output_version) + '.json', 'w') as fp:
        json.dump(report, fp)

    pd.DataFrame(report).transpose().to_csv(output_directory + '//' + model_name + '_Model_report_dict_' + str(output_version) + '.csv',
                                            float_format='%.3f', encoding='utf-8')
    pd.DataFrame(report).transpose().to_latex(output_directory + '//' + model_name + '_Model_report_dict_' + str(output_version) + '.tex',
                                              float_format='%.3f', encoding='utf-8')

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Generate latex report
    #with open(output_directory + '//' + model_name + '_Model_report_dict_' + str(output_version) + '.json', 'r') as fp:
    #    data = json.load(fp)
    #pd.DataFrame.from_dict(data).transpose().to_latex(output_directory + '//' + model_name + '_Model_report_dict_' + str(output_version) + '.tex', index=False)

    #************************************************
    print('Precision Recall Curver: ')
    y_true = y_test.to_list()
    # Control for cases without predict_proba functions,
    #       Precision functions take alternativel also decision functions
    try:
        y_pred = [l[1] for l in model.predict_proba(X_test)]
    except AttributeError:
        y_pred = list(model.decision_function(X_test))

    # Source: https://scikit-learn.org/stable/auto_examples/model_selection/plot_precision_recall.html#sphx-glr-auto-examples-model-selection-plot-precision-recall-py
    precision, recall, thresholds = precision_recall_curve(y_true, y_pred)
    average_precision = average_precision_score(y_true, y_pred)

    plt.figure()
    plt.step(recall, precision, where='post')

    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.ylim([0.0, 1.05])
    plt.xlim([0.0, 1.0])
    plt.title(
    'Average precision score, Alice Classification: AP={0:0.2f}'
    .format(average_precision))
    #plt.show()
    plt.savefig(output_directory + '//' + model_name + '_Model_Precision_Recall_curve_plot_'+str(output_version)+'.jpg', optimize=True)

    #************************************************
    print('ROC Curver: ')
    fpr, tpr, thresholds = roc_curve(y_true, y_pred)
    roc_auc = auc(fpr, tpr)

    # Plot ROC Curve
    # Source: https://scikit-learn.org/stable/auto_examples/model_selection/plot_roc.html
    plt.figure()
    lw = 2
    plt.plot(fpr, tpr, color='darkorange',
             lw=lw, label='ROC curve (area = %0.2f)' % roc_auc)
    plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Alice Classification Receiver Operating Characteristic')
    plt.legend(loc="lower right")
    #plt.show()
    plt.savefig(output_directory + '//' + model_name + '_Model_ROC_curve_plot_'+str(output_version)+'.jpg', optimize=True)

    return(score_dict)

#################################################
# Various models with TF-IDF Matrix             #
#################################################
# Use different model for performance evalutation

def tfidf_various_build(X_train, X_test, y_train, y_test,
                        output_version, output_directory,
                        classification_model, cls_name):
    r'''
    METHOD: Builds Pipeline for text classification of claims using TFIDF

    INPUT:  - X_train / X_test: df, column of claim text for training / testing
            - y_train / y_test: df, binary classification of text being ineligible (=1) or eligible (=0)
            - output_directory: directory to save outputs
            - classification_model: sklearn model for classification
            - cls_name: str, classification model for saving
            - output_version: str with version output
    OUTPUT: - TFIDF_{cls_name}.joblib, TFIDF_{cls_name}.pkl: Saved pipelines
            - RETURN: Built pipeline and dictionary with performance scores
            - Print: Confusiion Matrix, MCC score, and Report of fitted model,
                    Save models and plot to 'TFIDF_{cls_name}_Output_' + output_version
                    to output_directory
    r'''
    #-----------------------------------------
    # Build and fit pipeline
    tfidf_cls = Pipeline([('vect', CountVectorizer(tokenizer = preprocess_string,
                                                    lowercase = True,
                                                    ngram_range = (1, 2),
                                                    max_df = 0.5, #=> in balanced set, exclude terms frequent in both classes
                                                    min_df = 10) # => correct for misspelling
                                                    #max_features=1000)
                                                     ),
                            ('tfidf', TfidfTransformer()),
                            #('fct', FunctionTransformer(lambda x: x.todense(), accept_sparse=True)), # Transform into dense matrix
                            #('normalizer',Normalizer()),
                            ('clf', classification_model),
                            ])

    tfidf_cls.fit(X_train, y_train)

    #-------------------------------------
    # Validation
    score_dict = _validation_output(model=tfidf_cls,
                                    model_name='tfidf_' + str(cls_name),
                                    output_version=output_version,
                                    output_directory=output_directory,
                                    X_test=X_test,
                                    y_test=y_test)

    #-----------------------------------
    # Save Model
    joblib.dump(tfidf_cls, output_directory + '//' + 'tfidf_' + str(cls_name) + '_' + \
                str(output_version) + '.joblib')

    with open(output_directory + '//' + 'tfidf_' + str(cls_name) + '_' + \
              str(output_version) + '.pkl', 'wb') as model_file:
        pickle.dump(tfidf_cls, model_file)

    return(tfidf_cls, score_dict)


#################################################
# Support Vector Machine with TF-IDF Matrix     #
#################################################
#!!!! Use results from optimization:
# => ngram range (1,2), min_df=0, poly with degree 2 or 3, C = 10, coef0 = 0.1


def tfidf_svc_build(X_train, X_test, y_train, y_test, output_version, optimize=False):
    r'''
    METHOD: Builds TFIDF-SVC-Pipeline for text classification of claims

    INPUT:  - X_train / X_test: df, column of claim text for training / testing
            - y_train / y_test: df, binary classification of text being ineligible (=1) or eligible (=0)
            - optimize: Bool, should optimization of parameters be done, if True
                            create also TFIDF_SVC_ModelEvaluation output as csv
            - output_version: str with version output
    OUTPUT: - TFIDF_SVC_Poly2_Model.joblib, TFIDF_SVC_Poly2_Model.pkl: Saved pipelines with poly degree 2 kernel
            - TFIDF_SVC_RBF_Model.joblib, TFIDF_SVC_RBF_Model.pkl: Saved pipelines with rbf kernel
            - TFIDF_SVC_Linear_Model.joblib, TFIDF_SVC_Linear_Model.pkl: Saved pipelines with linear kernel
            - RETURN: Built pipeline for poly2, rbf, linear
            - Print: Confusiion Matrix, MCC score, and Report of fitted model,
                    Save models and plot to 'TFIDF_SVC_Output_' + output_version directory
    r'''
    #--------------------------------------------
    # Create Output Directory
    output_directory = r'TFIDF_SVC_Output_'+str(output_version)
    #====================================
    # Create Output Path if not already exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    #============================================
    #============================================
    def _pipeline_build_and_validation_tfidf_svc(kernel='rbf',
                                                 #C=10,
                                                 #coef0=0.1,
                                                 degree=2,
                                                 svc_name='rbf'):
        '''Wrapper for pipeline building and validation'''
        #--------------------------------------------
        # Define Pipeline for base rbf kernel
        tfidf_svc = Pipeline([
                            ('vect', CountVectorizer(tokenizer = preprocess_string,
                                                    lowercase = True,
                                                    ngram_range = (1, 2),
                                                    max_df = 0.5,
                                                    min_df = 10) # => filter out misspellings
                                                    #max_features=1000,
                                                    #min_df = 10)
                                                     ),
                            ('tfidf', TfidfTransformer()),
                            #('fct', FunctionTransformer(lambda x: x.todense(), accept_sparse=True)), # Transform into dense matrix
                            #('normalizer',Normalizer()),
                            ('clf', SVC(verbose=0,
                                        #class_weight='balanced', => already balanced training set
                                        random_state=RANDOM_SEED,
                                        probability=True,
                                        kernel=kernel,
                                        #C=C,
                                        #coef0=coef0,
                                        degree=degree,
                                        cache_size=500)),
                            ])

        tfidf_svc.fit(X_train, y_train)

        #-------------------------------------
        # Validation
        _validation_output(tfidf_svc, 'tfidf_svc_' + str(svc_name),
                           output_version,
                           output_directory,
                           X_test,
                           y_test)

        #-----------------------------------
        # Save Model

        joblib.dump(tfidf_svc, output_directory + '//' + 'tfidf_svc_' + str(svc_name) + '_' + \
                    str(output_version) + '.joblib')

        with open(output_directory + '//' + 'tfidf_svc_' + str(svc_name) + '_' + \
                  str(output_version) + '.pkl', 'wb') as model_file:
          pickle.dump(tfidf_svc, model_file)

        return(tfidf_svc)
    #============================================
    #============================================
    # Build and definition

    #--------------------------------------------
    # Define Pipeline for rbf kernel
    text_rbf_svc = _pipeline_build_and_validation_tfidf_svc(
        kernel='rbf',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='rbf'
        )


    #--------------------------------------------
    # Define Pipeline for quadratic kernel
    text_poly2_svc = _pipeline_build_and_validation_tfidf_svc(
        kernel='poly',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='poly2'
        )

    #--------------------------------------------
    # Define Pipeline for linear kernel
    text_linear_svc = _pipeline_build_and_validation_tfidf_svc(
        kernel='linear',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='linear'
        )

    #==========================================
    # Optimization
    def _optimization():
        ''' Uses Random Search to find optimal parameter settings '''

        param_grid = {
             'vect__ngram_range': [(1, 1), (1, 2), (1, 3)],
             'vect__max_df': [0.25, 0.5, 0.75],
             'vect__min_df': [0, 10, 20, 30],
             'vect__tokenizer': [preprocess_string, custom_tokenizer],

             'tfidf__use_idf': [True, False],

             'clf__C': [1e-1, 1, 1e+1, 1e+2, 1e+3],
             'clf__kernel': ['poly', 'rbf', 'linear'],
             'clf__degree': [2, 3, 4],
             'clf__coef0': np.arange(1e-2,2e-1,0.015),
             }


        gs_clf = RandomizedSearchCV(text_poly2_svc,
                              param_grid,
                              verbose=1,
                              cv=5,
                              n_iter=1000,
                              random_state=RANDOM_SEED,
                              scoring='accuracy',
                              n_jobs = -1)

        gs_clf.fit(X_train, y_train)

        #------------------------------------
        # Evaluation Output

        scores_df_clf = pd.DataFrame(gs_clf.cv_results_).sort_values(by='rank_test_score')
        scores_df_clf.to_csv(path_or_buf = output_directory + '//TFIDF_SVC_ModelEvaluation_' +
                                             str(output_version) + '.csv',
                                             encoding = 'utf-8',
                                             index=False)

    #--------------------------------------
    # Optimization Execution:
    if (optimize==True):
        _optimization()

    return(text_poly2_svc, text_rbf_svc, text_linear_svc)

###########################################
# Doc2Vec + Support Vector Machine
###########################################

#----------------------------------------------
# Create Doc2Vec Class for Pipeline
#----------------------------------------------
class Doc2VecTransformer(BaseEstimator):
    def __init__(self,  dm=0,
                        vector_size=300,
                        negative=5,
                        min_count=1,
                        alpha=0.065,
                        min_alpha=0.065,
                        epochs=5,
                        seed=RANDOM_SEED,
                        dbow_words=0,
                        workers=CORES,
                        epochs_infer=20):
         self.dm = dm
         self.vector_size = vector_size
         self.negative = negative
         self.min_count = min_count
         self.alpha = alpha
         self.min_alpha = min_alpha
         self.epochs = epochs
         self.seed = seed
         self.dbow_words = dbow_words
         self.workers = workers

         self.epochs_infer = epochs_infer

    def fit(self, x, y=None):
         # Create tagged documents
         tagged_x = [TaggedDocument(preprocess_string(v), [i]) for i, v in enumerate(x)]

         # initiate model
         self.model_dbow = Doc2Vec(tagged_x,
                                   dm=self.dm,
                                   vector_size=self.vector_size,
                                   #negative=self.negative,
                                   min_count=self.min_count,
                                   #alpha=self.alpha,
                                   #min_alpha=self.min_alpha,
                                   epochs=self.epochs,
                                   seed=self.seed,
                                   dbow_words=self.dbow_words,
                                   workers=self.workers)
         # Build vocabulary
         #self.model_dbow.build_vocab(tagged_x)
         # Train model
         #self.model_dbow.train(tagged_x, total_examples=len(tagged_x), epochs=self.epochs)
         return self

    def transform(self, x):
        return np.asmatrix(np.array([self.model_dbow.infer_vector(preprocess_string(v), \
                                                                  epochs=self.epochs_infer) for i, v in enumerate(x)]))

    def fit_transform(self, x, y=None):
        self.fit(x)
        return self.transform(x)

#----------------------------------------------
# Function for model building
#----------------------------------------------
def doc2vec_svc_build(X_train, X_test, y_train, y_test, output_version, optimize=False):
    r'''
    METHOD: Builds Dov2Vec-SVC-Pipeline for text classification of claims

    INPUT:  - X_train / X_test: df, column of claim text for training / testing
            - y_train / y_test: df, binary classification of text being ineligible (=1) or eligible (=0)
            - optimize: Bool, should optimization of parameters be done, if True
                            create also Doc2Vec_SCV_ModelEvaluation output as csv
            - output_version: str with version output
    OUTPUT: - Doc2Vec_SVC_RBF.joblib, Doc2Vec_SVC_RBF.pkl: Saved pipelines with SVC rbf kernel
            - Doc2Vec_SVC_Poly2.joblib, Doc2Vec_SVC_Poly2.pkl: Saved pipelines with SVC quadratic kernel
            - Doc2Vec_SVC_Linear.joblib, Doc2Vec_SVC_Linear.pkl: Saved pipelines with SVC linear kernel
            - RETURN: Built pipelines for rbf, poly2, linear
            - Print: Confusiion Matrix, MCC score, and Report of fitted model
                        Save models and plot to 'Doc2Vec_SVC_Output_' + output_version directory
    r'''

    #--------------------------------------------
    # Create Output Directory
    output_directory = r'Doc2Vec_SVC_Output_'+str(output_version)
    #====================================
    # Create Output Path if not already exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    #============================================
    #============================================
    def _pipeline_build_and_validation_doc2vec_svc(kernel='rbf',
                                                   #C=10,
                                                   #coef0=0.1,
                                                   degree=2,
                                                   svc_name='rbf'):
        '''Wrapper for pipeline building and validation'''
        #--------------------------------------------
        # Pipeline Construction
        doc2vec_clf = Pipeline([
                                ('doc2vec', Doc2VecTransformer(dm=0,
                                                               vector_size=300,
                                                               #negative=5,
                                                               min_count=10, #=> correct for misspellings
                                                               #alpha=0.065,
                                                               #min_alpha=0.065,
                                                               epochs=5,
                                                               seed = RANDOM_SEED,
                                                               dbow_words=0,
                                                               workers=CORES,
                                                               epochs_infer=20)),
                                ('normalizer',Normalizer()),
                                ('clf', SVC(verbose=0,
                                            #class_weight='balanced',
                                            random_state=RANDOM_SEED,
                                            probability=True,
                                            kernel=kernel,
                                            #C=C,
                                            #coef0=coef0,
                                            degree=degree,
                                            cache_size=500)),
                                ])

        doc2vec_clf.fit(X_train, y_train)

        #-------------------------------------
        # Validation
        _validation_output(doc2vec_clf,
                           'doc2vec_svc_' + str(svc_name),
                           output_version,
                           output_directory,
                           X_test,
                           y_test)

        #-----------------------------------
        # Save Model
        joblib.dump(doc2vec_clf, output_directory + '//' + 'doc2vec_svc_' + str(svc_name) + '_' + \
                    str(output_version) + '.joblib')

        with open(output_directory + '//' + 'doc2vec_svc_' + str(svc_name) + '_' + \
                  str(output_version)+'.pkl', 'wb') as model_file:
           pickle.dump(doc2vec_clf, model_file)

        return(doc2vec_clf)
    #============================================
    #============================================
    # Build and definition

    #--------------------------------------------
    # Define Pipeline for rbf kernel
    text_doc2vec_rbf_svc = _pipeline_build_and_validation_doc2vec_svc(
        kernel='rbf',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='rbf'
        )

    #--------------------------------------------
    # Define Pipeline for quadratic kernel
    text_doc2vec_poly2_svc = _pipeline_build_and_validation_doc2vec_svc(
        kernel='poly',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='poly2'
        )

    #--------------------------------------------
    # Define Pipeline for linear kernel
    text_doc2vec_linear_svc = _pipeline_build_and_validation_doc2vec_svc(
        kernel='linear',
        #C=10,
        #coef0=0.1,
        degree=2,
        svc_name='linear'
        )



    #----------------------------------
    # Optimization
    def _optimization_doc2vec():
        ''' Optimize Parameter Settings for Doc2Vec Pipeline'''
        param_doc2vec_clf = {
             'doc2vec__vector_size': [100, 200, 300],
             'doc2vec__negative': [0, 5, 10, 20],
             'doc2vec__min_count': [1, 5, 10, 20],
             'doc2vec__alpha': np.arange(1e-2,1e-1,0.015),
             'doc2vec__min_alpha': np.arange(1e-2,1e-1,0.015),
             'doc2vec__epochs': [5, 10, 20],
             'doc2vec__epochs_infer': [5, 10, 20, 30],

             'clf__C': [1e-1, 1, 1e+1, 1e+2, 1e+3],
             'clf__kernel': ['poly', 'rbf', 'linear'],
             'clf__degree': [2, 3, 4],
             'clf__coef0': np.arange(-1e-2,1e-1,0.015)
             }

        gs_doc2vec_clf = RandomizedSearchCV(
            text_doc2vec_linear_svc,
            param_doc2vec_clf,
            verbose=1,
            cv=5,
            n_iter=100,
            random_state=RANDOM_SEED,
            scoring='accuracy',
            n_jobs=-1
            )

        gs_doc2vec_clf.fit(X_train, y_train)

        #------------------------------------
        # Evaluation Output

        scores_df_doc2ve_clf = pd.DataFrame(gs_doc2vec_clf.cv_results_).sort_values(by='rank_test_score')
        scores_df_doc2ve_clf.to_csv(path_or_buf = output_directory + '//Doc2Vec_SCV_ModelEvaluation_' +
                                                    str(output_version)+'.csv',
                                                    encoding = 'utf-8',
                                                    index=False)

    #--------------------------------------
    # Optimization Execution:
    if (optimize==True):
        _optimization_doc2vec()

    return(text_doc2vec_rbf_svc, text_doc2vec_poly2_svc, text_doc2vec_linear_svc)


##################################################
# Helper function for word cloud visualization   #
##################################################
def _wordcloud_creation(model_data, output_version, output_directory):
    '''create word clouds from model_data (with columns claim_text and treated) in output_directory'''
    #=========================================
    # Create word cloud of word
    # Documentation: https://amueller.github.io/word_cloud/generated/wordcloud.WordCloud.html#
    wc = wordcloud.WordCloud(stopwords=wordcloud.STOPWORDS,
                             background_color='white',
                             max_font_size=40,
                             color_func=lambda *args, **kwargs: "black",
                             random_state=RANDOM_SEED)

    #-----------------------------------------
    # Define treated and uncreated corpa
    treated_texts = [str(t) for t in  model_data.loc[model_data.treated==1, 'claim_text']]
    treated_text = ' '.join(treated_texts)

    untreated_texts = [str(t) for t in  model_data.loc[model_data.treated==0, 'claim_text']]
    untreated_text = ' '.join(untreated_texts)

    #-----------------------------------------
    # Generate word clouds and save
    treated_wc = wc.generate(treated_text)
    treated_wc.to_file(output_directory + '//wc_unweighted_treated_trainingData_' + str(output_version) + '.jpg')

    untreated_wc = wc.generate(untreated_text)
    untreated_wc.to_file(output_directory + '//wc_unweighted_untreated_trainingData_' + str(output_version) + '.jpg')


    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Create word cloud weighted for differential frequency of words in treated and non-treated corpa

    #-----------------------------------------
    # Weight by differential frequency of terms in trated and non-treated corpa
    vectorized_model = TfidfVectorizer(use_idf=False,
                                       smooth_idf=False,
                                       stop_words=wordcloud.STOPWORDS)
    vectorized_corpa = vectorized_model.fit_transform([treated_text, untreated_text])

    #-----------------------------------------
    # Find relative difference between vectors (already normalized to unit length)
    differential_frequency = vectorized_corpa.toarray()[0] - vectorized_corpa.toarray()[1]

    #-----------------------------------------
    # create arrays for vector differences
    untreated_feature_frequency = []
    for f in differential_frequency:
        if f < 0:
            untreated_feature_frequency.append(-f)
        else:
            untreated_feature_frequency.append(0)
    # normalize to unit norm
    norm = np.linalg.norm(untreated_feature_frequency)
    untreated_feature_frequency = untreated_feature_frequency/norm

    # Get normalized vector for term difference of treated features
    treated_feature_frequency = []
    for f in differential_frequency:
        if f > 0:
            treated_feature_frequency.append(f)
        else:
            treated_feature_frequency.append(0)
    norm = np.linalg.norm(treated_feature_frequency)
    treated_feature_frequency = treated_feature_frequency/norm

    #-----------------------------------------
    # get terms from tfidf vector model and pair with weights
    wc_untreated_weights = {}
    for item in list(zip(vectorized_model.get_feature_names(), untreated_feature_frequency)):
        wc_untreated_weights[item[0]] = item[1]

    wc_treated_weights = {}
    for item in list(zip(vectorized_model.get_feature_names(), treated_feature_frequency)):
        wc_treated_weights[item[0]] = item[1]

    #-----------------------------------------
    # Create word cloud for both
    diff_treated_wc = wc.generate_from_frequencies(wc_treated_weights)
    diff_treated_wc.to_file(output_directory + '//wc_differential_frequency_weighting_treated_trainingData_' + str(output_version) + '.jpg')

    diff_untreated_wc = wc.generate_from_frequencies(wc_untreated_weights)
    diff_untreated_wc.to_file(output_directory + '//wc_differential_frequency_weighting_untreated_trainingData_' + str(output_version) + '.jpg')

    r'''
    # Source: https://www.scss.tcd.ie/~munnellg/projects/visualizing-text.html
    # https://radimrehurek.com/gensim/models/tfidfmodel.html

    # Tokenize the corpus
    vector_corpus = [word_tokenize(t) for t in [treated_text, untreated_text]]

    # Build dictionary
    dictionary = Dictionary(vector_corpus)

    # Vector to BOW vectors
    vectors_bow = [dictionary.doc2bow(t) for t in vector_corpus]

    # Build TFIDF model
    tfidf_model = TfidfModel(vectors_bow, smartirs='nnc')
    # => Get term frequencies from smartirs, source: https://en.wikipedia.org/wiki/SMART_Information_Retrieval_System

    # get TFIDF weights
    weights_treated = tfidf_model[vectors_bow[0]]
    weights_untreated = tfidf_model[vectors_bow[1]]

    # get terms from dictionary and pair with weights
    wc_treated_weights = [(dictionary[p[0]], p[1]) for p in weights_treated]
    wc_untreated_weights = [(dictionary[p[0]], p[1]) for p in weights_untreated]
    r'''
    return

#############################
# Main Routine              #
#############################
def _main_routine_wrapper(output_version=str(VERSION),
                          nclasses=4,
                          specified_uspc_class=['705'],
                          use_specified_uspc_class=False,
                          replacement_control_data=False,
                          use_PatentsView_control_claims=True):
    r'''Wrapper for main routine, differing in what type of control claims should be used
        OUTPUTS:
            - TFIDF_SVC_Output: directory with main model for tfidf-SVM model and performance outputs
            - Doc2Vec_SVC_Output: directory with model for Doc2Vec-SVM model and performance outputs

            - main_classes_Alice: pkl-file with list of uspc classes used for classification

            - Wordcloud: directory with .png outputs of word clouds

            - TFIDF_Several_Models: directory with model and performance outputs as summarized by Performance_summary
            - Performance_summary_df: tex-file with comparison of different classification models
    r'''
    #-------------------------------------------
    print('Start Main Routine, output verison: ' + str(output_version), flush=True)
    if use_PatentsView_control_claims:
        print('\t Use PatentsView control claims, replacement: ' + str(replacement_control_data), flush=True)
    else:
        print('\t Use Application text control claims, replacement: ' + str(replacement_control_data), flush=True)

    #-------------------------------------------
    import time
    from datetime import timedelta

    start_time = time.time()

    #*************************************************
    if use_specified_uspc_class == True:
        print('\t Use of specific classes: ' + str(use_specified_uspc_class) + '; ' + str(specified_uspc_class), flush=True)
        model_data, main_classes = training_data_import(nclasses=1,
                                                        home_directory=os.getcwd(),
                                                        specified_uspc_class=specified_uspc_class,
                                                        use_specified_uspc_class=True,
                                                        text_source='Alice_Claim_Extraction_v' + str(INPUT_VERSION),
                                                        replacement=replacement_control_data,
                                                        PatentsView_Control_claims=use_PatentsView_control_claims)

    else:
        #*************************************************
        print('\t Use top ' + str(nclasses) + ' classes affected.', flush=True)
        print('\t Load Data and create trainging dataset', flush=True)
        model_data, main_classes = training_data_import(nclasses=nclasses,
                                                        home_directory=os.getcwd(),
                                                        specified_uspc_class='xxx',
                                                        use_specified_uspc_class=False,
                                                        text_source='Alice_Claim_Extraction_v' + str(INPUT_VERSION),
                                                        replacement=replacement_control_data,
                                                        PatentsView_Control_claims=use_PatentsView_control_claims)
        # Use a smaller set to start developing the training model
        # model_data = model_data.sample(2000, random_state=RANDOM_SEED).copy()
        #*************************************************
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save classes main classes
    with open('main_classes_Alice_' + str(output_version) + '.pkl', 'wb') as fp:
        pickle.dump(main_classes, fp)

    #==========================================
    # Word cloud visualization
    print('\t Data visualiziation with word cloud', flush=True)
    start_time = time.time()

    #-----------------------------------
    # Output director for word cloud
    wc_output_directory = 'Wordcloud_v'+str(output_version)
    # Create WC Output Path if not already exist
    if not os.path.exists(wc_output_directory):
        os.makedirs(wc_output_directory)

    _wordcloud_creation(model_data,
                        output_version=output_version,
                        output_directory=wc_output_directory)
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    #=========================================
    # Split sample
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(model_data['claim_text'],
                                                        model_data['treated'],
                                                        test_size=0.15,
                                                        random_state=RANDOM_SEED,
                                                        stratify=model_data['treated'])

    #=============================================
    # Model Validation with different types of models
    print('\t Train and Evaluate Different Types of Models with TFIDF', flush=True)
    start_time = time.time()

    #--------------------------------------------
    # Create Output Directory
    output_different_models_directory = r'TFIDF_Several_Models_Output_'+str(output_version)
    #--------------------------------------------
    # Create Output Path if not already exist
    if not os.path.exists(output_different_models_directory):
        os.makedirs(output_different_models_directory)

    #------------------------------------------
    # Create DF from score dictionaries
    performance_df = pd.DataFrame()

    #-------------------------------------------
    # Model build and execution
    print('\t\t Logistic Regression', flush=True)
    from sklearn.linear_model import LogisticRegression
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=LogisticRegression(random_state=RANDOM_SEED),
                                        cls_name='logistic_regression')
    score_dict.update({'Model Name': 'Logistic Regression'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Naive Bayesian', flush=True)
    from sklearn.naive_bayes import MultinomialNB
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.naive_bayes.MultinomialNB.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=MultinomialNB(),
                                        cls_name='multinomial_NB')
    score_dict.update({'Model Name': 'Naive Bayes'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html
    print('\t\t SVC', flush=True)
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=SVC(random_state=RANDOM_SEED,
                                                                 probability=True),
                                        cls_name='svc_classifier')
    score_dict.update({'Model Name': 'Support Vector Machine'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Decision Tree', flush=True)
    from sklearn.tree import DecisionTreeClassifier
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.tree.DecisionTreeClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=DecisionTreeClassifier(random_state=RANDOM_SEED),
                                        cls_name='decision_tree_classifier')
    score_dict.update({'Model Name': 'Decision Tree'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Random Forest', flush=True)
    from sklearn.ensemble import RandomForestClassifier
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=RandomForestClassifier(random_state=RANDOM_SEED),
                                        cls_name='random_forest_classifier')
    score_dict.update({'Model Name': 'Random Forest'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t K Neighbors', flush=True)
    from sklearn.neighbors import KNeighborsClassifier
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.neighbors.KNeighborsClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=KNeighborsClassifier(),
                                        cls_name='k_neighbors')
    score_dict.update({'Model Name': 'K-nearest Neighbors'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Stochastic Gradient Descent', flush=True)
    # !!! No predict_proba, only with modified huber
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html
    from sklearn.linear_model import SGDClassifier
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=SGDClassifier(random_state=RANDOM_SEED),
                                        cls_name='sgd')
    score_dict.update({'Model Name': 'Stochastic Gradient Descent'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Stochastic Gradient Descent with modified huber loss', flush=True)
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.SGDClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=SGDClassifier(random_state=RANDOM_SEED,
                                                                           loss='modified_huber'),
                                        cls_name='sgd_modHuber')
    score_dict.update({'Model Name': 'Stochastic Gradient Descent - Modified Huber'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t AdaBoost', flush=True)
    from sklearn.ensemble import AdaBoostClassifier
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.AdaBoostClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=AdaBoostClassifier(random_state=RANDOM_SEED),
                                        cls_name='adaboost')
    score_dict.update({'Model Name': 'AdaBoost'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t Gradient Boosting', flush=True)
    from sklearn.ensemble import GradientBoostingClassifier
    # Source: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.GradientBoostingClassifier.html
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_version=output_version,
                                        output_directory=output_different_models_directory,
                                        classification_model=GradientBoostingClassifier(random_state=RANDOM_SEED),
                                        cls_name='gradientboosting')
    score_dict.update({'Model Name': 'Gradient Boosting'})
    performance_df = performance_df.append(score_dict, ignore_index=True)

    r'''
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    print('\t\t XGBoost', flush=True)
    from xgboost import XGBRegressor
    # Source: https://xgboost.readthedocs.io/en/latest/python/python_api.html#module-xgboost.sklearn
    _, score_dict = tfidf_various_build(X_train, X_test, y_train, y_test,
                                        output_directory=output_different_models_directory,
                                        classification_model=XGBRegressor(random_state=RANDOM_SEED,
                                                                          objective='binary:logistic'),
                                        cls_name='xgboost')
    score_dict.update({'Model Name': 'XGBoost'})
    performance_df = performance_df.append(score_dict, ignore_index=True)
    r'''
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save performance results
    performance_df = performance_df[['Model Name', 'Precision Score', 'Recall Score', 'F1 Score', 'Accuracy Score', 'MCC']]
    performance_df.to_csv(output_different_models_directory + '//Performance_summary_df_' + str(output_version) + '.csv',
                          float_format='%.3f', encoding='utf-8', index=True)
    performance_df.to_latex('Performance_summary_df_' + str(output_version) + '.tex',
                            float_format='%.3f', encoding='utf-8', index=False)

    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    #=============================================
    # SVC Model Training
    print('\t Train TF-IDF SVC Model', flush=True)
    start_time = time.time()
    tfidf_svc_build(X_train, X_test, y_train, y_test, output_version=output_version, optimize=False)
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    print('\t Train Doc2Vec SVC Model', flush=True)
    start_time = time.time()
    doc2vec_svc_build(X_train, X_test, y_train, y_test, output_version=output_version, optimize=False)
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    print('End Main Routine, output verison: ' + str(output_version), flush=True)
    return

#=======================================================
#=======================================================
# Execute Main Routine
if __name__ == '__main__':
    #r'''
    #------------------------------------------------------
    _main_routine_wrapper(output_version='PatentsViewControls_v' + str(VERSION),
                          nclasses=TOP_NCLASSES,
                          specified_uspc_class='xxx',
                          use_specified_uspc_class=False,
                          replacement_control_data=False,
                          use_PatentsView_control_claims=True)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    _main_routine_wrapper(output_version='ApplicationControls_v' + str(VERSION),
                          nclasses=TOP_NCLASSES,
                          specified_uspc_class='xxx',
                          use_specified_uspc_class=False,
                          replacement_control_data=True,
                          use_PatentsView_control_claims=False)
    #r'''
    #------------------------------------------------------
    _main_routine_wrapper(output_version='PatentsViewControls_only705_v' + str(VERSION),
                          nclasses=1,
                          specified_uspc_class=['705'],
                          use_specified_uspc_class=True,
                          replacement_control_data=False,
                          use_PatentsView_control_claims=True)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    _main_routine_wrapper(output_version='ApplicationControls_only705_v' + str(VERSION),
                          nclasses=1,
                          specified_uspc_class=['705'],
                          use_specified_uspc_class=True,
                          replacement_control_data=True,
                          use_PatentsView_control_claims=False)

r'''
Local Execution
r'''
