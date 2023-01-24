# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 3/10/2022
METHOD: AdaptKPSS_direct_Patent_Portfolio_Structuring_PatentsViewControls_4.1.py
        to use disambiguated assignees in PatentsView data.
        METHOD ADJUSTMENTS: Change also aggregation, counting forward citations
            removing weighted averages, and include depreciation of patent stock
        !!! Note: PatentsView assignee ids change frequently per new vintage,
            here is the vintage of Sept. 2021 used, but if data are constructed
            new to match with Census data, reconstruct with new assignee data.
    Subversion 1.2 (DATE 3/10/2022): Reduce runtime by removing pivot table
        (pivot tables are rarely used, and are already constructed in the Blocking_patent_prediction_construction_v1.2.py file)
    Subversion 1.3 (DATE 3/11/2022): Add forward citations and Balsmeier et al. (2017)
        quality classification
"""

r'''
#============================================
# Execution on hpc.haastech.org
#!/usr/bin/bash
#BSUB -n 1
#BSUB -e batch_output_directory/%J.err
#BSUB -o batch_output_directory/%J.out
# cd run _folder
# execute program
source activate py38
/apps/anaconda3/bin/python PatentsView_direcet_Patent_Portfolio_structuring__v1.3.py

#----------------------------
bsub <PatentsView_direcet_Patent_Portfolio_structuring__v1.3.sh
r'''


# %%
#################################################################
# Package Load
#################################################################

import pandas as pd
import numpy as np
import re
import os

import gc

import requests
from io import BytesIO
import zipfile
import csv

import multiprocessing as mp

#=============================================
# Current Build
VERSION = 1.3
# !!!! Also change model specification below !!!!!!!

# !!! Iteration of Classification Version
CLASSIFICATION_ITERATION = 9.2

#============================================
RANDOM_SEED = 42

# Define Home directory
home_directory = os.getcwd()

# Define source directory for additional data to be loaded
source_directory = r'Patent_portfolio_structuring_source_directory'
PatentsView_directory = 'PatentsView_raw_data'


# Path to classification output complemented by specific class of the control groups
classification_directory = 'Alice_patent_classification_vPatentsViewControls_v'+str(CLASSIFICATION_ITERATION)

#-------------------------------------------
# Create putput path
output_directory = 'Patent_Portfolio_based_on_PatentsView_data_'+str(VERSION)
# Create Intermediate Output Path if not already exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

#-------------------------------------------

pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 120)


# %%
########################################################
# Main for portfolio construction based on KPSS data   #
########################################################
def main(output_version, model_specification):
    print('Start patent portfolio construction for ' + str(output_version), flush=True)
    #################################################################
    # Loading Functions                                             #
    #################################################################

    #============================================
    #============================================
    # Execute until Checkpoint 1
    if not('PatentsView_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv' in\
           os.listdir(output_directory)):

        #####################################################################
        # Section 1: Augment with Patent Prediction                         #
        #####################################################################
        #===============================================
        # Alice Classification Assignment

        print('Merge with Alice claim classification', flush=True)
        #-----------------------------------------------
        # Load Alice patent classification (sourced from Patent_Claim_Classification Script)

        patent_classification_path = classification_directory+\
            '//FullText_Patent_claim_PatentView_'+str(model_specification)+'.csv'

        load_df = pd.read_csv(patent_classification_path, low_memory=False)

        # !!!! duplicates in patent classification !!!!!
        load_df=load_df.drop_duplicates()

        #!!!!! NOTE, there are duplicates due to claim level patent classification !!!!!!!!!!!!
        #************************************
        # Average across patent IDs
        patent_class = load_df[['patent_id', '1', 'predicted_label']].\
            groupby(['patent_id']).\
            agg(Alice_proba_predict_patent_average=('1', 'mean'),
                classified_claims=('predicted_label', 'count'),
                treated_classified_claims=('predicted_label', 'sum')).\
                reset_index()

        patent_class['min_one_Alice_affected'] = (patent_class.treated_classified_claims > 0).astype(int)
        patent_class['most_claims_Alice_affected'] = (patent_class.treated_classified_claims > (patent_class.classified_claims / 2)).astype(int)

        #----------------------------------------------
        # Binary prediction of Alice affection
        patent_class['Alice_mean_proba_predicted_affected'] = (patent_class.Alice_proba_predict_patent_average > 0.5).astype(int)

        #---------------------------------------------
        # Add identifier for only the first claim being invalid (the first claim is the most important one and broadest one)
        first_claim = load_df[load_df.claim_number==1][
            ['patent_id', 'predicted_label']].drop_duplicates().rename(columns={'predicted_label':'first_claim_Alice_affected'})

        patent_class = patent_class.merge(first_claim, on='patent_id', how='left')


        #########################################################################
        # Section 2: Assign predictions to PatentsView assignee data            #
        #########################################################################
        # Method used are copied and adapted from 'Blocking_patent_prediction_construction_v1.2.py'
        #================================================
        # Value matching
        #-----------------------------------------------
        print('Construct PatentsView data', flush=True)

        #---------------------------------------------------
        # Load and include filing dates for citing patent
        #========================================
        print('\t Application data load', flush=True)
        #----------------------------------------
        #   Application data from Patent View
        #----------------------------------------
        if ('application.tsv' in os.listdir(PatentsView_directory)):
                print('\t\t Load from directory', flush=True)
                #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                # Local
                application = pd.read_csv(PatentsView_directory + '/application.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
                #application = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\application.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load application data from economic research dataset

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/application.tsv.zip" , stream=True)
                if (r.ok == True) & \
                       (len(r.content) == int(r.headers['Content-Length'])):
                       break

            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            application = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #application = pd.read_csv(r"C:\Users\domin\Downloads\application.tsv\application.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        application = application.rename(columns={'id':'app_id',
                                                  'number':'app_number'})

        application['patent_id'] = pd.to_numeric(application.patent_id,
                                                downcast = 'integer', errors = 'coerce')
        application['filing_date_dt'] = pd.to_datetime(application['date'], errors='coerce')
        application['filing_year'] = application.filing_date_dt.dt.year

        #application['patent_id'].value_counts().value_counts()
        # => unique

        application = application[(application['patent_id'].notna())&(application['patent_id']!='')]
        #application.patent_id.isna().value_counts(normalize=True)
        #False    0.906544
        #True     0.093456
        #Name: patent_id, dtype: float64
        # => around 9.3% of applications refer to non-utility patents such as design patents

        print('\t Granted patent load', flush=True)
        #===========================================
        #----------------------------------------
        #   Patent Data from Patent View
        #----------------------------------------
        if ('patent.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            patent = pd.read_csv(PatentsView_directory + '/patent.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
            #patent = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\patent.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load patent data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/patent.tsv.zip")
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            patent = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)


        patent['patent_id'] = pd.to_numeric(patent.number,
                                            downcast = 'integer', errors = 'coerce')

        patent['issue_date_dt'] = pd.to_datetime(patent['date'])

        # Add issue quarter and year
        patent['issue_year'] = patent.issue_date_dt.dt.year
        patent['issue_quarter'] = patent.issue_date_dt.dt.quarter

        # Remove patent_id's that are na, this could cause an explosion of observations
        patent = patent[(patent['patent_id'].notna())&(patent['patent_id']!='')]

        #patent.patent_id.value_counts().value_counts()
        #=> unique
        #========================================
        print('\t Patent-Assignee load', flush=True)
        #===========================================
        #----------------------------------------
        #   patent assignee data from Patent View
        #----------------------------------------
        if ('patent_assignee.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            patent_assignee = pd.read_csv(PatentsView_directory + '/patent_assignee.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
            #patent_assignee = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\patent_assignee.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load patent_assignee data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/patent_assignee.tsv.zip")
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            patent_assignee = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)


        patent_assignee['patent_id'] = pd.to_numeric(patent_assignee.patent_id,
                                                     downcast = 'integer', errors = 'coerce')

        #patent_assignee['patent_id'].notna().value_counts()
        #(patent_assignee['patent_id']!='').value_counts()
        # -> both all true

        #========================================
        print('\t Assignee data load', flush=True)
        #===========================================
        #----------------------------------------
        #   assignee data from Patent View
        #----------------------------------------
        if ('assignee.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            assignee = pd.read_csv(PatentsView_directory + '/assignee.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
            #assignee = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\assignee.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load assignee data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/assignee.tsv.zip")
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            assignee = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        #assignee.type.value_counts(normalize=True)
        # =============================================================================
        # 3.0     0.478475
        # 2.0     0.416876
        # 4.0     0.056935
        # 5.0     0.040942
        # 14.0    0.003451
        # 7.0     0.001341
        # 15.0    0.000643
        # 6.0     0.000475
        # 12.0    0.000372
        # 13.0    0.000273
        # 0.0     0.000149
        # 9.0     0.000040
        # 8.0     0.000023
        # 1.0     0.000004
        # 17.0    0.000004
        # Name: type, dtype: float64
        # =============================================================================
        # => following PatentsView (https://patentsview.org/download/data-download-dictionary), type 2 is US corporation
        # Partial interest (signified by 1 before 2) is very marginal, thus exclude
        assignee_company = assignee[assignee.type==2].drop(
            ['type', 'name_first', 'name_last'], axis=1).rename(columns={'id':'assignee_id'})

        # Limit to patents assigned to companies
        patent_company_assignee = patent_assignee.merge(assignee_company, on='assignee_id', how='inner')

        patent_company_assignee = patent_company_assignee[
            (patent_company_assignee['patent_id'].notna())&(patent_company_assignee['patent_id']!='')]
        #(patent_company_assignee['patent_id'].notna()).value_counts()
        # => many NA values

        #patent_company_assignee.patent_id.value_counts().value_counts(normalize=True)
        #1    9.903179e-01
        #2    9.114182e-03
        #3    5.193212e-04
        #4    4.195251e-05
        #5    5.085152e-06
        #6    6.356441e-07
        #7    6.356441e-07
        #9    3.178220e-07
        #Name: patent_id, dtype: float64
        # => 99% of company assignees are unique

        patent_company_assignee = patent_company_assignee.drop_duplicates(['patent_id'])

        #========================================
        print('\t Persistent Assignee Disambuguation load', flush=True)
        #----------------------------------------
        #   persistent_assignee_disambigation Data from Patent View
        #----------------------------------------
        if ('persistent_assignee_disambig.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            persistent_assignee_disambig = pd.read_csv(PatentsView_directory + '/persistent_assignee_disambig.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load ipcr data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r'https://s3.amazonaws.com/data.patentsview.org/download/persistent_assignee_disambig.tsv.zip')
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            persistent_assignee_disambig = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #========================================
        print('\t Raw Assignee Data load', flush=True)
        #----------------------------------------
        #   rawassignee Data from Patent View
        #----------------------------------------
        if ('rawassignee.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            rawassignee = pd.read_csv(PatentsView_directory + '/rawassignee.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load ipcr data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r'https://s3.amazonaws.com/data.patentsview.org/download/rawassignee.tsv.zip')
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            rawassignee = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        # Merge with persistent bridge and take vintage disamb_assignee_id_20200929 for permanent link
        persistent_assignee = rawassignee[['uuid', 'assignee_id']].merge(
            persistent_assignee_disambig[['rawassignee_id', 'disamb_assignee_id_20200929']],
            left_on='uuid', right_on='rawassignee_id', how='inner').\
            drop(['uuid'], axis=1).drop_duplicates('assignee_id')

        #persistent_assignee.disamb_assignee_id_20200929.value_counts().value_counts(normalize=True).head()
        #1    0.987541
        #2    0.008089
        #3    0.001816
        #4    0.000828
        #5    0.000404
        #Name: disamb_assignee_id_20200929, dtype: float64
        # => little difference, once duplicates are removed
        #========================================
        print('\t IPC patent class load', flush=True)
        #----------------------------------------
        #   IPCR Data from Patent View
        #----------------------------------------
        if ('ipcr.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            print('\t\t Load from directory', flush=True)
            ipcr = pd.read_csv(PatentsView_directory + '/ipcr.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
            #ipcr = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\ipcr.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, nrows=1000000, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load ipcr data from Patent View

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/ipcr.tsv.zip")
                if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break
            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            ipcr = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #-------------------------------------
        # Define different classificaiton level (setting to nan if concatination on the level is na)
        ipcr['section'] = ipcr['section'].astype(str)

        ipcr['class'] = ipcr['section'].astype(str)+\
            ipcr['ipc_class'].astype(str).apply(lambda x: x.split('.')[0].zfill(2))
        ipcr['class'] = np.where(ipcr['ipc_class'].isna(), np.nan, ipcr['class'])

        ipcr['sub_class'] = ipcr['class']+ipcr['subclass'].astype(str)
        ipcr['sub_class'] = np.where(ipcr['subclass'].isna(), np.nan, ipcr['sub_class'])

        ipcr['maingroup'] = ipcr['sub_class']+\
            ipcr['main_group'].astype(str).apply(lambda x: x.split('.')[0].zfill(3))
        ipcr['maingroup'] = np.where(ipcr['main_group'].isna(), np.nan, ipcr['maingroup'])

        # Cast id to int
        ipcr['patent_id'] = pd.to_numeric(ipcr.patent_id,
                                          downcast='integer', errors='coerce')

        # Drop unneeded columns
        ipcr = ipcr[['patent_id', 'section', 'class', 'sub_class', 'maingroup', 'sequence']].drop_duplicates()

        ipcr = ipcr[(ipcr['patent_id'].notna())&(ipcr['patent_id']!='')]

        #ipcr.subclass.isnull().value_counts()
        #========================================================
        # define primary ipc group as sequence 0:
        primary_ipcr = ipcr[ipcr.sequence==0].drop('sequence', axis=1)

        # remove NA values and concatenate to single entry per patent
        #(class level has similar granularity as uspc, if section is empty, though, than no class can be reasonably defined)
        primary_ipcr = primary_ipcr[primary_ipcr['section'].notna()]

        primary_ipcr = primary_ipcr[(primary_ipcr['patent_id'].notna())&(primary_ipcr['patent_id']!='')]


        #========================================
        print('\t KPSS data load', flush=True)
        KPSS_public = pd.read_csv(source_directory + '//KPSS 2020 data//KPSS_2020_public.csv', low_memory=False)
        KPSS_public['issue_date_kpss_dt'] = pd.to_datetime(KPSS_public['issue_date'], format='%m/%d/%Y')
        KPSS_public['issue_year_kpss'] = KPSS_public.issue_date_kpss_dt.dt.year
        KPSS_public['filing_date_kpss_dt'] = pd.to_datetime(KPSS_public['filing_date'], format='%m/%d/%Y')
        KPSS_public['filing_year_kpss'] = KPSS_public.filing_date_kpss_dt.dt.year
        KPSS_public['patent_id'] = pd.to_numeric(KPSS_public.patent_num,
                                                 downcast = 'integer', errors = 'coerce')

        # !!! Note that the issue dates of the cited patents in uspatentcitations is
        # the normalized to be the first day of the issue month
        KPSS_public['issue_date_dt_month_kpss'] = KPSS_public['issue_date_kpss_dt'] + pd.offsets.MonthBegin(0)


        #KPSS_public['in_uspc'] = KPSS_public.apply(lambda x: bool(x.grant_doc_num in (list(set(uspc_current.patent_id.to_list())))), axis=1)

        kpss_merge = KPSS_public[
            ['patent_id', 'xi_real',
             'xi_nominal', 'cites',
             'filing_date_kpss_dt', 'issue_date_kpss_dt',
             'filing_year_kpss', 'issue_year_kpss',
             'issue_date_dt_month_kpss']
            ].drop_duplicates()

        #------------------------------
        # Merge with citations data and remove NA values

        kpss_merge = kpss_merge.rename(columns={'grant_doc_num':'patent_id'})
        kpss_merge = kpss_merge[(kpss_merge['patent_id'].notna())&(kpss_merge['patent_id']!='')]

        #========================================
        # Forward citation construction
        print('\t US Patent citation load', flush=True)
        #----------------------------------------
        #   Citation Data from Patent View
        #----------------------------------------
        if ('uspatentcitation.tsv' in os.listdir(PatentsView_directory)):
                print('\t\t Load from directory', flush=True)
                #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                # Local
                uspatentcitation = pd.read_csv(PatentsView_directory + '/uspatentcitation.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
                #uspatentcitation = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent_distribution_construction\Data\PatentsView_raw_data\uspatentcitation.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, nrows=1e6, low_memory=False)
        else:
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Load citation data from economic research dataset

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/uspatentcitation.tsv.zip" , stream=True)
                if (r.ok == True) & \
                       (len(r.content) == int(r.headers['Content-Length'])):
                       break

            z = zipfile.ZipFile(BytesIO(r.content))
            z.extractall(PatentsView_directory)

            uspatentcitation = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #--------------------------------------
        # Drop unimportant identifiers
        uspatentcitation = uspatentcitation.drop(['uuid'], axis=1)
        #uspatentcitation.citation_id = uspatentcitation.citation_id.astype(str).\
        #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
        #uspatentcitation.patent_id = uspatentcitation.patent_id.astype(str).\
        #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
        uspatentcitation['citation_id'] = pd.to_numeric(uspatentcitation.citation_id,
                                                        downcast = 'integer', errors = 'coerce')
        uspatentcitation['patent_id'] = pd.to_numeric(uspatentcitation.patent_id,
                                                        downcast = 'integer', errors = 'coerce')

        uspatentcitation = uspatentcitation[
            (uspatentcitation['patent_id'].notna())&(uspatentcitation['patent_id']!='') &\
                (uspatentcitation['citation_id'].notna())&(uspatentcitation['citation_id']!='') &\
                    (uspatentcitation['patent_id']!=uspatentcitation['citation_id'])]
        #------------------------------------------
        # Limit to patent citations
        # CAVEAT: According to documentation (see https://www.uspto.gov/learning-and-resources/support-centers/electronic-business-center/kind-codes-included-uspto-patent)
        # Reexamination certificates had the codes B1 and B2 before 2001,
        # while patents since Jan. 2001 have codes B1 and B2, and patent had the code A before Jan. 2001

        #=> date: first day of the month the cited patent (citation_id) was granted
        uspatentcitation['date_dt'] = pd.to_datetime(uspatentcitation['date'], errors='coerce')
        uspatentcitation['issue_date_cited_dt_month'] = uspatentcitation['date_dt'] + pd.offsets.MonthBegin(0)

        uspatentcitation = uspatentcitation[uspatentcitation.kind.isin(['A', 'B1', 'B2'])]
        uspatentcitation = uspatentcitation[~((uspatentcitation.kind.isin(['B1', 'B2'])) & \
                                              (uspatentcitation.date_dt < np.datetime64('2001-01-02')))]

        print('\t\t Unconditional Forward citations received.', flush=True)
        citations = uspatentcitation[['citation_id', 'patent_id']].\
                drop_duplicates().groupby(['citation_id']).size().reset_index(drop=False).\
                    rename(columns={0:'forward_citations',
                                    'citation_id':'patent_id'})

        #---------------------------------------
        # Merge in issue and assigneed data to ensure to know when citation occured
        patent_citation_merge = patent_company_assignee[
            ['patent_id', 'assignee_id']].drop_duplicates()

        patent_citation_with_assignee = uspatentcitation.merge(
            patent_citation_merge,
            how='left',
            on='patent_id')

        patent_citation_merge_cited = patent_citation_merge.add_suffix('_cited')
        patent_citation_merge_cited = patent_citation_merge_cited.\
            rename(columns={'patent_id_cited':'citation_id'})


        patent_citation_with_assignee = patent_citation_with_assignee.merge(
            patent_citation_merge_cited,
            how='left',
            on='citation_id')

        external_citation_df = patent_citation_with_assignee[
            (patent_citation_with_assignee.assignee_id != patent_citation_with_assignee.assignee_id_cited) & \
            (patent_citation_with_assignee.assignee_id.notna()) & (patent_citation_with_assignee.assignee_id_cited.notna()) & \
            (patent_citation_with_assignee.assignee_id!='') & (patent_citation_with_assignee.assignee_id_cited!='')
            ]

        print('\t\t External/non-self citations received.', flush=True)
        external_citations = external_citation_df[['citation_id', 'patent_id']].\
            drop_duplicates().groupby(['citation_id']).size().reset_index(drop=False).\
                rename(columns={0:'external_forward_citations',
                                'citation_id':'patent_id'})


        # =============================================================================
        # Merge and output
        # =============================================================================
        print('\t Merge and Save PatentsView data', flush=True)

        #--------------------------------------------------
        # -> all data merged with are unique
        patent_df = patent.merge(
            application[['app_id', 'patent_id', 'app_number', 'filing_date_dt', 'filing_year']],
            on='patent_id', how='left')

        patent_df = patent_df.merge(
            primary_ipcr, on='patent_id', how='left')

        patent_df = patent_df.merge(
            patent_company_assignee,
            on='patent_id', how='left').merge(
                persistent_assignee,
                on='assignee_id', how='left')

        patent_df = patent_df.merge(
            kpss_merge, on='patent_id', how='left')

        patent_df = patent_df.merge(
            citations, on='patent_id', how='left').merge(
                external_citations, on='patent_id', how='left')

        #=> need patent_df to have reference to merge citation data into
        #--------------------------------------------------------------------
        print('\t\t Forward citations relative to sub_class and filing year.', flush=True)
        # Follow Balsmeier et al. (2017)

        # IPCR subclasses are similar in granularity to the USPC classes used in
        # Balsmeier et al. 2017
        class_type = 'sub_class'

        patent_citation_with_ipcr = patent_df[
            ['patent_id', class_type, 'filing_year', 'forward_citations', 'external_forward_citations']
            ].drop_duplicates()

        # Fill zero citations
        patent_citation_with_ipcr['forward_citations'] = patent_citation_with_ipcr['forward_citations'].fillna(value=0)
        patent_citation_with_ipcr['external_forward_citations'] = patent_citation_with_ipcr['external_forward_citations'].fillna(value=0)

        q1percent = lambda x: x.quantile(0.99)
        q10percent = lambda x: x.quantile(0.90)

        patent_ipc_group_data_forward_cite = patent_citation_with_ipcr.\
                groupby(['filing_year', class_type]).agg(q1percent_forward_cites = ('forward_citations', q1percent),
                                                         q10percent_forward_cites = ('forward_citations', q10percent),
                                                         q1percent_external_forward_cites = ('external_forward_citations', q1percent),
                                                         q10percent_external_forward_cites = ('external_forward_citations', q10percent)).\
                    reset_index()

        # merge with main dataframe
        patent_complete_with_forward_citations_local_class_type = patent_citation_with_ipcr.merge(
            patent_ipc_group_data_forward_cite,
            on=['filing_year', class_type],
            how='left')

        #****************************************************************
        # Define categories for patent
        patent_complete_with_forward_citations_local_class_type['top1_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.forward_citations>0) &\
            (patent_complete_with_forward_citations_local_class_type.forward_citations>=\
             patent_complete_with_forward_citations_local_class_type.q1percent_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['top10_to_2_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.forward_citations>0) &\
             (patent_complete_with_forward_citations_local_class_type.forward_citations>=\
              patent_complete_with_forward_citations_local_class_type.q10percent_forward_cites) &\
             (patent_complete_with_forward_citations_local_class_type.forward_citations<\
              patent_complete_with_forward_citations_local_class_type.q1percent_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['cited_patent_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.forward_citations>0) &\
             (patent_complete_with_forward_citations_local_class_type.forward_citations<\
              patent_complete_with_forward_citations_local_class_type.q10percent_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['Uncited_patent_forward_citations'] = \
            (patent_complete_with_forward_citations_local_class_type.forward_citations==0).astype(int)

        # Define quartiles
        patent_complete_with_forward_citations_local_class_type[
            'forward_citations_quartile'] = patent_complete_with_forward_citations_local_class_type.\
            groupby(['filing_year', class_type])['forward_citations'].\
                transform(lambda x: pd.qcut(x, q=4, duplicates='drop', labels=False)+1)

        #****************************************************************
        # Define categories for patent
        patent_complete_with_forward_citations_local_class_type['top1_external_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.external_forward_citations>0) &\
            (patent_complete_with_forward_citations_local_class_type.external_forward_citations>=\
             patent_complete_with_forward_citations_local_class_type.q1percent_external_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['top10_to_2_external_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.external_forward_citations>0) &\
             (patent_complete_with_forward_citations_local_class_type.external_forward_citations>=\
              patent_complete_with_forward_citations_local_class_type.q10percent_external_forward_cites) &\
             (patent_complete_with_forward_citations_local_class_type.external_forward_citations<\
              patent_complete_with_forward_citations_local_class_type.q1percent_external_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['cited_patent_external_forward_citations'] = \
            ((patent_complete_with_forward_citations_local_class_type.external_forward_citations>0) &\
             (patent_complete_with_forward_citations_local_class_type.external_forward_citations<\
              patent_complete_with_forward_citations_local_class_type.q10percent_external_forward_cites)).astype(int)

        patent_complete_with_forward_citations_local_class_type['Uncited_patent_external_forward_citations'] = \
            (patent_complete_with_forward_citations_local_class_type.external_forward_citations==0).astype(int)

        # Define quartiles
        patent_complete_with_forward_citations_local_class_type[
            'external_forward_citations_quartile'] = patent_complete_with_forward_citations_local_class_type.\
            groupby(['filing_year', class_type])['external_forward_citations'].\
                transform(lambda x: pd.qcut(x, q=4, duplicates='drop', labels=False)+1)


        # =============================================================================
        # cond=(patent_complete_with_forward_citations_local_class_type[['top1_cites', 'top10_to_2_cites', 'cited_patent_cites', 'Uncited_patent_cites']].sum(axis=1)>1)
        # patent_complete_with_forward_citations_local_class_type[cond]
        #
        # cond=(patent_complete_with_forward_citations_local_class_type[['top1_forward_citations', 'top10_to_2_forward_citations', 'cited_patent_forward_citations', 'Uncited_patent_forward_citations']].sum(axis=1)>1)
        # patent_complete_with_forward_citations_local_class_type[cond]
        # =============================================================================

        patent_complete_with_forward_citations_local_class_type = patent_complete_with_forward_citations_local_class_type.\
            drop(['filing_year', class_type], axis=1).\
                rename(columns={'forward_citations':'forward_citations_zero',
                                'external_forward_citations':'external_forward_citations_zero'})

        # rename and merge back into main df
        patent_df = patent_df.merge(
            patent_complete_with_forward_citations_local_class_type,
            on='patent_id',
            how='left')

        #------------------------------------------------------------

        # Merge with Alice assignment data
        patent_alice_assignments = pd.merge(patent_df, patent_class,
                                            on='patent_id',
                                            how='left')

        print('\t\t Test distribution of patent_id in patent data:', flush=True)
        print(patent_alice_assignments.patent_id.value_counts().value_counts(), flush=True)

        del uspatentcitation, external_citation_df, patent_citation_with_assignee
        del ipcr, assignee, patent_assignee, patent, application
        del persistent_assignee, rawassignee, persistent_assignee_disambig
        del patent_complete_with_forward_citations_local_class_type, patent_citation_with_ipcr, patent_ipc_group_data_forward_cite
        #---------------------------------------------
        print('Checkpoint 1', flush=True)
        #---------------------------------------------
        # Intermediate Save: Checkpoint 1
        patent_alice_assignments.to_csv(
            output_directory+'//PatentsView_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv',
            index=False, encoding='utf-8')
    else:
        print('Checkpoint 1 found in home directory, load', flush=True)
        #============================================
        patent_alice_assignments = pd.read_csv(
            output_directory+'//PatentsView_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv',
            encoding='utf-8', low_memory=False)

    #---------------------------------------------
    # Post loading Typecasting and editing

    # Remove unneeded column
    patent_alice_assignments = patent_alice_assignments.drop(
        ['id', 'type', 'number', 'country', 'date', 'abstract', 'title', 'kind', 'filename', 'withdrawn',
         'issue_quarter', 'app_id', 'app_number', 'section', 'class', 'location_id',
         'filing_date_kpss_dt', 'issue_date_kpss_dt', 'filing_year_kpss',
         'issue_year_kpss', 'issue_date_dt_month_kpss',
         'q1percent_forward_cites', 'q10percent_forward_cites',
         'q1percent_external_forward_cites', 'q10percent_external_forward_cites'], axis=1)

    # Limit to years after USPTO provided data on issued patents, that is 1976
    patent_alice_assignments = patent_alice_assignments[patent_alice_assignments.issue_year>=1976]

    patent_alice_assignments['issue_date_dt'] = pd.to_datetime(patent_alice_assignments['issue_date_dt'], errors='coerce')
    patent_alice_assignments['filing_date_dt'] = pd.to_datetime(patent_alice_assignments['filing_date_dt'], errors='coerce')

    gc.collect()

    # %%
    ################################################################
    #   Section 2: Patent Portfolio Aggregation                    #
    ################################################################

    def _patentportfolio_state_construction(portfolio_output_directory,
                                            patent_alice_assignments,
                                            year_count,
                                            exec_identifier,
                                            dep_rate,
                                            key_variable,
                                            Alice_prediction_indicator,
                                            execution_limit=20,
                                            annual=False):
        r'''
        METHOD: Construct patent portfolios for executions up to beginning of year_count
                from patent_assignments df, aggregate by key_variable.
                If annual=True, only account for execution year.
                !!! Reference date for the portfolio variante is the last day of the previous
                year, for the current year it is the end of the current year

        INPUT: - portfolio_output_directory: str with output path
               - patent_alice_assignments: df bas dataframe for execution
               - year_count: int with execution year
               - exec_identifier: str identifying for the time variable to use (filing or issue date)
               - dep_rate: double annual depreciation rate applied to patent count and citations for patent stock
               - key_variabe: str with firm identifier to aggregation
               - Alice_prediction_indicator: str with column name of binary value being 1 for affected and zero o.w.
               - execution_limit: int for how long back executions should go (only for annual==False), in years
               - annual: bool if True, only aggregate for executions in year_count,
                              if False, aggregate for all application filed 20 year prior to
                               year_count beginning and assignments up to
                               'execution_limit' years before year_count,
                               based on construction basis in exec_identifier
        RETURN: patent_portfolio: DF with aggregate patent assignment variables for year(/quarter)/key_variable
                pivoted_count: DF with count of patent class assignments per key_variable in time frame of assignments
        r'''

        print('\t Patent portfolio construction for key {0} and \n \
              \t year {1}, annual: {2}, execution limit: {3}, \n \
              \t Alice prediction base: {4}, \n \
              \t year counting basis: {5}, \n \
              \t depreciation rate: {6}'.\
              format(key_variable, year_count, annual, execution_limit,
                     Alice_prediction_indicator, exec_identifier, dep_rate), flush=True)
        #**********************************************
        # Define if only look for per year assignments, or aggregate up to end of year
        if annual==False:
            patent_state_assignments = patent_alice_assignments.loc[
                (patent_alice_assignments[exec_identifier + '_year'] < year_count) & \
                    (patent_alice_assignments['filing_year'] >= (year_count - 20)) &\
                        (patent_alice_assignments[exec_identifier+'_year'] >= (year_count-execution_limit))
                        ]
            reference_date = np.datetime64(str(year_count-1) + '-12-31')
        else:
            patent_state_assignments = patent_alice_assignments.loc[
                (patent_alice_assignments[exec_identifier + '_year'] == year_count)]

            reference_date = np.datetime64(str(year_count) + '-12-31')

        #**********************************************
        # Type conversion of dates
        patent_state_assignments['issue_date_dt'] = pd.to_datetime(patent_state_assignments['issue_date_dt'],
                                                                errors='coerce')
        patent_state_assignments['filing_date_dt'] = pd.to_datetime(patent_state_assignments['filing_date_dt'],
                                                                   errors='coerce')

        #**********************************************
        #**********************************************
        # Calculate Age of Patent, proxy for how long the data generating process was protected

        # Impose constraint to be postitive
        patent_state_assignments['patent_age_days'] = reference_date - patent_state_assignments.issue_date_dt
        patent_state_assignments['patent_age'] = patent_state_assignments['patent_age_days'].apply(lambda x: x.days/365.25)
        patent_state_assignments['patent_age_years'] = patent_state_assignments['patent_age_days'].apply(lambda x: np.floor(x.days/365.25))

        patent_state_assignments['patent_age_application_days'] = reference_date - patent_state_assignments.filing_date_dt
        patent_state_assignments['patent_age_application'] = patent_state_assignments['patent_age_application_days'].apply(lambda x: x.days/365.25)
        patent_state_assignments['patent_age_application_years'] = patent_state_assignments['patent_age_application_days'].apply(lambda x: np.floor(x.days/365.25))

        patent_state_assignments['patent_time_to_grant_days'] = patent_state_assignments.issue_date_dt - patent_state_assignments.filing_date_dt
        patent_state_assignments['patent_time_to_grant'] = patent_state_assignments['patent_time_to_grant_days'].apply(lambda x: x.days/365.25)
        patent_state_assignments['patent_time_to_grant_years'] = patent_state_assignments['patent_time_to_grant_days'].apply(lambda x: np.floor(x.days/365.25))

        #**********************************************
        #**********************************************
        # Remove irrational values with application date after grant date
        patent_state_assignments = patent_state_assignments[~(patent_state_assignments.filing_date_dt > patent_state_assignments.issue_date_dt)]

        # Remove negative age values
        patent_state_assignments['patent_age'] = np.where(
            patent_state_assignments['patent_age']<0, np.nan, patent_state_assignments['patent_age'])            
        patent_state_assignments['patent_age_years'] = np.where(
            patent_state_assignments['patent_age_years']<0, np.nan, patent_state_assignments['patent_age_years'])
        # => application age should not be negative; controlling for filing occuring before issuance
        # and the refence period being the last possible day for filing and issuance, this number must be non-negative

        #**********************************************
        #***********************************************
        # Depreciation granted patents

        patent_state_assignments['depreciated_patent_count'] = (1-dep_rate)**patent_state_assignments['patent_age_years']

        #**********************************************
        #***********************************************
        # Define citation weights by filling forward citations with zeros
        patent_state_assignments['forward_citations_zero'] = patent_state_assignments.forward_citations.fillna(0)
        patent_state_assignments['external_forward_citations_zero'] = patent_state_assignments.external_forward_citations.fillna(0)

        # Depreciate forward citations
        patent_state_assignments['depreciated_patent_forward_citations'] = \
            patent_state_assignments['forward_citations_zero'] * (1-dep_rate)**patent_state_assignments['patent_age_years']
        patent_state_assignments['depreciated_patent_external_forward_citations'] = \
            patent_state_assignments['external_forward_citations_zero'] * (1-dep_rate)**patent_state_assignments['patent_age_years']


        #**********************************************
        # Define additional variables
        patent_state_assignments['Alice_affected'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), 1, 0)

        patent_state_assignments['Alice_affected_patent_age'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_age, np.nan)
        patent_state_assignments['Alice_affected_patent_age_application'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_age_application, np.nan)
        patent_state_assignments['Alice_affected_patent_time_to_grant'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_time_to_grant, np.nan)

        patent_state_assignments['Alice_affected_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.forward_citations_zero, np.nan)
        patent_state_assignments['Alice_affected_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.external_forward_citations_zero, np.nan)

        patent_state_assignments['Alice_affected_top1_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.top1_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_top10_to_2_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.top10_to_2_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_cited_patent_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.cited_patent_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_Uncited_patent_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.Uncited_patent_forward_citations, np.nan)

        patent_state_assignments['Alice_affected_top1_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.top1_external_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_top10_to_2_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.top10_to_2_external_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_cited_patent_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.cited_patent_external_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_Uncited_patent_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.Uncited_patent_external_forward_citations, np.nan)


        patent_state_assignments['Alice_affected_depreciated_patent_count'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_patent_count, np.nan)
        patent_state_assignments['Alice_affected_depreciated_patent_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_patent_forward_citations, np.nan)
        patent_state_assignments['Alice_affected_depreciated_patent_external_forward_citations'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_patent_external_forward_citations, np.nan)

        #--------------------------------------------
        # Additional labels for affected predicted patents
        patent_state_assignments['Alice_predicted_affected_patent_age'] = patent_state_assignments['Alice_affected_patent_age'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_patent_age_application'] = patent_state_assignments['Alice_affected_patent_age_application'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_patent_time_to_grant'] = patent_state_assignments['Alice_affected_patent_time_to_grant'] * patent_state_assignments[Alice_prediction_indicator]

        patent_state_assignments['Alice_predicted_affected_forward_citations'] = patent_state_assignments['forward_citations_zero'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_external_forward_citations'] = patent_state_assignments['external_forward_citations_zero'] * patent_state_assignments[Alice_prediction_indicator]

        patent_state_assignments['Alice_predicted_affected_top1_forward_citations'] = patent_state_assignments['top1_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_top10_to_2_forward_citations'] = patent_state_assignments['top10_to_2_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_cited_patent_forward_citations'] = patent_state_assignments['cited_patent_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_Uncited_patent_forward_citations'] = patent_state_assignments['Uncited_patent_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]

        patent_state_assignments['Alice_predicted_affected_top1_external_forward_citations'] = patent_state_assignments['top1_external_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_top10_to_2_external_forward_citations'] = patent_state_assignments['top10_to_2_external_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_cited_patent_external_forward_citations'] = patent_state_assignments['cited_patent_external_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_Uncited_patent_external_forward_citations'] = patent_state_assignments['Uncited_patent_external_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]

        patent_state_assignments['Alice_predicted_affected_depreciated_patent_count'] = patent_state_assignments['depreciated_patent_count'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_depreciated_patent_forward_citations'] = patent_state_assignments['depreciated_patent_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_depreciated_patent_external_forward_citations'] = patent_state_assignments['depreciated_patent_external_forward_citations'] * patent_state_assignments[Alice_prediction_indicator]

        #**********************************************
        # Aggregate
        patent_portfolio = patent_state_assignments.groupby([key_variable]).agg(
            # Alice variables
            Alice_affected=("Alice_affected", 'sum'),
            Alice_predicted_affected=(Alice_prediction_indicator, 'sum'),

            Alice_affected_mean_pred=("Alice_proba_predict_patent_average", 'mean'),

            #*****************************************************************
            Alice_affected_patent_age=('Alice_affected_patent_age', 'mean'),
            Alice_affected_patent_age_application=('Alice_affected_patent_age_application', 'mean'),
            Alice_affected_patent_time_to_grant=('Alice_affected_patent_time_to_grant', 'mean'),

            Alice_affected_forward_citations=('Alice_affected_forward_citations', 'sum'),
            Alice_affected_external_forward_citations=('Alice_affected_external_forward_citations', 'sum'),

            Alice_affected_top1_forward_citations=('Alice_affected_top1_forward_citations','sum'),
            Alice_affected_top10_to_2_forward_citations=('Alice_affected_top10_to_2_forward_citations','sum'),
            Alice_affected_cited_patent_forward_citations=('Alice_affected_cited_patent_forward_citations','sum'),
            Alice_affected_Uncited_patent_forward_citations=('Alice_affected_Uncited_patent_forward_citations','sum'),

            Alice_affected_top1_external_forward_citations=('Alice_affected_top1_external_forward_citations','sum'),
            Alice_affected_top10_to_2_external_forward_citations=('Alice_affected_top10_to_2_external_forward_citations','sum'),
            Alice_affected_cited_patent_external_forward_citations=('Alice_affected_cited_patent_external_forward_citations','sum'),
            Alice_affected_Uncited_patent_external_forward_citations=('Alice_affected_Uncited_patent_external_forward_citations','sum'),

            Alice_affected_depreciated_patent_count=('Alice_affected_depreciated_patent_count', 'sum'),
            Alice_affected_depreciated_patent_forward_citations=('Alice_affected_depreciated_patent_forward_citations', 'sum'),
            Alice_affected_depreciated_patent_external_forward_citations=('Alice_affected_depreciated_patent_external_forward_citations', 'sum'),

            #*****************************************************************
            Alice_predicted_affected_patent_age=('Alice_predicted_affected_patent_age', 'mean'),
            Alice_predicted_affected_patent_age_application=('Alice_predicted_affected_patent_age_application', 'mean'),
            Alice_predicted_affected_patent_time_to_grant=('Alice_predicted_affected_patent_time_to_grant', 'mean'),

            Alice_predicted_affected_forward_citations=('Alice_predicted_affected_forward_citations', 'sum'),
            Alice_predicted_affected_external_forward_citations=('Alice_predicted_affected_external_forward_citations', 'sum'),

            Alice_predicted_affected_top1_forward_citations=('Alice_predicted_affected_top1_forward_citations','sum'),
            Alice_predicted_affected_top10_to_2_forward_citations=('Alice_predicted_affected_top10_to_2_forward_citations','sum'),
            Alice_predicted_affected_cited_patent_forward_citations=('Alice_predicted_affected_cited_patent_forward_citations','sum'),
            Alice_predicted_affected_Uncited_patent_forward_citations=('Alice_predicted_affected_Uncited_patent_forward_citations','sum'),

            Alice_predicted_affected_top1_external_forward_citations=('Alice_predicted_affected_top1_external_forward_citations','sum'),
            Alice_predicted_affected_top10_to_2_external_forward_citations=('Alice_predicted_affected_top10_to_2_external_forward_citations','sum'),
            Alice_predicted_affected_cited_patent_external_forward_citations=('Alice_predicted_affected_cited_patent_external_forward_citations','sum'),
            Alice_predicted_affected_Uncited_patent_external_forward_citations=('Alice_predicted_affected_Uncited_patent_external_forward_citations','sum'),

            Alice_predicted_affected_depreciated_patent_count=('Alice_predicted_affected_depreciated_patent_count', 'sum'),
            Alice_predicted_affected_depreciated_patent_forward_citations=('Alice_predicted_affected_depreciated_patent_forward_citations', 'sum'),
            Alice_predicted_affected_depreciated_patent_external_forward_citations=('Alice_predicted_affected_depreciated_patent_external_forward_citations', 'sum'),

            #*****************************************************************
            # Portfolio varables
            total_assignments=("patent_id", 'count'),
            total_forward_citations=("forward_citations_zero", 'sum'),
            total_external_forward_citations=("external_forward_citations_zero", 'sum'),

            total_top1_forward_citations=('top1_forward_citations','sum'),
            total_top10_to_2_forward_citations=('top10_to_2_forward_citations','sum'),
            total_cited_patent_forward_citations=('cited_patent_forward_citations','sum'),
            total_Uncited_patent_forward_citations=('Uncited_patent_forward_citations','sum'),

            total_top1_external_forward_citations=('top1_external_forward_citations','sum'),
            total_top10_to_2_external_forward_citations=('top10_to_2_external_forward_citations','sum'),
            total_cited_patent_external_forward_citations=('cited_patent_external_forward_citations','sum'),
            total_Uncited_patent_external_forward_citations=('Uncited_patent_external_forward_citations','sum'),

            total_claims=('num_claims', 'sum'),
            classified_claims=('classified_claims', 'sum'),
            treated_classified_claims=('treated_classified_claims', 'sum'),

            total_patent_age=('patent_age', 'mean'),
            total_patent_age_application=('patent_age_application', 'mean'),
            total_patent_time_to_grant=('patent_time_to_grant', 'mean'),

            total_depreciated_patent_count=('depreciated_patent_count', 'sum'),
            total_depreciated_patent_forward_citations=('depreciated_patent_forward_citations', 'sum'),
            total_depreciated_patent_external_forward_citations=('depreciated_patent_external_forward_citations', 'sum')

            ).reset_index()

        #**********************************************************
        # Relative variable definition
        patent_portfolio['relative_Alice_affected'] = patent_portfolio['Alice_affected'] / patent_portfolio['total_assignments']
        patent_portfolio['relative_Alice_predicted_affected'] = patent_portfolio['Alice_predicted_affected'] / patent_portfolio['total_assignments']

        patent_portfolio['relative_Alice_affected_patent_age'] = patent_portfolio['Alice_affected_patent_age'] / patent_portfolio['total_patent_age']
        patent_portfolio['relative_Alice_predicted_affected_patent_age'] = patent_portfolio['Alice_predicted_affected_patent_age'] / patent_portfolio['total_patent_age']

        patent_portfolio['relative_Alice_affected_patent_age_application'] = patent_portfolio['Alice_affected_patent_age_application'] / patent_portfolio['total_patent_age_application']
        patent_portfolio['relative_Alice_predicted_affected_patent_age_application'] = patent_portfolio['Alice_predicted_affected_patent_age_application'] / patent_portfolio['total_patent_age_application']

        patent_portfolio['relative_Alice_affected_patent_time_to_grant'] = patent_portfolio['Alice_affected_patent_time_to_grant'] / patent_portfolio['total_patent_time_to_grant']
        patent_portfolio['relative_Alice_predicted_affected_patent_time_to_grant'] = patent_portfolio['Alice_predicted_affected_patent_time_to_grant'] / patent_portfolio['total_patent_time_to_grant']

        patent_portfolio['relative_Alice_affected_forward_citations'] = patent_portfolio['Alice_affected_forward_citations'] / patent_portfolio['total_forward_citations']
        patent_portfolio['relative_Alice_predicted_affected_forward_citations'] = patent_portfolio['Alice_predicted_affected_forward_citations'] / patent_portfolio['total_forward_citations']

        patent_portfolio['relative_Alice_affected_external_forward_citations'] = patent_portfolio['Alice_affected_external_forward_citations'] / patent_portfolio['total_external_forward_citations']
        patent_portfolio['relative_Alice_predicted_affected_external_forward_citations'] = patent_portfolio['Alice_predicted_affected_external_forward_citations'] / patent_portfolio['total_external_forward_citations']

        # Replace infinite value -> should not be necessary
        #patent_portfolio.replace([np.inf, -np.inf], np.nan, inplace=True)
        #******************************************************
        # Add prefix to columns to distinguish annual values
        if annual==True:
            patent_portfolio = patent_portfolio.add_prefix('annual_')
        else:
            patent_portfolio = patent_portfolio.add_prefix('portfolio_annual_')

        #******************************************************
        # Add basis for aggregation, i.e. issue or filing
        patent_portfolio['aggregation_base'] = exec_identifier

        #******************************************************
        patent_portfolio['year'] = year_count
        if annual==False:
            patent_portfolio['execution_limit'] = execution_limit
        else:
            patent_portfolio['execution_limit'] = np.nan

        #****************************************************
        # Add Alice classification basis
        patent_portfolio['Alice_classification_basis'] = Alice_prediction_indicator

        # Add depreciation rate used:
        patent_portfolio['depreciation_rate_basis'] = dep_rate

        #==============================================
        # Save output
        if annual==False:
            patent_portfolio.to_csv(portfolio_output_directory +
                                    '//PatentsView_direct_annual_patent_portfolio_' + str(key_variable) +
                                    '_' + str(output_version) +
                                    '_' + str(year_count) +
                                    '_' + str(exec_identifier) +
                                    '_dep_rate_' + str(dep_rate) +
                                    '_' + str(execution_limit) +
                                    '_' + str(Alice_prediction_indicator) + '.csv',
                                    encoding='utf-8')
        else:
            patent_portfolio.to_csv(portfolio_output_directory +
                                     '//PatentsView_direct_within_annual_patent_assignment_' + str(key_variable) +
                                    '_' + str(output_version) +
                                    '_' + str(year_count) +
                                    '_' + str(exec_identifier) +
                                    '_dep_rate_' + str(dep_rate) +
                                    '_' + str(Alice_prediction_indicator) + '.csv',
                                    encoding='utf-8')

        return(patent_portfolio)



    #########################################

    #*********************************
    #*********************************
    # Construct rolling portfolios

    def _rolling_portfolio_construction_wrapper(id_variable):
        '''Wrapper for annual and portfolio construction for id_variable'''

        # Follow, e.g., Kogan & Papanikolau (2019) and Eisfeld et al. (2020) and set
        # depreciation rate at around 15% (equal to BEA depreciation rate of R&D expenditures)
        dep_rate_current = 0.15

        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        first_year = 1990
        last_year = 2022

        # Iterate through year and create patent portfolios for end of year
        # and aggregate patent assignment for the execution year

        patent_portfolio = pd.DataFrame()
        patent_assignments = pd.DataFrame()

        # Create intermediary saving directory
        portfolio_output_directory = output_directory+'//intermediate_save__' + \
            str(id_variable) + '_' + str(output_version) + '_directory'
        if not os.path.exists(portfolio_output_directory):
            os.makedirs(portfolio_output_directory)

        #r'''
        # Linear Execution
        # =============================================================================
        #  Execution  annual portfolio construction
        # =============================================================================
        for year_iterator in range(first_year, last_year):
            for Alice_classification_iter in ['min_one_Alice_affected', 'most_claims_Alice_affected', 'Alice_mean_proba_predicted_affected', 'first_claim_Alice_affected']:
                for execution_limit_iterator in [5, 10, 20]:
                    for exec_year_iterator in ['filing', 'issue']:
                        patent_append =  _patentportfolio_state_construction(
                            portfolio_output_directory=portfolio_output_directory,
                            patent_alice_assignments=patent_alice_assignments,
                            year_count=year_iterator,
                            exec_identifier=exec_year_iterator,
                            dep_rate=dep_rate_current,
                            key_variable=id_variable,
                            Alice_prediction_indicator=Alice_classification_iter,
                            execution_limit=execution_limit_iterator,
                            annual=False
                            )
                        #-------------------------------------------
                        # append
                        patent_portfolio = patent_portfolio.append(
                            patent_append,
                            ignore_index=True,
                            sort=False)

        # =============================================================================
        #  Execution  annual assignments => itteration limit not relevant
        # =============================================================================
        for year_iterator in range(first_year, last_year):
            for Alice_classification_iter in ['min_one_Alice_affected', 'most_claims_Alice_affected', 'Alice_mean_proba_predicted_affected', 'first_claim_Alice_affected']:
                for exec_year_iterator in ['filing', 'issue']:
                    patent_append = _patentportfolio_state_construction(
                        portfolio_output_directory=portfolio_output_directory,
                        patent_alice_assignments=patent_alice_assignments,
                        year_count=year_iterator,
                        exec_identifier=exec_year_iterator,
                        dep_rate=dep_rate_current,
                        key_variable=id_variable,
                        Alice_prediction_indicator=Alice_classification_iter,
                        execution_limit=-1,
                        annual=True
                        )

                    #-------------------------------------------
                    # append
                    patent_assignments = patent_assignments.append(patent_append,
                                                                   ignore_index=True,
                                                                   sort=False)

        del patent_append
        #r'''
        #======================================================================
        # %% !!! %%%
        r'''
        #======================================================================
        # Parallel Execution
        # =============================================================================
        #  Execution  annual portfolio construction
        # =============================================================================
        # Search for first patent claims
        #cores = mp.cpu_count()
        cores = 5
        print('\t\t Number of Cores: ' + str(cores))

        #----------------------------------------------
        pool = mp.Pool(cores)
        for year_iterator in range(first_year, last_year):
            for Alice_classification_iter in ['min_one_Alice_affected', 'most_claims_Alice_affected', 'Alice_mean_proba_predicted_affected', 'first_claim_Alice_affected']:
                for execution_limit_iterator in [5, 10, 20]:
                    for exec_year_iterator in ['filing', 'issue']:
                        pool.apply_async(
                            _patentportfolio_state_construction,
                            args=(
                                portfolio_output_directory,
                                patent_alice_assignments,
                                year_iterator,
                                exec_year_iterator,
                                dep_rate_current,
                                id_variable,
                                Alice_classification_iter,
                                execution_limit_iterator,
                                False
                                )
                            )
        pool.close()
        pool.join()

        # Load from saved intermediary
        raw_files_list = os.listdir(portfolio_output_directory)
        raw_csv_path = [
            portfolio_output_directory+'//'+f for f in raw_files_list if \
            bool(re.search('PatentsView_direct_annual_patent_portfolio_', f))
            ]

        patent_portfolio = pd.DataFrame()
        for load_file in raw_csv_path:
            patent_append = pd.read_csv(load_file, encoding='utf-8', low_memory=False)

            patent_portfolio = patent_portfolio.append(
                patent_append,
                ignore_index=True,
                sort=False)

        # =============================================================================
        #  Execution  annual assignments => itteration limit not relevant
        # =============================================================================
        # Search for first patent claims
        #cores = mp.cpu_count()
        cores = 5
        print('\t\t Number of Cores: ' + str(cores))

        #----------------------------------------------
        pool = mp.Pool(cores)

        for year_iterator in range(first_year, last_year):
            for Alice_classification_iter in ['min_one_Alice_affected', 'most_claims_Alice_affected', 'Alice_mean_proba_predicted_affected', 'first_claim_Alice_affected']:
                for exec_year_iterator in ['filing', 'issue']:
                    pool.apply_async(
                        _patentportfolio_state_construction,
                        args=(
                            portfolio_output_directory,
                            patent_alice_assignments,
                            year_iterator,
                            exec_year_iterator,
                            dep_rate_current,
                            id_variable,
                            Alice_classification_iter,
                            -1,
                            True
                            )
                        )
        pool.close()
        pool.join()

        # Load from saved intermediary
        raw_files_list = os.listdir(portfolio_output_directory)
        raw_csv_path = [
            portfolio_output_directory+'//'+f for f in raw_files_list if \
            bool(re.search('//PatentsView_direct_within_annual_patent_assignment_', f))
            ]

        patent_assignments = pd.DataFrame()
        for load_file in raw_csv_path:
            patent_append = pd.read_csv(load_file, encoding='utf-8', low_memory=False)

            patent_assignments = patent_assignments.append(
                patent_append,
                ignore_index=True,
                sort=False)

        del patent_append
        r'''
        # =============================================================================
        #  Collect Results and Save output
        # =============================================================================

        #=============================================
        patent_portfolio.to_csv(portfolio_output_directory +
                                 '//PatentsView_direct_annual_patent_portfolio_' + str(id_variable) +
                                 '_' + str(output_version) + '.csv',
                                 encoding='utf-8')
        patent_assignments.to_csv(portfolio_output_directory +
                                 '//PatentsView_direct_within_annual_patent_assignment_' + str(id_variable) +
                                 '_' + str(output_version) + '.csv',
                                 encoding='utf-8')

        return(patent_portfolio, patent_assignments)

    #===============================================
    # assignee_id Aggregating
    #===============================================
    # Define key variables
    patent_portfolio, patent_assignments = _rolling_portfolio_construction_wrapper('assignee_id')

    #-------------------------------------------
    # Output
    #---------------------------------------------
    print('Checkpoint 3, for assignee_id clustering for annual data', flush=True)
    #---------------------------------------------
    # Intermediate Save: Checkpoint 3
    patent_portfolio.to_csv(output_directory+'//PatentsView_direct_patent_portfolio_assignee_id_' + \
                            str(output_version) + '.csv',
                            index=False, encoding='utf-8')
    patent_assignments.to_csv(output_directory+'//PatentsView_direct_annual_patent_assignment_assignee_id_' + \
                              str(output_version) + '.csv',
                              index=False, encoding='utf-8')
    return

#############################################
# Main Execution                            #
#############################################

if __name__ == '__main__':
    # Classification based on PatentsView Controls:
    #-------------------------------------------
    classification_version = 'PatentsViewControls' + str(CLASSIFICATION_ITERATION)

    main(output_version='_cpcAffected_v' + str(VERSION),
         model_specification='cpcAffected__Alice_predicted_TFIDF_poly2__vPatentsViewControls_v' + str(CLASSIFICATION_ITERATION))
             # Patent classification input version and which type of model to be used (i.e. control group)
             # (Patent claims from PatentView classifiction already selected in function, as well as PatentsView as source for controls; see classification_directory)
             # => differentiate between like patents from uspc or cpc classes
             # See Alice_Patent_Claim_Classification_v9.2.py for details

    main(output_version='_uspcAffected_v' + str(VERSION),
         model_specification='uspcAffected__Alice_predicted_TFIDF_poly2__vPatentsViewControls_v' + str(CLASSIFICATION_ITERATION))

r'''
# %%
#############################################
# Local Execution
#############################################
pd.set_option('display.float_format', lambda x: '%.4f' % x)

# Test portfolio construction results and how fit to cleaned assignee name files
patent_pf_df = pd.read_csv(
    r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent Portfolio and Economic Data\Patent_portfolio_construction_results\PatentsView_assignee_id_03122022\PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3.csv",
    nrows=1000000, low_memory=False)

patent_pf_df.describe()

patent_annual_df = pd.read_csv(
    r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Patent Portfolio and Economic Data\Patent_portfolio_construction_results\PatentsView_assignee_id_03122022\PatentsView_direct_annual_patent_assignment_assignee_id__cpcAffected_v1.3.csv",
    nrows=2000000, low_memory=False)


patent_application_df = pd.read_csv(
    r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Census Data Application\Data Upload Kiteworks\Upload 3_10_2022\Data\PatentsView_application_with_org_and_raw_location.csv",
    nrows=1000000, low_memory=False)

patent_assignee_df = pd.read_csv(
    r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Census Data Application\Data Upload Kiteworks\Upload 3_10_2022\Data\PatentsView_patent_assignee_with_org_and_raw_location.csv",
    low_memory=False)

patent_assignee_df.assignee_id

(patent_pf_df.portfolio_annual_assignee_id.isin(patent_assignee_df.assignee_id)).value_counts(normalize=True)
#True    1.0
#Name: portfolio_annual_assignee_id, dtype: float64

(patent_annual_df.annual_assignee_id.isin(patent_assignee_df.assignee_id)).value_counts(normalize=True)
#True    1.0
#Name: annual_assignee_id, dtype: float64

(patent_assignee_df.assignee_id.isin(patent_pf_df.portfolio_annual_assignee_id)).value_counts(normalize=True)
#False    0.703152
#True     0.296848
#Name: assignee_id, dtype: float64

(patent_assignee_df.assignee_id.isin(patent_annual_df.annual_assignee_id)).value_counts(normalize=True)
#False    0.565476
#True     0.434524
#Name: assignee_id, dtype: float64

# => importantly, of this sample, all assignee_id's in the constructed
# patent portfolios are in the assignee dataset

#=================================================
# Create 2014 observation of patent portfolio (save memory space of not having to load entire portfolio DF into R)
patent_portfolio = pd.read_csv(r"/home/dominik_jurek/Patent_Portfolio_based_on_PatentsView_data_1.3/PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3.csv", low_memory=False)
patent_portfolio_2014 = patent_portfolio[patent_portfolio.year==2014]
patent_portfolio_2014.to_csv(r"/home/dominik_jurek/Patent_Portfolio_based_on_PatentsView_data_1.3/PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3__2014_observations.csv", index=False)

# Create also 2010 observation of patent portfolio, selecting on observations before the sequence of invalidation (
#  this conditions already on survival and being a long-term entrant, i.e., survival of at least four year, 
#  as defined by Kerr, Nanda, 2009)
patent_portfolio = pd.read_csv(r"/home/dominik_jurek/Patent_Portfolio_based_on_PatentsView_data_1.3/PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3.csv", low_memory=False)
patent_portfolio_2010 = patent_portfolio[patent_portfolio.year==2010]
patent_portfolio_2010.to_csv(r"/home/dominik_jurek/Patent_Portfolio_based_on_PatentsView_data_1.3/PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3__2010_observations.csv", index=False)


#===============================================
# Merge annual and patent portfolio dataframes based on same aggregation_base, Alice_classification_basis, year, and assignee_id
# Note that the patent portfolio construction also has a time frame for execution_limit

import pandas as pd
import numpy as np
import re
import os


dir_results = r"/home/dominik_jurek/Patent_Portfolio_based_on_PatentsView_data_1.3"

patent_portfolio = pd.read_csv(
    dir_results+"/PatentsView_direct_patent_portfolio_assignee_id__cpcAffected_v1.3.csv", low_memory=False)
patent_portfolio = patent_portfolio.rename(
    columns={'portfolio_annual_assignee_id':'assignee_id'})

# Limit to post 2000
patent_portfolio = patent_portfolio[patent_portfolio.year>=2000]

annual_patent_portfolio = pd.read_csv(
    dir_results+"/PatentsView_direct_annual_patent_assignment_assignee_id__cpcAffected_v1.3.csv", low_memory=False)
annual_patent_portfolio = annual_patent_portfolio.rename(
    columns={'annual_assignee_id':'assignee_id'})

# Limit to post 2000
annual_patent_portfolio = annual_patent_portfolio[annual_patent_portfolio.year>=2000]

portfolio_with_annual_assignments = patent_portfolio.merge(
    annual_patent_portfolio.drop(['execution_limit', 'depreciation_rate_basis'], axis=1), 
    on=['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis'], 
    how='left')

annual_assignments_with_assignments = patent_portfolio.merge(
    annual_patent_portfolio.drop(['execution_limit', 'depreciation_rate_basis'], axis=1), 
    on=['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis'], 
    how='right')


portfolio_with_annual_assignments[['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis']].value_counts().value_counts()
#3    7508976
#1    5013032
#2    3716464
#dtype: int64

annual_assignments_with_assignments[['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis']].value_counts().value_counts()
#3    1894080
#1     861156
#2      89452
#dtype: int64



portfolio_with_annual_assignments[['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis', 'execution_limit']].value_counts().value_counts()
#1    34972888
#dtype: int64

annual_assignments_with_assignments[['year', 'assignee_id', 'aggregation_base', 'Alice_classification_basis', 'execution_limit']].value_counts().value_counts()
# -> unique

portfolio_with_annual_assignments_issue_min_one = portfolio_with_annual_assignments[
    (portfolio_with_annual_assignments.aggregation_base=='issue') & \
        (portfolio_with_annual_assignments.Alice_classification_basis=='min_one_Alice_affected')]

portfolio_with_annual_assignments_filing_min_one = portfolio_with_annual_assignments[
    (portfolio_with_annual_assignments.aggregation_base=='filing') & \
        (portfolio_with_annual_assignments.Alice_classification_basis=='min_one_Alice_affected')]    
    
portfolio_with_annual_assignments_issue_first_claim = portfolio_with_annual_assignments[
    (portfolio_with_annual_assignments.aggregation_base=='issue') & \
        (portfolio_with_annual_assignments.Alice_classification_basis=='first_claim_Alice_affected')]

    
    
annual_assignments_with_assignments_issue_min_one = annual_assignments_with_assignments[
    (annual_assignments_with_assignments.aggregation_base=='issue') & \
        (annual_assignments_with_assignments.Alice_classification_basis=='min_one_Alice_affected')]    

annual_assignments_with_assignments_issue_first_claim = annual_assignments_with_assignments[
    (annual_assignments_with_assignments.aggregation_base=='issue') & \
        (annual_assignments_with_assignments.Alice_classification_basis=='first_claim_Alice_affected')]
    
    
    
    
portfolio_with_annual_assignments.to_csv(
    dir_results+"/Joined_post_2000__PatentsView_direct_assignee_id__cpcAffected_v1.3.csv",
    index=False
    )

portfolio_with_annual_assignments_issue_min_one.to_csv(
    dir_results+"/Joined_issue_min_one_post_2000__PatentsView_direct_assignee_id__cpcAffected_v1.3.csv",
    index=False
    )

portfolio_with_annual_assignments_filing_min_one.to_csv(
    dir_results+"/Joined_filing_min_one_post_2000__PatentsView_direct_assignee_id__cpcAffected_v1.3.csv",
    index=False
    )

portfolio_with_annual_assignments_issue_first_claim.to_csv(
    dir_results+"/Joined_issue_first_claim_post_2000__PatentsView_direct_assignee_id__cpcAffected_v1.3.csv",
    index=False
    )



annual_assignments_with_assignments_issue_min_one.to_csv(
    dir_results+"/Joined_PatentsView_assignment_with_portfolio__issue_min_one_post_2000__cpcAffected_v1.3.csv",
    index=False
    )

annual_assignments_with_assignments_issue_first_claim.to_csv(
    dir_results+"/Joined_PatentsView_assignment_with_portfolio__issue_first_claim_post_2000__cpcAffected_v1.3.csv",
    index=False
    )


#-----------------------------------------------
# Create assignees in states with anti troll laws
# Define assigness is states that are affected by Anti-troll laws, following
# Appel et al. 2019 and their list of states according to the Working Paper appendix

anit_troll = {'AL': '4/2/2014',
              'AZ': '3/24/2016',
              'CO': '6/5/2015',
              'FL': '6/2/2015',
              'GA': '4/15/2014',
              'ID': '3/26/2014',
              'IL': '8/26/2014',
              'IN': '5/5/2015',
              'KS': '5/20/2015',
              'LA': '5/28/2014',
              'ME': '4/14/2014',
              'MD': '5/5/2014',
              'MN': '4/29/2016',
              'MS': '3/28/2015',
              'MO': '7/8/2014',
              'MT': '4/2/2015',
              'NH': '7/11/2014',
              'NC': '8/6/2014',
              'ND': '3/26/2015',
              'OK': '5/16/2014',
              'OR': '3/3/2014',
              'RI': '6/4/2016',
              'SC': '6/9/2016',
              'SD': '3/26/2014',
              'TN': '5/1/2014',
              'TX': '6/17/2015',
              'UT': '4/1/2014',
              'VT': '5/22/2013',
              'VA': '5/23/2014',
              'WA': '4/25/2015',
              'WI': '4/24/2014',
              'WY': '3/11/2016'}

anti_troll = pd.DataFrame(anit_troll.items(), columns=['State', 'Signing_date'])
anti_troll['signing_dt'] = pd.to_datetime(anti_troll.Signing_date) 
anti_troll['signing_year'] = anti_troll['signing_dt'].dt.year

#location = pd.read_csv(r"C:\Users\domin\Downloads\location.tsv (2)\location.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
# Load dataframe with assignee IDs:
assingees_with_locations = pd.read_csv(r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Census Data Application\Data Upload Kiteworks\Upload 3_10_2022\Data\PatentsView_patent_assignee_with_org_and_raw_location.csv")    

state_list = list(assingees_with_locations.state.unique())
len([x for x in anti_troll.State.tolist() if not(x in state_list)]) 
# -> all in list

anti_troll_assignee = assingees_with_locations[['assignee_id', 'state']].merge(
    anti_troll, left_on='state', right_on='State', how='inner')

anti_troll_assignee.to_csv(r'G:\My Drive\Preliminary Research\Alice and Innovation Project\Alice_working_directory\anti_troll_assignee.csv',
                           index=False)
r'''