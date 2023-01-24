# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 11/20/2020
METHOD: Adapt Patent Portfolio Construction (version 6.5) to only match using
        KPSS data. The reason is that my own dictionary based matching process
        turns out to drop almost 30% of all patents that KPSS matched, and
        Noah Stoffman has an updated matching up to 2019.
        See: https://github.com/KPSS2017/Technological-Innovation-Resource-Allocation-and-Growth-Extended-Data
    VERSION 2: Include Innovative Search with uspc classes
    VERSION 3: Quarterly patent fillings
        Subversion 3.1: Include patent scope measures from Kuhn & Thompson (2019);
                        source from PatentsView_abstract_claim_extractions_2.py,
                        as well as standard deviations and means for variables, except time variables
    VERSION 4: Remove Crunchbase data &
                Change submission method for Google Cloud
        Subversion 4.1: Include additionally definition of treated patents as those where first claim is invalid
                        (used also by Galasso and Schankerman, 2015)
    VERSION 5: Aggregation method without weighting but direct citations, remove quarterly aggregation,
                execution on hpc cluster, remove count tables (is part of patent portfolio measure of, e.g., Blocking_patent_prediction_construction_v1.2.py)
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
/apps/anaconda3/bin/python KPSS_direct_Patent_Portfolio_Structuring_PatentsViewControls_5.py

