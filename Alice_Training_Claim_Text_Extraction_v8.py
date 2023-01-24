# -*- coding: utf-8 -*-
"""
    DATE: 9/16/2020
    AUTHOR: Dominik J
    METHOD: Classification of Alice|Bilski|Mayo|Myriad Affected Claims
            Parallel Execution
        VERSION 6: Integer based identifiers and pg-pub extraction
            Subversion 6.1 with additional testing
            Subversion 6.2 include PatentsView Claim extraction
        VERSION 7: Iterate through several occurances of the found application_ids
                    per publication xml file
            Subversion 7.1: Add additional output strings &
                            improved request approach to check for content length and no streaming
                            & Correct for vintage of application data used
            Subsubversion 7.1.1: Update url & dataset names and submission routine for Google Cloud
                                !!! Rename to 7_1_1.py to allow for import of function in classification file
        VERISON 8 (DATE 3/11/2022): Use PatentsView Pre-grant application data 
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
/apps/anaconda3/bin/python Alice_Training_Claim_Text_Extraction_v8.py

#---------------------------------------
bsub < Alice_Training_Claim_Text_Extraction_v8.sh
r'''

#################################################################
# Load Packages
#################################################################

import pandas as pd
import numpy as np
import re
import os
import shutil

import requests
from io import BytesIO
from lxml import html

import zipfile
import csv

import multiprocessing as mp

#directory_path = 'C:\\Users\\domin\\Desktop'
# os.chdir('C:\\Users\\domin\\Desktop')
# For old server
# os.chdir('/bulk/phd/dominik_jurek')

#----------------------------------------
# Expand field limit to iterate through all claims
import ctypes
csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))
csv.field_size_limit()

#----------------------------------------
# Current Build
VERSION = 8

# home directory
home_directory = os.getcwd()

# Define PatentsView directory
PatentsView_directory = 'PatentsView_raw_data'

r'''
pd.set_option('display.max_rows', 400)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 100)
r'''

import psutil
print('\t\t CPUs: {0:.0f};\n \
      \t\t Memory usage: total {1:.2f} GB; available {2:.2f} GB;\n \
      \t\t free percent {3:2.1f}%; used {4:.2f} GB; free {5:.2f} GB'.format(
    psutil.cpu_count(),
    psutil.virtual_memory()[0]/1024**3,
    psutil.virtual_memory()[1]/1024**3,
    psutil.virtual_memory()[2],
    psutil.virtual_memory()[3]/1024**3,
    psutil.virtual_memory()[4]/1024**3
    ), flush=True)

#################################################################
# PatentsView Pre-grant Application Claim Collection
#################################################################
    
#============================================
#  Executable link extraction
#============================================
def _url_claim_PatentView_PreGrant():
    '''Helper function to extract list of (url, year) for application claim full text'''
    #===============================================
    # Download claims for granted patents
    patent_claim_master_url = r'https://patentsview.org/download/pg_claims'

    # Wrap around limited amount of retrys
    for request_attempt in range(5):
        request = requests.get(patent_claim_master_url)
        if (request.ok == True):
            break

    tree = html.fromstring(request.content)

    # Find URLs to years
    links = tree.xpath("//a[contains(@href, '.zip')]")
    # Get links for year in respective range
    url_link_list = [(l.get('href'), int(re.findall(r'\d{4,4}', l.get('href'))[0])) for l in links]
    return(url_link_list)
    

#=========================================================================
# Yearly pre-grant application claim extraction
#=========================================================================
def application_claim_PatentView(yearly_link, year, app_df, output_path, output_name = 'v8'):
    '''
    METHOD: Extracts application claim text from PatentsView pre-grant application data
            for given list of application ids from xml publications
    INPUT:  yearly_link: url to PatentView Pre-grant application claim text
            year: publication year for claim text from URL
            app_df: df from application_regrant_publication with searched document and application_id
            output_path: Path to output directory
            year: publication year of application to be extracted
            output_name: string of added to the end of the outpuf file name
    OUTPUT: PatentsView_PregrantApp_claim_extraction: DF with extracted claims for publication year
                keys should be the appl_id and document_number
    RETURN: NONE
    '''
    
    #------------------------------
    print('\t Search treated application claims for year ' + str(year), flush=True)
    try:
        # Load the fulltext from the patent claism

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(yearly_link)
            # Check if no error and length is correct
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        #z = zipfile.ZipFile(r"C:\Users\domin\Downloads\claims_2016.tsv.zip")

        app_claims = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #------------------------------------------
        # Limit observations to independent claims that are in the app DF (wihtout dependency)
        indep = (app_claims.dependent.isnull())
        indep_app_claims = app_claims[indep]

        #------------------------------------------
        # Cleaning the entries and remove digits from the beginning
        indep_app_claims.loc[:, 'claim_text'] = indep_app_claims.text.astype(str).apply(lambda x: \
                                                                       re.sub(r'^\d{1,3}\s{0,}\.{0,1}\s', '', \
                                                                              x).strip())

        #------------------------------------------
        # Further control for independent claims following https://www.uspto.gov/sites/default/files/documents/patent_claims_methodology.pdf
        # And check via reg expression if there is a reference to a different claim
        indep_app_claims.loc[:, 'dep_reference'] = indep_app_claims.claim_text.apply(lambda x: bool(re.search(r'\bclaim\s+\d+\b|\bclaims\s+\d+\b', str(x))))
        indep_app_claims = indep_app_claims[~indep_app_claims.dep_reference]

        #------------------------------------------
        # Select applications which are in the search application dataframe
        #indep_patent_claims['patent_id'] = indep_patent_claims.patent_id.astype(str).\
        #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
        indep_app_claims = indep_app_claims[~indep_app_claims.document_number.isnull()]

        searched_indep_app_claims = indep_app_claims.merge(
            app_df, on='document_number', how='inner')
        searched_indep_app_claims.reset_index(inplace=True, drop=True)

        #--------------------------------------------------
        # Rename and typcasting        
        searched_indep_app_claims = searched_indep_app_claims.rename(
            columns={'num':'claim_num',
                     'document_number':'pgpub_number',
                     'filing_date_dt':'filing_date_PregrantApp_dt', 
                     'filing_year':'filing_year_PregrantApp'})
        
        searched_indep_app_claims.loc[:, 'claim_int'] = pd.to_numeric(
            searched_indep_app_claims.claim_num, errors='coerce')
        
        #----------------------------------------
        # Output Result
        searched_indep_app_claims.to_csv(
            path_or_buf = output_path + '/PatentsView_PregrantApp_claim_extraction_' + str(year) + '_' + output_name + '.csv',
            index=False, encoding = 'utf-8')
        print('\t Lenght of output DF of independent application claims for type ' + str(output_name) +
              ', year '+ str(year) + ': ' + str(len(searched_indep_app_claims)), flush=True)

    except Exception as exc:
        print('\t Error in claim search for year: ' + str(year) + ' => ' + str(exc))

    return

#################################################################
# PatentsView Claim Extraction of Full Text Claims
#################################################################
#============================================
def _url_claim_PatentView(min_year=1990):
    '''Helper function to extract list of (url, year) for patent claim full text'''
    #===============================================
    # Download claims for granted patents
    patent_claim_master_url = r'https://patentsview.org/download/claims'


    # Wrap around limited amount of retrys
    for request_attempt in range(5):
        request = requests.get(patent_claim_master_url)
        if (request.ok == True):
            break

    tree = html.fromstring(request.content)

    # Find URLs to years
    links = tree.xpath("//a[contains(@href, '.zip')]")
    # Get links for year in respective range
    url_link_list = [(l.get('href'), int(re.findall(r'\d{4,4}', l.get('href'))[0])) for l in links if int(re.findall(r'\d{4,4}', l.get('href'))[0]) >= min_year]
    return(url_link_list)

#============================================
def patent_claim_PatentView(yearly_link, year,
                            patent_list,
                            output_path, output_name):
    '''
    METHOD: Extracts from USPTO PatentsView claim text
    INPUT:  yearly_link: url to PatentView claim text
            year: publication year for claim text from URL
            patent_list: List with 'patent_id' as int
            output_path: Path to output directory
            min_year: first year of patent publications to be extracted
            output_name: string of added to the end of the outpuf file name for classificaiton type
    OUTPUT: PatentsView_claim_extraction: DF with extracted independent claims text
                                            for patent_list -> saved in output_path

    '''

    #------------------------------
    # Turn patent id list into in
    patent_list = [int(i) for i in patent_list if not(np.isnan(i))]

    #------------------------------
    print('\t Search treated patent claims for type ' + str(output_name) + ', year ' + str(year), flush=True)
    try:
        # Load the fulltext from the patent claism

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(yearly_link)
            # Check if no error and length is correct
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        #z = zipfile.ZipFile(r"C:\Users\domin\Downloads\claims_2016.tsv.zip")

        patent_claims = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #------------------------------------------
        # Limit observations to independent claims that are in the patent DF
        indep = (patent_claims.dependent.isnull())|(patent_claims.dependent==-1)|(patent_claims.dependent=='-1')
        indep_patent_claims = patent_claims[indep]

        #------------------------------------------
        # Cleaning the entries and remove digits from the beginning
        indep_patent_claims['text'] = indep_patent_claims.text.astype(str).apply(lambda x: \
                                                                                 re.sub(r'^\d{1,3}\.{0,1}\s', '', \
                                                                                        x).strip())

        #------------------------------------------
        # Further control for independent claims following https://www.uspto.gov/sites/default/files/documents/patent_claims_methodology.pdf
        # And check via reg expression if there is a reference to a different claim
        indep_patent_claims.loc[:, 'dep_reference'] = indep_patent_claims.text.apply(lambda x: bool(re.search(r'\bclaim\s+\d+\b|\bclaims\s+\d+\b', str(x))))
        indep_patent_claims = indep_patent_claims[~indep_patent_claims.dep_reference]

        #------------------------------------------
        # Select patents which are in the searched classes
        # !!! Note that I focus on utility patents, which have as identifier an integer
        # See: https://www.uspto.gov/patents-application-process/applying-online/patent-number#:~:text=A%20Patent%20Number%20is%20assigned,six%2C%20seven%20or%20eight%20digits.
        #indep_patent_claims['patent_id'] = indep_patent_claims.patent_id.astype(str).\
        #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
        indep_patent_claims['patent_id'] = pd.to_numeric(indep_patent_claims.patent_id,
                                                         downcast = 'integer', errors = 'coerce')
        indep_patent_claims = indep_patent_claims[~indep_patent_claims.patent_id.isnull()]

        searched_indep_patents = indep_patent_claims[indep_patent_claims.patent_id.isin(patent_list)]
        searched_indep_patents.reset_index(inplace=True, drop=True)
        #searched_indep_patents = indep_patent_claims.sample(n=1000, random_state=RANDOM_SEED)

        #----------------------------------------
        # Output Result
        searched_indep_patents.to_csv(path_or_buf = output_path + '/PatentsView_claim_extraction_' + str(year) + '_' + output_name + '.csv',
                                      index=False, encoding = 'utf-8')
        print('\t Lenght of output DF of independent claims for type ' + str(output_name) +
              ', year '+ str(year) + ': ' + str(len(searched_indep_patents)), flush=True)

    except Exception as exc:
        print('\t Error in claim search for year: ' + str(year) + ' => ' + str(exc))

    return


########################################################################
# Extraction of control claims that are patented
########################################################################

def control_patent_claim_fulltext_extraction(rejections_data, application_df, nclasses, output_path, min_year = 2010, max_year = 2010, output_name = 'v3'):
    '''
    METHOD: Extracts from USPTO patent view claim text from applications in same cohort
            as rejection data, thus identifying eligble claims in same USPC group
            and without office actions (internally parallel)
    INPUT:  rejections_data: DF with identified rejections from Office Action Research Dataset for Patents
            application_df: DF from PatentsView Pre-grant Applications
            nclasses: Number of USPC Classes to be considered from most frequent downward
            output_path: Path to output directory
            min_year: first publication year of patent application to be extracted
            max_year: last publication year of patent application to be extracted
            output_name: string of added to the end of the outpuf file name
    OUTPUT: Control_Patent_claim_extraction: DF with extracted claims for filing / publication year
    RETURN: NONE
    '''
    #================================================
    # Step 1: Gather data on patent that can serve as controls
    print('\t Load relevant data', flush=True)
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


    '''
    Get application data for code for patents
    r = requests.get(r"http://data.patentsview.org/20200331/download/application.tsv.zip" , stream=True)
    z = zipfile.ZipFile(BytesIO(r.content))
    z.extractall()

    patents_application_data = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting = csv.QUOTE_NONNUMERIC)
    '''
    #==================================================
    # Step 2: Get office actions to restrict to non-affected patents
    '''
    r = requests.get(r"https://bulkdata.uspto.gov/data/patent/office/actions/bigdata/2017/rejections.csv.zip" , stream=True)
    z = zipfile.ZipFile(BytesIO(r.content))

    rejections = pd.read_csv(z.open(z.infolist()[0].filename))
    '''

    # Office actions to exclude from control set

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

    
    #==============================================================
    # Step 3: Merge and find main USPC classes for the respective years and non-affected applications

    # rejections.app_id.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True    10133179 => coerce to integers without loss
    # office_actions.app_id.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True    4384532
    # application_data.application_number.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True     10170943
    # False      954812
    #application_data_nonumeric = application_data[~application_data.application_number.astype(str).apply(lambda x: x.isdigit())]
    #application_data_nonumeric.earliest_pgpub_date.isnull().value_counts()
    #True    954812
    #Name: earliest_pgpub_date, dtype: int64
    # => All applications which have non-numeric application number are not published!
    #application_data_nonumeric.application_number.apply(lambda x: x.split(r'/')[0])
    # PCT    954812 => international application, source: https://www.uspto.gov/ebc/portal/infopctnum.htm#:~:text=PCT%20or%20International%20Application%20Numbers,PCT%2FUS1999%2F123456'.
    # => all relevant app_ids are integer, those application_data id that are not integer are international
    # applications without publication in the US.
    # => It makes sense for performance improvements to convert to integer

    rejections_data['app_id'] = pd.to_numeric(rejections_data.app_id, downcast = 'integer', errors = 'coerce')
    office_actions['app_id'] = pd.to_numeric(office_actions.app_id, downcast = 'integer', errors = 'coerce')
    application_data['app_id'] = pd.to_numeric(application_data.application_number, downcast = 'integer', errors = 'coerce')

    #rejections_data['app_id'] = rejections_data.app_id.astype(str)
    #office_actions['app_id'] = office_actions.app_id.astype(str)
    #application_data['app_id'] = application_data.application_number.astype(str)

    rejections_application_date = pd.merge(application_data,
                                            rejections_data,
                                            how = 'inner',
                                            on = ['app_id'])

    # Convert date to dateobjects
    rejections_application_date.filing_date = pd.to_datetime(rejections_application_date.filing_date, errors = 'coerce')

    # NOTE:
    # rejections_application_date.filing_date.dt.year.min() => 2007
    # rejections_application_date.filing_date.dt.year.max() => 2017

    application_data.filing_date = pd.to_datetime(application_data.filing_date, errors = 'coerce')

    #=================================================================
    # Step 4: Create control data which have no recorded office action and are within the same cohorts
    print('\t Control patent contruction', flush=True)
    application_control_data = application_data[~application_data.app_id.isin(list(office_actions.app_id))\
                                                & (application_data.filing_date.dt.year.isin(list(rejections_application_date.filing_date.dt.year)))].copy()


    #len(application_data[(application_data.filing_date.dt.year.isin(list(rejections_application_date.filing_date.dt.year))) &
    #                 (application_data.uspc_class == 705)])
    # 71090
    #len(application_data[~application_data.app_id.isin(list(office_actions.app_id)) & \
    #                 (application_data.filing_date.dt.year.isin(list(rejections_application_date.filing_date.dt.year))) & \
    #                 (application_data.uspc_class == 705)])
    # 29035
    # Not so much differeny

    # Find the categories most exposed for alice cases

    # rejections_application_date.uspc_class.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True     10129947
    # False        3193
    # => not all uspc classes are int, use string
    #rejections_application_date['uspc_class_int'] = pd.to_numeric(rejections_application_date.uspc_class, downcast = 'integer', errors = 'coerce')
    #uspc_main_category = list(set(rejections_application_date['uspc_class_int'].value_counts().nlargest(nclasses).reset_index()['index']))

    #------------------------------------------
    # Define main categories
    rejections_application_date['uspc_class_str'] = rejections_application_date.uspc_class.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    print('USPC main classes:')
    print(rejections_application_date['uspc_class_str'].value_counts(ascending=False).nlargest(nclasses))

    uspc_main_category = list(set(rejections_application_date['uspc_class_str'].value_counts(ascending=False). \
                                  nlargest(nclasses).reset_index()['index']))

    #------------------------------------------
    # rejections_application_date.earliest_pgpub_number.isnull().value_counts(normalize=True)
    # False    0.971729
    # True     0.028271
    # => Less than 3% of all observations don't have pregrant publication number. This is more unique
    # than the application number which can be referenced in other patents

    # application_data.earliest_pgpub_number.astype(str).apply(lambda x: len(x)).value_counts()
    #3     5795970
    #15    5329678
    #9         107
    #application_data.application_number.astype(str).apply(lambda x: len(x)).value_counts()
    #8     10072856
    #14      954812
    #7        98087
    # => publication and application number are uniquely different, application number could be
    # also in 'related patent documents', whiles publication number are more unique

    # Remove country code at beginning and Kind code at end,
    # see: https://www.uspto.gov/patents-application-process/checking-application-status/search-application
    #      https://www.uspto.gov/learning-and-resources/support-centers/electronic-business-center/kind-codes-included-uspto-patent
    #application_data['earliest_pgpub_number_cleaned'] = application_data.earliest_pgpub_number.astype(str).apply(lambda x: re.sub(r'^US', '', x)).apply(lambda x: re.sub(r'[a-zA-Z]{1,1}\d{0,1}$', '', x))
    #application_data.earliest_pgpub_number_cleaned.astype(str).apply(lambda x: len(x)).value_counts()
    #2     5795970
    #11    5329678
    #9         107
    # => still unique identification when going for publication reference

    # Filter control data to classes most affected
    #application_control_data['uspc_class_int'] = pd.to_numeric(application_control_data.uspc_class, downcast = 'integer', errors = 'coerce')
    #application_control_data = application_control_data[application_control_data.uspc_class_int.isin(uspc_main_category)]

    application_control_data['uspc_class_str'] = application_control_data.uspc_class.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    application_control_data = application_control_data[application_control_data.uspc_class_str.isin(uspc_main_category)]

    # Coerce patent names to string
    #application_control_data['patent_id'] = application_control_data.patent_number.astype(str).\
    #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))
    #application_data.patent_number.astype(str).apply(lambda x: x.isdigit()).value_counts()
    #True     5808103
    #False    5317652
    #Name: patent_number, dtype: int64

    # Restrict to patented cases
    # Appl_status_codes is integer, see https://www.uspto.gov/sites/default/files/documents/Appendix%20A.pdf
    application_control_data['appl_status_code'] = pd.to_numeric(application_control_data.appl_status_code,
                                                                 errors='coerce', downcast='integer')
    control_patents = application_control_data[application_control_data.appl_status_code == 150]
    # Filter patent information for data that are in the control group
    # control_patents = patents_application_data[patents_application_data.number.isin(list(application_control_data.app_id))]

    print('\t Number of extractable control applications from PatentsView Pre-grant applications: ' + str(len(control_patents)), flush=True)

    
    # Find document numbers from PatentsView Pre-grant application data
    application_with_doc_num = application[
        application.app_id.isin(control_patents.app_id)][
            ['app_id', 'document_number', 'filing_date_dt', 'filing_year']].drop_duplicates()
    #===============================================
    # Step 5: Download claims for granted control patents

    # Use the same method as the main claim extraction to get the control claims (note, above the app_id's are coerced to int)

    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    #-------------------------------------------------------
    # restrict scraping to minimum year with one year in control
    print('\t Collect url to application claim text', flush=True)
    url_link_list = _url_claim_PatentView_PreGrant()
    #-------------------------------------------------------

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start control claim extraction from PatentsView Pre-grant application for ' + str(output_name) +
              ' and year ' + str(year) + '\n', flush=True)
        pool.apply_async(
                        application_claim_PatentView,
                        args=(
                              yearly_link,
                              year,
                              application_with_doc_num,
                              output_path,
                              'PatentsView_PregrantApp_ControlPatents_' + output_name
                              )
                        )
    pool.close()
    pool.join()


    #====================================
    # Step 6: PatentsView Claims Extraction application with publication number and date after
    #           Alice and no 101 office action
    # Limit to control claim applications without 101 rejections Alice identification
    #====================================
    # Source: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3024621
    #         https://www.uspto.gov/sites/default/files/documents/Variable%20tables_v20171120.pdf

    # Application data preparations
    # Focusing on
    # !!! Note that I focus on utility patents, which have as identifier an integer
    # See: https://www.uspto.gov/patents-application-process/applying-online/patent-number#:~:text=A%20Patent%20Number%20is%20assigned,six%2C%20seven%20or%20eight%20digits.
    application_data['patent_num'] = pd.to_numeric(application_data.patent_number,
                                                   downcast = 'integer', errors = 'coerce')
    application_data['patent_issue_date_dt'] = pd.to_datetime(application_data.patent_issue_date, errors = 'coerce')

    application_data['uspc_class_str'] = application_data.uspc_class.astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    #----------------------------------------
    # Define conditions for patents
    # Restrict control patents to those granted after the Alice decision
    alice_decision_date = np.datetime64('2014-06-19')

    # Restriction to patents without 101 office actions
    alice_101_condition = (office_actions.rejection_101 == 1)
    office_actions_101_app_id_list = list(office_actions[alice_101_condition]['app_id'])

    # Find patents with:
    # - No 101 office action
    # - same filing cohort as rejected claims
    # - patent issue date after alice decision
    # - uspc classes in main classes
    application_patentView_control_data = application_data[~(application_data.app_id.isin(office_actions_101_app_id_list)) & \
                                                           (application_data.filing_date.dt.year.isin(list(rejections_application_date.filing_date.dt.year))) & \
                                                               (application_data.patent_issue_date_dt > alice_decision_date) & \
                                                                   (application_data.uspc_class_str.isin(uspc_main_category))
                                                                   ].copy()

    #---------------------------------------------------------
    # Restrict to patented cases with patent number
    application_patentView_control_data['appl_status_code'] = pd.to_numeric(application_patentView_control_data.appl_status_code,
                                                                            errors='coerce', downcast='integer')
    control_PatentsView_patents = application_patentView_control_data[application_patentView_control_data.appl_status_code == 150]
    # control_PatentsView_patents.patent_num.isnull().value_counts()
    control_PatentsView_patents = control_PatentsView_patents[~control_PatentsView_patents.patent_num.isnull()]

    print('\t Number of extractable control patent from PatentsView: ' + str(len(control_PatentsView_patents)), flush=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # PatentsView Extraction Routine
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    #-------------------------------------------------------
    # restrict scraping to minimum year with one year in control
    patentsView_first_year = min(control_PatentsView_patents.patent_issue_date_dt.dt.year) - 1
    print('\t Collect url to patent claim text, first year ' + str(patentsView_first_year), flush=True)
    url_link_list = _url_claim_PatentView(min_year=patentsView_first_year)
    #-------------------------------------------------------

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start control claim extraction from PatentsView for ' + str(output_name) +
              ' and year ' + str(year) + '\n', flush=True)
        pool.apply_async(
                        patent_claim_PatentView,
                        args=(
                              yearly_link,
                              year,
                              list(control_PatentsView_patents.patent_num),
                              output_path,
                              'PatentsView_ControlPatents_' + output_name
                              )
                        )
    pool.close()
    pool.join()

    return

########################################################################
# Main Executions
########################################################################
if __name__ == '__main__':

    print('Start main routine')
    ####################################
    # Parameter and Input Definition
    ####################################
    # Application publication years to be checked (2 year frame)
    min_year_global = 2005
    max_year_global = 2021

    #----------------------------------------
    # Define output path
    output_path = 'Alice_Claim_Extraction_v' + str(VERSION)

    #====================================
    # Create Output Path if not already exist
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    #====================================
    # Input Data

    # Use office action research dataset from Chief Economist of USPTO
    # source: https://www.uspto.gov/learning-and-resources/electronic-data-products/office-action-research-dataset-patents
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

    #====================================
    # Define Extraction Claims
    condition_rejections = (rejections.alice_in == 1)|(rejections.bilski_in == 1)|(rejections.mayo_in == 1)|(rejections.myriad_in==1)
    bilski_to_alice_rejections = rejections[condition_rejections].copy()

    #----------------------------------------
    #   Application data from Patent View
    #----------------------------------------
    if ('application_pregrant_publication.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Local
            application = pd.read_csv(PatentsView_directory + '/application_pregrant_publication.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from economic research dataset

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r'https://s3.amazonaws.com/data.patentsview.org/pregrant_publications/application.tsv.zip' , stream=True)
            if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'application_pregrant_publication.tsv'
        z.extract(z.infolist()[0])
        
        application = pd.read_csv(z.open(z.infolist()[0]), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        shutil.move('application_pregrant_publication.tsv', PatentsView_directory + '/application_pregrant_publication.tsv')

    #application = pd.read_csv(r"C:\Users\domin\Downloads\application.tsv\application.tsv", delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    application['app_id'] = pd.to_numeric(application.application_number,
                                            downcast = 'integer', errors = 'coerce')
    application['filing_date_dt'] = pd.to_datetime(application['date'], errors='coerce')
    application['filing_year'] = application.filing_date_dt.dt.year

    ####################################
    # Function Execution
    ####################################

    #---------------------------------------------
    # Bilski to Alice
    #---------------------------------------------

    print('Start control Claim Full Text extraction for Bilski, Mayo, Myriad, Alice')
    #===================================
    # Full text control patent claim extraction (internally parallel)
    #!!! => See in function for tpye analysis of rejection, office_actions, and application data

    control_patent_claim_fulltext_extraction(
                                             rejections_data = bilski_to_alice_rejections,
                                             application_df = application,
                                             nclasses = 100,
                                             output_path = output_path,
                                             min_year = min_year_global,
                                             max_year = max_year_global,
                                             output_name = 'Bilski_to_Alice_v' + str(VERSION)
                                             )

    print('End control Claim Full Text extraction for Bilski, Mayo, Myriad, Alice')
    #===================================
    # Full text claim extraction


    #---------------------------------------------
    # Bilski to Alice
    #---------------------------------------------
    print('Start rejected Claim Full Text extraction for Bilski, Mayo, Myriad, Alice')
    # Coerce to app_id to integer => all relevant app_ids are digits
    # rejections.app_id.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True    10133179
    bilski_to_alice_rejections['app_id_int'] = pd.to_numeric(bilski_to_alice_rejections.app_id,
                                                             downcast = 'integer', errors = 'coerce')

    #alice_rejections['app_id_str'] = alice_rejections.app_id.astype(str)

    # Find document numbers from PatentsView Pre-grant application data
    bilski_to_alice_rejections_application_with_doc_num = application[
        application.app_id.isin(list(bilski_to_alice_rejections.app_id_int))][
            ['app_id', 'document_number', 'filing_date_dt', 'filing_year']].drop_duplicates()
    
    print('\t Number of extractable application with rejections by Bilski, Mayo, Myriad, Alice: ' + str(len(bilski_to_alice_rejections_application_with_doc_num)), flush=True)
    #-------------------------------------------------------
    url_link_list = _url_claim_PatentView_PreGrant()
    
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start rejected claim extraction for Bilski to Alice for year ' + str(year) + '\n')
        pool.apply_async(
                        application_claim_PatentView,
                        args=(
                              yearly_link,
                              year,
                              bilski_to_alice_rejections_application_with_doc_num,
                              output_path,
                              'Bilski_to_Alice_v' + str(VERSION)
                              )
                        )
    pool.close()
    pool.join()


    print('End rejected Claim Full Text extraction for Bilski, Mayo, Myriad, Alice')

    #r'''
    ####################################
    # Function Execution Alice only
    ####################################

    alice_condition = (rejections.alice_in == 1)
    alice_rejections = rejections[alice_condition].copy()


    print('Start control Claim Full Text extraction  for Alice only')
    #===================================
    # Full text control patent claim extraction (internally parallel)
    #!!! => See in function for tpye analysis of rejection, office_actions, and application data

    #---------------------------------------------
    # Alice only
    #---------------------------------------------
    control_patent_claim_fulltext_extraction(
                                             rejections_data = alice_rejections,
                                             application_df = application,
                                             nclasses = 50,
                                             output_path = output_path,
                                             min_year = min_year_global,
                                             max_year = max_year_global,
                                             output_name = 'Alice_v' + str(VERSION)
                                             )

    print('End control Claim Full Text extraction for Alice only')
    #===================================
    # Full text claim extraction
    print('Start rejected Claim Full Text extraction for Alice only')

    #---------------------------------------------
    # Alice only
    #---------------------------------------------
    # Coerce to app_id to integer => all relevant app_ids are digits
    # rejections.app_id.astype(str).apply(lambda x: x.isdigit()).value_counts()
    # True    10133179
    alice_rejections['app_id_int'] = pd.to_numeric(alice_rejections.app_id, downcast = 'integer', errors = 'coerce')


    # Find document numbers from PatentsView Pre-grant application data
    alice_rejections_application_with_doc_num = application[
        application.app_id.isin(list(alice_rejections.app_id_int))][
            ['app_id', 'document_number', 'filing_date_dt', 'filing_year']].drop_duplicates()
    
    print('\t Number of extractable application with rejections by Alice only: ' + str(len(alice_rejections_application_with_doc_num)), flush=True)
    #-------------------------------------------------------
    url_link_list = _url_claim_PatentView_PreGrant()
    
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start rejected claim extraction for Alice only for year ' + str(year) + '\n')
        pool.apply_async(
                        application_claim_PatentView,
                        args=(
                              yearly_link,
                              year,
                              alice_rejections_application_with_doc_num,
                              output_path,
                              'Alice_v' + str(VERSION)
                              )
                        )
    pool.close()
    pool.join()

    print('End rejected Claim Full Text extraction for Alice only')
    r'''
    r'''
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Linear Execution
    # for year_itter in range(min_year, max_year + 1):
    #   claim_fulltext_extraction(search_ids = list(alice_rejections.app_id), year = year_itter, output_name = 'Alice_v' + str(VERSION))
    #r'''

    print('End main routine')