#----------------------------
bsub <KPSS_direct_Patent_Portfolio_Structuring_PatentsViewControls_5.sh
r'''


# %%
#################################################################
# Package Load
#################################################################

import pandas as pd
import numpy as np
import re
import os


import requests
from io import BytesIO
import zipfile
import csv

#import multiprocessing as mp
#from scipy.stats.mstats import winsorize

#=============================================
# Current Build
VERSION = 5
# !!!! Also change model specification below !!!!!!!

# !!! Iteration of Classification Version
CLASSIFICATION_ITERATION = 9.2

#============================================
RANDOM_SEED = 42

# Define Home directory
home_directory = os.getcwd()

# Define source directory for additional data to be loaded
source_directory = r'Patent_portfolio_structuring_source_directory'
kpss_source_directory = source_directory + '//KPSS 2020 data'
PatentsView_directory = 'PatentsView_raw_data'


# Path to classification output complemented by specific class of the control groups
classification_directory = 'Alice_patent_classification_vPatentsViewControls_v'+str(CLASSIFICATION_ITERATION)

#-------------------------------------------
# Create putput path
output_directory = 'Patent_Portfolio_based_on_KPSS_data_'+str(VERSION)
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
    if not('kpss_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv' in\
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

        #-----------------------------------------------
        # Rename classification
        patent_class = patent_class.rename(columns={'patent_id':'grant_doc_num'})
        
        #####################################################################
        # Section 2: Assign predictions to KPSS data                        #
        #####################################################################

        #================================================
        # Value matching
        #-----------------------------------------------
        print('Merge with KPSS value data', flush=True)
        # Source: https://github.com/KPSS2017/Technological-Innovation-Resource-Allocation-and-Growth-Extended-Data
        # Documentation at: https://mitsloan.mit.edu/shared/ods/documents/?PublicationDocumentID=5894

        KPSS_public = pd.read_csv(kpss_source_directory + '//KPSS_2020_public.csv', low_memory=False)
        KPSS_public['issue_date_dt'] = pd.to_datetime(KPSS_public['issue_date'], format='%m/%d/%Y')
        KPSS_public['issue_year'] = KPSS_public.issue_date_dt.dt.year
        KPSS_public['issue_quarter'] = KPSS_public.issue_date_dt.dt.quarter
        KPSS_public['filing_date_dt'] = pd.to_datetime(KPSS_public['filing_date'], format='%m/%d/%Y')
        KPSS_public['filing_year'] = KPSS_public.filing_date_dt.dt.year
        KPSS_public['filing_quarter'] = KPSS_public.filing_date_dt.dt.quarter
        KPSS_public['grant_doc_num'] = pd.to_numeric(KPSS_public.patent_num,
                                                     downcast = 'integer', errors = 'coerce')

        
        #KPSS_public['in_uspc'] = KPSS_public.apply(lambda x: bool(x.grant_doc_num in (list(set(uspc_current.patent_id.to_list())))), axis=1)
        kpss_merge = KPSS_public[
            ['grant_doc_num', 'xi_real',
             'xi_nominal', 'cites',
             'filing_date_dt', 'issue_date_dt',
             'filing_year', 'issue_year']
            ].drop_duplicates()

        # !!!! Need here a right merge to preserve all the other variables in KPSS merge
        patent_alice_assignments = pd.merge(patent_class,
                                            kpss_merge,
                                            on='grant_doc_num',
                                            how='right')

        #-----------------------------------------------
        # Assignment data
        #-----------------------------------------------
        print('Merge with KPSS assignment data', flush=True)
        patent_permco_permno_match_public = pd.read_csv(kpss_source_directory + '//patent_permco_permno_match_public_2020.csv', low_memory=False)
        #patent_permco_permno_match_public.patent_num.value_counts().value_counts()
        # => unique

        # Coerce data types
        patent_permco_permno_match_public['grant_doc_num'] = pd.to_numeric(
            patent_permco_permno_match_public.patent_num,
            downcast = 'integer', errors = 'coerce')
        patent_permco_permno_match_public['permco'] = pd.to_numeric(
            patent_permco_permno_match_public.permco,
            downcast = 'integer', errors = 'coerce')
        patent_permco_permno_match_public['permno'] = pd.to_numeric(
            patent_permco_permno_match_public.permno,
            downcast = 'integer', errors = 'coerce')


        # Merge with Alice assignment data => inner merge since no assignments outside of KPSS
        patent_alice_assignments = pd.merge(patent_alice_assignments,
                                            patent_permco_permno_match_public.\
                                                drop(['patent_num'], axis=1).drop_duplicates(),
                                            on='grant_doc_num',
                                            how='inner')

        #---------------------------------------------
        print('Checkpoint 1', flush=True)
        #---------------------------------------------
        # Intermediate Save: Checkpoint 1
        patent_alice_assignments.to_csv(
            output_directory+'//kpss_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv',
            index=False, encoding='utf-8')
    else:
        print('Checkpoint 1 found in home directory, load', flush=True)
        #============================================
        patent_alice_assignments = pd.read_csv(
            output_directory+'//kpss_direct_patent_alice_assignments_cp_1_' + str(output_version) + '.csv',
            encoding='utf-8', dtype={'grant_doc_num':int})
    #---------------------------------------------
    #---------------------------------------------
    # Testing purpose: patent_alice_assignments = pd.read_csv('patent_alice_assignments_cp_1.csv', encoding='utf-8')
    # patent_assignments = pd.read_csv('patent_assignment_data_1_2000.csv')

    # %%
    ################################################################
    #   Section 2: Patent Portfolio Aggregation                    #
    ################################################################
    # => Section 2 in the original process is about sting matching to assignments
    
    r'''
    #========================================
    # Innovative search vector space construction
    #========================================
    # -> not executed since already part of other innovation strategy measure construction
    
    print('\t Load for class count cpc current', flush=True)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #!!!! Most patents are now classified via CPC, as in Dugan (2018)
    # Translate affected patents into CPC classes
    # See: https://www.uspto.gov/patents-application-process/patent-search/classification-standards-and-development
    #-------------------------------
    # cpc classifications
    #-------------------------------
    if ('cpc_current.tsv' in os.listdir(PatentsView_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        print('\t\t Load from directory', flush=True)
        cpc_current = pd.read_csv(PatentsView_directory + '/cpc_current.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load from Patent View

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/cpc_current.tsv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break
        z = zipfile.ZipFile(BytesIO(r.content))
        z.extractall(PatentsView_directory)

        cpc_current = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)


    #-------------------------------------
    # Focus on primary categories
    cpc_current = cpc_current[cpc_current.category=='inventional']

    # Drop unneeded columns and make cpc groups unique
    cpc_current = cpc_current.drop(['uuid', 'section_id',
                                    'category', 'subgroup_id',
                                    'sequence', 'subsection_id'], axis=1).drop_duplicates()

    # Cast id to int
    cpc_current['patent_id'] = pd.to_numeric(cpc_current.patent_id,
                                             downcast='integer', errors='coerce')
    # Rename
    cpc_current = cpc_current.rename(columns={'patent_id':'grant_doc_num',
                                              'group_id':'patent_class'})

    # list of all available cpc classes
    cpc_groups = [str(s) for s in cpc_current.patent_class.unique()]

    #---------------------------------------------------
    print('\t Load for class count uspc current', flush=True)
    #-------------------------------
    # uspc_current classifications
    #-------------------------------
    # Use current uspc classification to be more in aligne with cpc classification, AND
    # there seems to be an issue with classifications only reaching until 2013 assignments
    if ('uspc_current.tsv' in os.listdir(PatentsView_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        print('\t\t Load from directory', flush=True)
        uspc_current = pd.read_csv('uspc_current.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load from Patent View

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/uspc_current.tsv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break
        z = zipfile.ZipFile(BytesIO(r.content))
        z.extractall(PatentsView_directory)

        uspc_current = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    
    uspc_current['mainclass_id'] = uspc_current['mainclass_id'].astype(str).\
            apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    # Type casting of id
    uspc_current['patent_id'] = pd.to_numeric(uspc_current.patent_id,
                                              downcast='integer', errors='coerce')

    # Focus main classes
    uspc_current = uspc_current[['patent_id', 'mainclass_id']].drop_duplicates()

    # Rename
    uspc_current = uspc_current.rename(columns={'patent_id':'grant_doc_num',
                                                'mainclass_id':'patent_class'})

    # list of all available cpc classes
    uspc_groups = [str(s) for s in uspc_current.patent_class.unique()]

    #key_variable='permco'
    #patent_state_assignments = patent_alice_assignments.loc[(patent_alice_assignments.exec_year == 2014)]

    def _innovative_search_vector_space_construction(patent_state_assignments,
                                                     key_variable,
                                                     patent_classes=cpc_current,
                                                     class_list=cpc_groups):
        
        #METHOD: Implement vector space construction for patent classes as from Manso, Balsmeier, Fleming (2019)
        #INPUT: - patent_state_assignments: df from _patentportfolio_state_construction
        #       - key_variabe: str with firm identifier to aggregation
        #       - patent_classes: df with patent classes, consisting of columns 'grant_doc_num' and 'patent_class' only
        #       - class_list: list of classes available
        #RETURN: pivoted_count: df with first column being the key variable and the columns are the count of
        #                        assigned patents per patent class
        

        # Select assignments and patent numbers
        patent_key_assignments = patent_state_assignments[[key_variable, 'grant_doc_num']].drop_duplicates()

        #------------------------------------
        # Merge with patent classes, ensuring type consistency
        patent_key_assignments['grant_doc_num'] = pd.to_numeric(patent_key_assignments.grant_doc_num,
                                                                downcast='integer', errors='coerce')
        patent_classes['grant_doc_num'] = pd.to_numeric(patent_classes.grant_doc_num,
                                                        downcast='integer', errors='coerce')

        patent_key_classe_assignments = pd.merge(patent_key_assignments,
                                                 patent_classes,
                                                 how='inner',
                                                 on='grant_doc_num')
        # By now, the data frame should consist of three columns: key, grant_doc_num, patent_class
        # => group based on key and patent_class
        group_count = patent_key_classe_assignments.groupby([key_variable, 'patent_class']).count().\
            reset_index().rename(columns={'grant_doc_num':'count'})

        #-------------------------------------
        # Reshape the group count
        pivoted_count = group_count.pivot(index=key_variable, columns='patent_class', values='count').fillna(0).reset_index()

        #-----------------------------------
        # fill not found columns with zeros
        not_found_classes = set(class_list).difference(set(pivoted_count.columns))
        for empty_col in list(not_found_classes):
            pivoted_count[empty_col] = 0.0

        return(pivoted_count)
    r'''

    #*********************************************
    # Rolling Patent Assignment
    #*********************************************
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
        patent_state_assignments['cites_zero'] = patent_state_assignments.cites.fillna(0)
        
        # Depreciate forward citations
        patent_state_assignments['depreciated_cites'] = \
            patent_state_assignments['cites_zero'] * (1-dep_rate)**patent_state_assignments['patent_age_years']
        
        patent_state_assignments['depreciated_xi_real'] = \
            patent_state_assignments['xi_real'] * (1-dep_rate)**patent_state_assignments['patent_age_years']
        

        #**********************************************
        # Define additional variables
        patent_state_assignments['Alice_affected'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), 1, 0)

        patent_state_assignments['Alice_affected_patent_age'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_age, np.nan)
        patent_state_assignments['Alice_affected_patent_age_application'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_age_application, np.nan)
        patent_state_assignments['Alice_affected_patent_time_to_grant'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.patent_time_to_grant, np.nan)

        patent_state_assignments['Alice_affected_cites'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.cites_zero, np.nan)
        patent_state_assignments['Alice_affected_xi_real'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.xi_real, np.nan)            
        
        patent_state_assignments['Alice_affected_depreciated_patent_count'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_patent_count, np.nan)
        patent_state_assignments['Alice_affected_depreciated_cites'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_cites, np.nan)
        patent_state_assignments['Alice_affected_depreciated_xi_real'] = np.where(~np.isnan(patent_state_assignments[Alice_prediction_indicator]), patent_state_assignments.depreciated_xi_real, np.nan)
        
        #--------------------------------------------
        # Additional labels for affected predicted patents
        patent_state_assignments['Alice_predicted_affected_patent_age'] = patent_state_assignments['Alice_affected_patent_age'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_patent_age_application'] = patent_state_assignments['Alice_affected_patent_age_application'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_patent_time_to_grant'] = patent_state_assignments['Alice_affected_patent_time_to_grant'] * patent_state_assignments[Alice_prediction_indicator]

        patent_state_assignments['Alice_predicted_affected_cites'] = patent_state_assignments['cites_zero'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_xi_real'] = patent_state_assignments['xi_real'] * patent_state_assignments[Alice_prediction_indicator]
        
        patent_state_assignments['Alice_predicted_affected_depreciated_patent_count'] = patent_state_assignments['depreciated_patent_count'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_depreciated_cites'] = patent_state_assignments['depreciated_cites'] * patent_state_assignments[Alice_prediction_indicator]
        patent_state_assignments['Alice_predicted_affected_depreciated_xi_real'] = patent_state_assignments['depreciated_xi_real'] * patent_state_assignments[Alice_prediction_indicator]
        
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

            Alice_affected_cites=('Alice_affected_cites', 'sum'),
            Alice_affected_xi_real=('Alice_affected_xi_real', 'sum'),
            
            Alice_affected_depreciated_patent_count=('Alice_affected_depreciated_patent_count', 'sum'),
            Alice_affected_depreciated_cites=('Alice_affected_depreciated_cites', 'sum'),
            Alice_affected_depreciated_xi_real=('Alice_affected_depreciated_xi_real', 'sum'),
            
            #*****************************************************************
            Alice_predicted_affected_patent_age=('Alice_predicted_affected_patent_age', 'mean'),
            Alice_predicted_affected_patent_age_application=('Alice_predicted_affected_patent_age_application', 'mean'),
            Alice_predicted_affected_patent_time_to_grant=('Alice_predicted_affected_patent_time_to_grant', 'mean'),

            Alice_predicted_affected_cites=('Alice_predicted_affected_cites', 'sum'),
            Alice_predicted_affected_xi_real=('Alice_predicted_affected_xi_real', 'sum'),
            
            Alice_predicted_affected_depreciated_patent_count=('Alice_predicted_affected_depreciated_patent_count', 'sum'),
            Alice_predicted_affected_depreciated_cites=('Alice_predicted_affected_depreciated_cites', 'sum'),
            Alice_predicted_affected_depreciated_xi_real=('Alice_predicted_affected_depreciated_xi_real', 'sum'),
            
            #*****************************************************************
            # Portfolio varables
            total_assignments=("grant_doc_num", 'count'),
            total_cites=("cites_zero", 'sum'),
            total_xi_real=("xi_real", 'sum'),
            
            total_patent_age=('patent_age', 'mean'),
            total_patent_age_application=('patent_age_application', 'mean'),
            total_patent_time_to_grant=('patent_time_to_grant', 'mean'),

            total_depreciated_patent_count=('depreciated_patent_count', 'sum'),
            total_depreciated_cites=('depreciated_cites', 'sum'),
            total_depreciated_xi_real=('depreciated_xi_real', 'sum')

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

        patent_portfolio['relative_Alice_affected_cites'] = patent_portfolio['Alice_affected_cites'] / patent_portfolio['total_cites']
        patent_portfolio['relative_Alice_predicted_affected_cites'] = patent_portfolio['Alice_predicted_affected_cites'] / patent_portfolio['total_cites']
        
        patent_portfolio['relative_Alice_affected_xi_real'] = patent_portfolio['Alice_affected_xi_real'] / patent_portfolio['total_xi_real']
        patent_portfolio['relative_Alice_predicted_affected_xi_real'] = patent_portfolio['Alice_predicted_affected_xi_real'] / patent_portfolio['total_xi_real']
        
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
                                    '//KPSS_direct_annual_patent_portfolio_' + str(key_variable) +
                                    '_' + str(output_version) +
                                    '_' + str(year_count) +
                                    '_' + str(exec_identifier) +
                                    '_dep_rate_' + str(dep_rate) +
                                    '_' + str(execution_limit) +
                                    '_' + str(Alice_prediction_indicator) + '.csv',
                                    encoding='utf-8')
        else:
            patent_portfolio.to_csv(portfolio_output_directory +
                                     '//KPSS_direct_within_annual_patent_assignment_' + str(key_variable) +
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
        last_year = 2021

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
    
        # =============================================================================
        #  Collect Results and Save output
        # =============================================================================

        #=============================================
        patent_portfolio.to_csv(portfolio_output_directory +
                                 '//KPSS_direct_annual_patent_portfolio_' + str(id_variable) +
                                 '_' + str(output_version) + '.csv',
                                 encoding='utf-8')
        patent_assignments.to_csv(portfolio_output_directory +
                                 '//KPSS_direct_within_annual_patent_assignment_' + str(id_variable) +
                                 '_' + str(output_version) + '.csv',
                                 encoding='utf-8')

        return(patent_portfolio, patent_assignments)


    
    #===============================================
    # permco Aggregating
    #===============================================
    # Define key variables
    patent_portfolio, patent_assignments = _rolling_portfolio_construction_wrapper('permco')

    #-------------------------------------------
    # Output
    #---------------------------------------------
    print('Checkpoint 3, for permco clustering for annual data', flush=True)
    #---------------------------------------------
    # Intermediate Save: Checkpoint 3
    patent_portfolio.to_csv(output_directory+'//KPSS_direct_patent_portfolio_permco_' + \
                            str(output_version) + '.csv',
                            index=False, encoding='utf-8')
    patent_assignments.to_csv(output_directory+'//KPSS_direct_annual_patent_assignment_permco_' + \
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

