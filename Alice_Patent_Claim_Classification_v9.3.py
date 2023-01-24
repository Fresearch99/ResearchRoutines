# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 9/16/2020
METHOD: Patent Claim Classification of Existing Patents
        Load trained pipeline from Alice_NLP_claim_classification_model_build
            and pickled list of in affected patent classes
    VERSION 2: Use NLP model from v2; use RBF and Poly SVC model
    VERSION 3: Testing sequence of model with LIME, WordCloud visualisiation
    VERSION 4: Change patent classes that are affected, Linear model classification
    VERSION 5: Remove error message from saving classified claims
    VERSION 6: Include binar prediction from model
    VERSION 7: Classification alternative based on CPC classes of affected patents
        Subverison 1: Correct mistake in LIME (predict_proba instead of predict needed)
        Subversion 2: Limit word cloud creation to 1000000 observations for cpc classification
                        Drop other classifications than poly2
    VERSION 8: Use current USPC classes to find patents for classification
        Subversion 1: Request method with length checking and no streaming
    VERSION 9: Classification of application claims
        Subversion 1: Use 2019 application data release
        Subversion 2: Use 2020 application data release and update dataset names & url and submission routine for Google Cloud
                        Create also subdirectories for the annual classification and claim extraction outputs
        Subversion 9.3 (DATE 3/11/2022): Use PatentsViews Pre-grant application publications for
                        model building and claim classification
                        !!! CPC at filing for application data only available starting 2013!!
                        !!! cpc_current version for version 2013-01-01 seems more complete, also this verison is the most complete !!!
"""
# !!! Slight changes in classified patents to be expected due to recurring updates in the claim files

# sbatch Alice_Patent_Claim_Classification_v9.3.sh
# seff JOB-ID for efficiency details

r'''
# conda activate py37 before submission, just to make sure packages can be loaded
#------------------------------------
#!/bin/bash
#
# Submit this script using: sbatch script-name
#
#SBATCH -p n2d-standard-32 # partitions  c2-standard-30

#SBATCH --nodes=1                    # Run all processes on a single node
#SBATCH --ntasks=8                   # Number of processes
#SBATCH --nodelist=bear-compute-1-2  # Specify node to run on => check with sinfo which are idle
#SBATCH --mem 61G # memory pool for all cores


#SBATCH --ntasks=1 # Submit srun only once
#SBATCH --cpus-per-task=10 # number of cores
#SBATCH --mem-per-cpu=6G # memory per cpu

#SBATCH -p n2d-standard-32 # partitions  c2-standard-30
#SBATCH -c 16 # number of cores
#SBATCH --mem 61G # memory pool for all cores
#SBATCH -o slurm.%N.%j.out # STDOUT
#SBATCH -e slurm.%N.%j.err # STDERR

#SBATCH -o slurm.%N.%j.out # STDOUT
#SBATCH -e slurm.%N.%j.err # STDERR

cd $WORKING_DIR

srun  ~/.conda/envs/py37/bin/python3 Alice_Patent_Claim_Classification_v9.3.py

#============================================
# Execution on hpc.haastech.org
#!/usr/bin/bash
#BSUB -n 1
#BSUB -e batch_output_directory/%J.err
#BSUB -o batch_output_directory/%J.out
# cd run _folder
# execute program
source activate py38
/apps/anaconda3/bin/python Alice_Patent_Claim_Classification_v9.3.py

#----------------------------
bsub <Alice_Patent_Claim_Classification_v9.3.sh

r'''

#######################################################
#   Load Environment
#######################################################

import pandas as pd
import numpy as np
import re
import os
import shutil

import pickle
import joblib

import requests
from io import BytesIO
import zipfile
import csv
from lxml import html

import multiprocessing as mp

from lime.lime_text import LimeTextExplainer
import wordcloud
from sklearn.feature_extraction.text import TfidfVectorizer

# Set seed
RANDOM_SEED = 42

# Version of Current Build
VERSION_BUILD = 9.3

# Version of Model Build to be loaded
INPUT_VERSION_BUILD = 7.5

#----------------------------------------
# Expand field limit to iterate through all claims
import ctypes
csv.field_size_limit(int(ctypes.c_ulong(-1).value // 2))
csv.field_size_limit()

#----------------------------------------
# Define how many cpc classes should be considered for classification (for general classification and only using uspc 705)
CPC_NCLASSES = 5

CPC_NCLASSES_705 = 3

#---------------------------------------------------
# Define PatentsView directory
PatentsView_directory = 'PatentsView_raw_data'

r'''
pd.set_option('display.max_rows', 100)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 120)
r'''

##################################################
#   Full text classification of patent claims
##################################################

#============================================
#  Executable link extraction
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

# =============================================================================
# Yearly application claim classification
# =============================================================================

def patent_claim_classificationn_Applications(search_classes, output_path,
                                              nlp_model,
                                              year = 2006, output_name = 'v7'):
    '''
    METHOD: Extracts from USPTO bulk website full text application claims
            for given list of cpc id's and classify
    INPUT:  search_classes: List of str cpc classes to be searched for
            output_path: Path to output directory
            nlp_model: sklearn-Pipeline for classification of text
            year: publication year of application to be extracted
            output_name: string of added to the end of the outpuf file name for classificaiton type
    OUTPUT: Application_claim_extraction: DF with extracted claims for publication year
                with main cpc subclass in the respective search_classes list
                and claim text classified with the nlp_model
    RETURN: NONE
    '''
    #==========================================
    # Convert search_classes to str
    search_classes = [str(s) for s in search_classes]

    ##########################################
    # Text Normalization Routine             #
    ##########################################
    #import unicodedata
    def _text_nomralization(text):
        #text = unicodedata.normalize('NFC', text)
        # remove residual html tags
        text = re.sub(re.compile('<.*?>'), ' ', text)

        text = re.sub(r'\n|\r|\t', ' ', text)
        # Remove double spacing and backslashes
        text = re.sub(r'\s+', ' ', text)
        # Remove leading space
        text = text.strip()

        return text

    ######################################################
    # Older patents don't have the cpc main classes,
    # thus, use the ipcr classifier
    ipcr_cpc_concordance_url = r'https://www.cooperativepatentclassification.org/cpc/concordances/cpc-ipc-concordance.xml'

    response = requests.get(ipcr_cpc_concordance_url)
    tree = html.fromstring(response.content)

    concordance_table = {}
    #for item in tree.xpath("//level[contains(text(), '0')]/parent::*"):
    for item in tree.xpath("//item"):
       concordance_table[item.xpath("ipc")[0].text] = item.xpath("cpc")[0].text

    ######################################################

    print('Start of Application Claim Classification Routine for year: ' + str(year), flush=True)

    bulk_data_url = r'https://bulkdata.uspto.gov/'

    for request_attempt in range(5):
        request = requests.get(bulk_data_url)
        if (request.ok == True):
            break

    tree = html.fromstring(request.content)

    # Find URLs to fulltext applications
    links = tree.xpath("//a[contains(@href, 'application/redbook/fulltext')]")
    # Get links to years in respective range
    url_link_list = [(l.get('href'), int(l.get('href') .split('/')[-1])) for l in links if int(l.get('href') .split('/')[-1]) == year]

    for yearly_url, year in url_link_list:
        print('\t Begin iteration through publication links for output ' + str(output_name) +
              ' year ' + str(year) + ', found URL: ' +
              str(yearly_url), flush=True)

        # Sometimes the multiprocesses don't load, thus restart
        for attempts_for_sublisting in range(5):

            # Wrapper for recall of request method if not fully fetched
            for request_attempt in range(5):
                request_yearly = requests.get(yearly_url)
                print('\t\t Year ' + str(year) + ', status code in attempt: '  +
                          str(attempts_for_sublisting + 1) +
                          ': ' + str(request_yearly.status_code) +
                          ' request attempt: ' + str(request_attempt), flush=True)
                if (request_yearly.ok == True):
                   break

            yearly_tree = html.fromstring(request_yearly.content)

            #------------------------------------------
            # Create yearly output df

            output_columns_names = ['app_id',
                                    'pgpub_number',
                                    'cpc_main_subclass',
                                    'cpc_main_identifiers',
                                    'ipcr_main_identifiers',
                                    'publication_identifiers',
                                    'pgpub_kind',
                                    'pgpub_date',
                                    'application_identifiers',
                                    'app_date',
                                    'invention_title',
                                    'us_related_documents',
                                    'priority_claims',
                                    'parent_doc',
                                    'child_doc',
                                    'claim_number',
                                    'claim_integer',
                                    'text',
                                    'indep_claim',
                                    'predicted_label']

            # Extend the output claim by the class names from the nlp model
            output_columns_names.extend(nlp_model.classes_.astype(str))

            claim_text_df = pd.DataFrame(columns = output_columns_names)

            #------------------------------------------

            # Find all yearly zip files
            zip_files = yearly_tree.xpath("//a[contains(@href, '.zip')]")

            # Get links to zip files
            zip_url_link_list = [l.get('href') for l in zip_files]
            print('\t\t\t Sublists found for ' + str(output_name) +
                  ' year ' + str(year) + ': \n' + str(zip_url_link_list), flush=True)

            # check if sublists were produced
            if len(zip_url_link_list) == 0:
                print('\t\t\t No sublists found for ' + str(output_name) +
                  ' year ' + str(year) + ', current attempts: ' + str(attempts_for_sublisting) +
                  ', try again', flush=True)
            else:
                # Worked, so create content table
                #---------------------------------------
                # Create content table for check sum of byte size
                for attempts_for_content_table in range(5):
                    try:
                        table = yearly_tree.xpath("//table")[1]
                        data = [[str(td.text_content()) for td in tr.xpath('td')] for tr in table.xpath('//tr')]

                        content_table = pd.DataFrame(data, columns=data[0])
                        print('\t\t\t\t Content table for ' + str(output_name) +
                              ' year ' + str(year) + ' attempt: ' + str(attempts_for_content_table) +
                              ': \n' + str(content_table), flush=True)
                        break

                    except Exception:
                        print('\t\t\t\t Content table not created for ' + str(output_name) +
                              ' year ' + str(year) + ' attempt: ' + str(attempts_for_content_table), flush=True)
                        #retry
                break

        #================================================
        for zip_url_link_publication in zip_url_link_list:
            print('\t\t Sublist: ' + str(zip_url_link_publication), flush=True)

            # Read zip file via IO stream

            # Wrap around limited amount of retrys
            for request_attempt in range(5):
                r = requests.get(yearly_url + '/' + zip_url_link_publication)

                print('\t\t Sublist: ' + str(zip_url_link_publication) +
                      ', length of request: ' +
                      str(len(r.content)) +
                      ' request attempt: ' + str(request_attempt), flush=True)

                # Check content lengt
                byte_len = int(content_table.loc[content_table.iloc[:, 0] == zip_url_link_publication, ].iloc[:, 1])
                if (r.ok == True) & \
                   (len(r.content) == byte_len) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                    print('\t\t Sublist: ' + str(zip_url_link_publication) +
                          ' checked for length and loaded', flush=True)
                    break

            z = zipfile.ZipFile(BytesIO(r.content))

            # Local debugging
            # z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa180510.zip")
            # z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa060105.zip")
            # z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa050106.zip")
            #z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa060928.zip")


            # Decode bytes object into string by following encoding of xml files
            document_string = z.open(z.infolist()[0].filename).read().decode('utf-8')

            # For debugging, search for app_id:14027103, earliest pub: US20140276241A1

            #============================================================
            # Extract surrounding xml tree for each us-application:

            # Identify location of searched id in concatenated xml string
            # NOTE: integer conversion causes leading zeros to be dropped
            #id_positions = re.search('<doc-number>0*' + str(app_id_search) + '</doc-number>', document_string).span()
            id_positions = [m.end() for m in re.finditer('<us-patent-application', document_string)]

            for id_pos in id_positions:
                #id_pos=437120144
                try:
                    # Search the start tags:
                    start_tag_spans = max([s.span()[0] for s in re.compile('<us-patent-application.*>').finditer(document_string) if s.span()[0] < id_pos])

                    # Search the end tags:
                    end_tag_spans = min([s.span()[1] for s in re.compile('</us-patent-application>').finditer(document_string) if s.span()[1] > id_pos])

                    # Extract subtree
                    subtree_string = document_string[start_tag_spans:end_tag_spans]
                    #-----------------------------------


                    #==================================
                    # Extract the relevant data and add to claim fulltext df
                    # Create Subtree
                    document_tree = html.fromstring(subtree_string)


                    #document_tree.getchildren()[0].getchildren()[3].getchildren()[0].getchildren()[1].text
                    # document_tree.getchildren()[0].getchildren()[3].getchildren()[0].text_content()
                    #for child in document_tree.getchildren()[0].getchildren()[3].getchildren()[0]:
                    #    print(child.tag, child.text)

                    if len(document_tree.xpath("//main-cpc")) != 0:
                        # !! find cpc main subclass and compare to list
                        main_cpc_subclass = str(document_tree.xpath("//main-cpc/*/section")[0].text)\
                            + str(document_tree.xpath("//main-cpc/*/class")[0].text)\
                            + str(document_tree.xpath("//main-cpc/*/subclass")[0].text)
                    else:
                        # use concordance and ipc classification
                        if len(document_tree.xpath("//classifications-ipcr")) != 0: #main vintage of 2006
                            main_ipcr_subclass = str(document_tree.xpath("//classifications-ipcr/*/section")[0].text)\
                                + str(document_tree.xpath("//classifications-ipcr/*/class")[0].text)\
                                + str(document_tree.xpath("//classifications-ipcr/*/subclass")[0].text)\
                                + str(document_tree.xpath("//classifications-ipcr/*/main-group")[0].text)\
                                + "/" + str(document_tree.xpath("//classifications-ipcr/*/subgroup")[0].text)
                        else:
                            if len(document_tree.xpath("//main-classification")) != 0: # main vintage of 2005
                                main_ipcr_subclass = document_tree.xpath("//main-classification")[0].text
                                # Replace leading zeros in the main group digits
                                grouped_string = re.search(r'(^\w\d{2,2}\w)(\d{1,3})/(\d+)', main_ipcr_subclass)
                                main_ipcr_subclass = grouped_string.group(1)\
                                   + str(int(grouped_string.group(2)))\
                                   + "/" + grouped_string.group(3)

                        main_cpc_subclass = re.search(r'^\w\d{2,2}\w', concordance_table[main_ipcr_subclass]).group(0)
                    ####################################################
                    #!!!
                    if not(main_cpc_subclass in search_classes):
                        continue
                    ####################################################

                    # main cpc classification
                    main_cpc_dict = {}
                    if len(document_tree.xpath("//main-cpc")) != 0:
                        for item in document_tree.xpath("//main-cpc")[0].getchildren()[0].iterdescendants():
                            main_cpc_dict[item.tag] = item.text_content()

                    # main ipcr classification
                    ipcr_dict = {}
                    if len(document_tree.xpath("//classifications-ipcr")) != 0:
                        for item in document_tree.xpath("//classifications-ipcr")[0].getchildren()[0].iterdescendants():
                            ipcr_dict[item.tag] = item.text_content()

                    # publication reference:
                    publication_identifiers_dict = {}
                    if len(document_tree.xpath("//publication-reference")) != 0:
                        for item in document_tree.xpath("//publication-reference")[0].iterdescendants():
                            publication_identifiers_dict['pgpub_'+item.tag] = _text_nomralization(item.text)

                    #======================================
                    # Detail data from publication information
                    #--------------------------------------
                    # Get pgpub number
                    if len(document_tree.xpath("//publication-reference/document-id/doc-number")) != 0:
                        pgpub_id = _text_nomralization(document_tree.xpath("//publication-reference/document-id/doc-number")[0].text)
                    else:
                        pgpub_id = ''
                    #--------------------------------------

                    #--------------------------------------
                    # Get pgpub kind
                    if len(document_tree.xpath("//publication-reference/document-id/kind")) != 0:
                        pgpub_kind = _text_nomralization(document_tree.xpath("//publication-reference/document-id/kind")[0].text)
                    else:
                        pgpub_kind = ''
                    #--------------------------------------

                    #--------------------------------------
                    # Get pgpub date
                    if len(document_tree.xpath("//publication-reference/document-id/date")) != 0:
                        pgpub_date = _text_nomralization(document_tree.xpath("//publication-reference/document-id/date")[0].text)
                        pgpub_date = str(pd.to_datetime(pgpub_date, format='%Y%m%d').date())
                    else:
                        pgpub_date = ''
                    #---------------------------------------

                    #========================================
                    # application reference:
                    application_identifiers_dict = {}
                    if len(document_tree.xpath("//application-reference")) != 0:
                        for item in document_tree.xpath("//application-reference")[0].iterdescendants():
                            application_identifiers_dict['app_'+item.tag] = _text_nomralization(item.text)


                    #----------------------------------------
                    # Detail data from publication information
                    #---------------------------------------
                    # Get app id as integer
                    if len(document_tree.xpath("//application-reference/document-id/doc-number")) != 0:
                        app_id = int(_text_nomralization(document_tree.xpath("//application-reference/document-id/doc-number")[0].text))
                    else:
                        app_id = np.nan
                    #--------------------------------------

                    #--------------------------------------
                    # Get app date
                    if len(document_tree.xpath("//application-reference/document-id/date")) != 0:
                        app_date = _text_nomralization(document_tree.xpath("//application-reference/document-id/date")[0].text)
                        app_date = str(pd.to_datetime(app_date, format='%Y%m%d').date())
                    else:
                        app_date = ''
                    #--------------------------------------

                    #######################################################
                    print('\t\t\t ID extraction for application number: ' + str(app_id) + \
                          ' in file ' + str(zip_url_link_publication) +
                          ' from cpc main class: ' + str(main_cpc_subclass), flush=True)

                    #######################################################

                    #======================================
                    # US related documents
                    us_related_documents_dict = {}
                    us_related_documents_n = 1
                    if len(document_tree.xpath("//us-related-documents")) != 0:
                        for item in document_tree.xpath("//us-related-documents")[0].iterchildren():
                            for item_item in item.iterchildren():
                                us_related_documents_dict['usreldoc_'+item_item.tag+'_'+str(us_related_documents_n)] = _text_nomralization(item_item.text_content())
                            us_related_documents_n += 1

                    #--------------------------------------
                    # Title
                    if len(document_tree.xpath("//invention-title")) != 0:
                        invention_title = _text_nomralization(document_tree.xpath("//invention-title")[0].text_content())
                    else:
                        invention_title = ''
                    #--------------------------------------

                    #=========================================
                    # Additional claim identifiers
                    # Priority claims:
                    priority_claims_dict = {}
                    priority_claims_n = 1
                    if len(document_tree.xpath("//priority-claims")) != 0:
                        for item in document_tree.xpath("//priority-claims")[0].iterchildren():
                            for item_item in item.iterchildren():
                                priority_claims_dict['priority_claims_'+item_item.tag+'_'+str(priority_claims_n)] = _text_nomralization(item_item.text)
                            priority_claims_n += 1


                    # Continuation patents
                    parent_doc_dict = {}
                    parent_doc_n = 1
                    if len(document_tree.xpath("//parent-doc")) != 0:
                        for item in document_tree.xpath("//parent-doc")[0].iterchildren():
                            for item_item in item.iterchildren():
                                parent_doc_dict['parent_doc_'+item_item.tag+'_'+str(parent_doc_n)] = _text_nomralization(item_item.text)
                            parent_doc_n += 1

                    child_doc_dict = {}
                    child_doc_n = 1
                    if len(document_tree.xpath("//child-doc")) != 0:
                        for item in document_tree.xpath("//child-doc")[0].iterchildren():
                            for item_item in item.iterchildren():
                                child_doc_dict['child_doc_'+item_item.tag+'_'+str(child_doc_n)] = _text_nomralization(item_item.text)
                            child_doc_n += 1

                    #======================================
                    # Claim extraction
                    claims = document_tree.xpath("//claims/claim")

                    for claim_item in claims:
                        # Get the entire text from the claim
                        claim_text = claim_item.text_content()
                        claim_text = _text_nomralization(claim_text)

                        # Get claim number of claim from value of the tag
                        claim_num = claim_item.values()[1]

                        try:
                            claim_int = int(claim_num)
                        except Exception:
                            # For the case of non-valid integers (e.g. cancelations)
                            claim_int = -1

                        # Iterate through the children of the claim-text (which is by itself the first child of the
                        # the claim element) and see if any of them is tagged as a claim-ref, meaning it is
                        # a dependent claims
                        child_tags = [child.tag for child in claim_item.getchildren()[0].getchildren()]
                        indep_claim = int(not('claim-ref' in child_tags))

                        #-------------------------------
                        # Only extract independent claims:
                        if indep_claim == 1:
                            append_list = [app_id, pgpub_id, main_cpc_subclass,
                                           main_cpc_dict.__str__(),
                                           ipcr_dict.__str__(),
                                           publication_identifiers_dict.__str__(),
                                           pgpub_kind,
                                           pgpub_date,
                                           application_identifiers_dict.__str__(),
                                           app_date,
                                           invention_title,
                                           us_related_documents_dict.__str__(),
                                           priority_claims_dict.__str__(),
                                           parent_doc_dict.__str__(),
                                           child_doc_dict.__str__(),
                                           claim_num, claim_int, claim_text,
                                           indep_claim]

                            # Expand by predicted label and the classification probs
                            append_list.extend(nlp_model.predict([claim_text]))
                            append_list.extend(nlp_model.predict_proba([claim_text]).tolist()[0])

                            claim_text_df.loc[len(claim_text_df)] = append_list
                            # Save output after number of itterations
                            if len(claim_text_df) % 5000 == 0:
                                claim_text_df.to_csv(path_or_buf = output_path +
                                                     '/FullText_Patent_claim_ApplicationPublications_Alice_predicted_' +
                                                     str(year) + '_' + output_name + '.csv', index = False, encoding = 'utf-8')

                except Exception as exc:
                    # !!! For errors that printout only a class number, this is most likely an error
                    # in the concordance between ipc and cpc, a key error that the ipc number doesn't have a
                    # concordance to a cpc class.
                    print('Error in file itteration for output ' + str(output_name) +
                          ' year ' + str(year) + ', Sublist ' + str(zip_url_link_publication) +
                          ', string position: '+ str(id_pos) +
                          ' :' + str(exc), flush=True)
        claim_text_df.to_csv(path_or_buf = output_path + '/FullText_Patent_claim_ApplicationPublications_Alice_predicted_' +
                             str(year) + '_' + output_name + '.csv', index = False, encoding = 'utf-8')

    print('End of Application Claim Classification Routine for output ' + str(output_name) +
          ' year: ' + str(year) + '; length of claim DF: ' + str(len(claim_text_df)), flush=True)
    return


#=========================================================================
# Yearly patent claim classification
#=========================================================================
def patent_claim_classification_PatentView(yearly_link, year,
                                            affected_patent_list, nlp_model,
                                            output_path, output_name):
    '''
    METHOD: Extracts from USPTO PatentsView claim text and predict classification
    INPUT:  yearly_link: url to PatentView claim text
            year: publication year for claim text from URL
            affected_patent_list: List with 'patent_id' as int
            nlp_model: sklearn-Pipeline for classification of text
            output_path: Path to output directory
            min_year: first year of patent publications to be extracted
            output_name: string of added to the end of the outpuf file name for classificaiton type
    OUTPUT: FullText_Patent_claim_PatentView_Alice_predicted: DF with extracted independent claims text
                                                             for publication year
                                                             and predicted classification
                                                             from the nlp model -> saved in output_path
             PredOnly_Patent_claim_PatentView_Alice_predicted: DF with patent_id and
                                                               predicted classification
                                                               according to nlp model -> saved in output_path
    '''

    #------------------------------
    # Turn patent id list into in
    affected_patent_list = [int(i) for i in affected_patent_list if not(np.isnan(i))]

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

        searched_indep_patents = indep_patent_claims[indep_patent_claims.patent_id.isin(affected_patent_list)]
        searched_indep_patents.reset_index(inplace=True, drop=True)
        #searched_indep_patents = indep_patent_claims.sample(n=1000, random_state=RANDOM_SEED)

        #------------------------------------------
        # Predicted invalidaiton likelihood
        predicted_porbabilities_text = nlp_model.predict_proba(searched_indep_patents.text)
        predictions_df = pd.DataFrame(predicted_porbabilities_text, columns=nlp_model.classes_.astype(str))

        predicted_label_text = pd.DataFrame(nlp_model.predict(searched_indep_patents.text),
                                            columns=['predicted_label'])

        predictions_df = pd.concat([predictions_df,
                                    predicted_label_text],
                                   axis=1,
                                   ignore_index=True,
                                   sort=False,
                                   verify_integrity=False)

        #-----------------------------------------
        # Merge with text data
        independent_claim_probabilities = pd.concat([searched_indep_patents,
                                                     predictions_df],
                                                    axis=1,
                                                    ignore_index=True,
                                                    sort=False,
                                                    verify_integrity=False)

        # Rename data frame columns
        name_list = list(searched_indep_patents.columns)
        name_list.extend(nlp_model.classes_.astype(str))
        name_list.extend(['predicted_label'])
        independent_claim_probabilities.columns = name_list

        #----------------------------------------
        # Output Result
        independent_claim_probabilities.to_csv(path_or_buf = output_path + '/FullText_Patent_claim_PatentView_Alice_predicted_' + str(year) + '_' + output_name + '.csv',
                                               index=False, encoding = 'utf-8')
        print('\t Lenght of output DF of classified independent claims for type ' + str(output_name) +
              ', year '+ str(year) + ': ' + str(len(independent_claim_probabilities)), flush=True)

        # Account for Format Change in 2005
        try:
            independent_claim_probabilities[['patent_id', 'num', 'sequence', '0', '1', 'predicted_label']].\
                to_csv(path_or_buf = output_path + '/PredOnly_Patent_claim_PatentView_Alice_predicted_' + str(year) + '_' + output_name + '.csv',
                       index=False, encoding = 'utf-8')

        except Exception:
            # print('\t\t Writeout Error in claims ID only for year: ' + str(year) + ' => ' + str(exc_wo))
            independent_claim_probabilities[['patent_id', 'claim_number', 'sequence', '0', '1', 'predicted_label']].\
                to_csv(path_or_buf = output_path + '/PredOnly_Patent_claim_PatentView_Alice_predicted_' + str(year) + '_' + output_name + '.csv',
                       index=False, encoding = 'utf-8')

    except Exception as exc:
        print('\t Error in claim search for year: ' + str(year) + ' => ' + str(exc))

    return([independent_claim_probabilities, independent_claim_probabilities[['patent_id', 'num', 'sequence', '0', '1', 'predicted_label']]])


#============================================
#  Executable application claim links
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
# Yearly pre-grant application claim classification
#=========================================================================
def application_claim_classification_PatentView(yearly_link, year,
                                                app_df, nlp_model,
                                                output_path, output_name):
    '''
    METHOD: Extracts application claim text from PatentsView pre-grant application data
            and predict classification
    INPUT:  yearly_link: url to PatentView Pre-grant application claim text
            year: publication year for claim text from URL
            app_df: df from application_pregrant_publication with searched document and application_id
            nlp_model: sklearn-Pipeline for classification of text
            output_path: Path to output directory
            year: publication year of application to be extracted
            output_name: string of added to the end of the outpuf file name
    OUTPUT: FullText_PregrantApp_claim_PatentView_Alice_predicted:
                DF with extracted independent claims text
                for publication year
                and predicted classification
                from the nlp model -> saved in output_path
             PredOnly_PregrantApp_claim_PatentView_Alice_predicted:
                 DF with app_id and predicted classification
                 according to nlp model -> saved in output_path
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

        #-----------------------------
        # Remove cancelled claims
        cancelled_condition = indep_app_claims.claim_text.\
                apply(lambda x: not(bool(re.search(r'canceled', re.sub('[^A-Za-z]','', x))) & bool(len(re.sub('[^A-Za-z]','', x)) < 20)))

        indep_app_claims = indep_app_claims[cancelled_condition]

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

        #------------------------------------------
        # Predicted invalidaiton likelihood
        predicted_porbabilities_text = nlp_model.predict_proba(searched_indep_app_claims.claim_text)
        predictions_df = pd.DataFrame(predicted_porbabilities_text, columns=nlp_model.classes_.astype(str))

        predicted_label_text = pd.DataFrame(nlp_model.predict(searched_indep_app_claims.claim_text),
                                            columns=['predicted_label'])

        predictions_df = pd.concat([predictions_df,
                                    predicted_label_text],
                                   axis=1,
                                   ignore_index=True,
                                   sort=False,
                                   verify_integrity=False)

        #-----------------------------------------
        # Merge with text data
        independent_claim_probabilities = pd.concat([searched_indep_app_claims,
                                                     predictions_df],
                                                    axis=1,
                                                    ignore_index=True,
                                                    sort=False,
                                                    verify_integrity=False)

        # Rename data frame columns
        name_list = list(searched_indep_app_claims.columns)
        name_list.extend(nlp_model.classes_.astype(str))
        name_list.extend(['predicted_label'])
        independent_claim_probabilities.columns = name_list

        #----------------------------------------
        # Output Result
        independent_claim_probabilities.to_csv(
            path_or_buf = output_path + '/FullText_PregrantApp_claim_PatentView_Alice_predicted_' + str(year) + '_' + output_name + '.csv',
            index=False, encoding = 'utf-8')
        print('\t Lenght of output DF of classified independent claims for type ' + str(output_name) +
              ', year '+ str(year) + ': ' + str(len(independent_claim_probabilities)), flush=True)

        independent_claim_probabilities[['app_id', 'claim_num', 'sequence', '0', '1', 'predicted_label']].\
            to_csv(path_or_buf = output_path + '/PredOnly_PregrantApp_claim_PatentView_Alice_predicted_' + str(year) + '_' + output_name + '.csv',
                   index=False, encoding = 'utf-8')

    except Exception as exc:
        print('\t Error in application claim search for year: ' + str(year) + ' => ' + str(exc))

    return([independent_claim_probabilities,
            independent_claim_probabilities[['app_id', 'claim_num', 'sequence', '0', '1', 'predicted_label']]])


#=============================================
# Classification Testing with Lime
#=============================================
def lime_text_explainer(patent_classification,
                        model,
                        version_string,
                        output_path=os.getcwd(),
                        size=1000):
    r'''
    METHOD: Use lime explainer to assess significant word for predict
    INPUT: - patent_classification: DF with classified patents text as attribute 'text'
           - model: classification nlp pipeline
           - output_path: str with directory to save outputs in
           - version_string: str, to be added to output for identification
           - size: int, size of sample drawn
    OUTPUT: - DF, top_wordlabel_LIMETextExplainer_raw containing the concatednated classifiers
            - DF, top_wordlabel_LIMETextExplainer_grouped with count and mean of word
    RETURN: DFs in list
    r'''
    #----------------------------------
    # Visualization with LIME
    # Source: https://towardsdatascience.com/explain-nlp-models-with-lime-shap-5c5a9f84d59b
    #         https://marcotcr.github.io/lime/tutorials/Lime%20-%20multiclass.html
    #         https://marcotcr.github.io/lime/tutorials/Lime%20-%20basic%20usage%2C%20two%20class%20case.html
    #         https://medium.com/@ageitgey/natural-language-processing-is-fun-part-3-explaining-model-predictions-486d8616813c
    #         https://www.oreilly.com/content/introduction-to-local-interpretable-model-agnostic-explanations-lime/
    r'''
    #---------------------------
    # Local debugging:
    patent_classification = pd.read_csv(r"C:\Users\domin\Desktop\FullText_Patent_claim_PatentView_Alice_predicted_1995_TFIDF_linear_cpc_vApplicationControls7.csv")
    model = joblib.load(r"C:\Users\domin\Desktop\tfidf_svc_linear_ApplicationControls7.joblib")
    size = 10
    #---------------------------
    r'''

    # Define Lime text explainer for a sample string
    explainer = LimeTextExplainer(random_state=RANDOM_SEED)

    # Iterate over 'size' strings random sample and show the most frequent word
    lime_text_sample = patent_classification.sample(n=size, random_state=RANDOM_SEED)

    #------------------------------------
    # Iterate through sample
    top_label_df = pd.DataFrame(columns=['word', 'weight'])
    for text_string in lime_text_sample.text:
        try:
            exp = explainer.explain_instance(text_instance=str(text_string),
                                             classifier_fn=model.predict_proba)

            top_label_df = pd.concat([top_label_df,
                                      pd.DataFrame(exp.as_list(), columns=['word', 'weight'])],
                                      axis = 0, ignore_index = True)
        except Exception as ex:
            print('\t\t Error in Lime Text exlanation for ' + str(version_string) +
                  ': Following text casued issue: ' + str(text_string) +
                  '=>' + str(ex))

    #------------------------------------
    # Output
    top_label_df.sort_values('weight', ascending=[False])
    top_label_df.to_csv(path_or_buf = output_path + '/top_wordlabel_LIMETextExplainer_raw_' + str(version_string) + '.csv',
                        index=False, encoding='utf-8')

    #------------------------------------
    # Grouping and output
    top_label_df_grouped = top_label_df.groupby(['word'])['weight'].agg(['mean', 'count']).reset_index()
    top_label_df_grouped.to_csv(path_or_buf = output_path + '/top_label_LIMETextExplainertop_wordlabel_LIMETextExplainer_grouped_' + str(version_string) + '.csv',
                                index=False, encoding='utf-8')

    return(top_label_df, top_label_df_grouped)

#====================================================
# Helper function for word cloud visualization
#====================================================
def _wordcloud_creation(model_data, output_directory, version_string=''):
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
    treated_wc.to_file(output_directory + '/wc_unweighted_predicted_treated_patentClaims_'+str(version_string)+'.jpg')

    untreated_wc = wc.generate(untreated_text)
    untreated_wc.to_file(output_directory + '/wc_unweighted_predicted_untreated_patentClaims_'+str(version_string)+'.jpg')


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
    diff_treated_wc.to_file(output_directory + '/wc_differential_frequency_weighting_predicted_treated_patentClaims_'+str(version_string)+'.jpg')

    diff_untreated_wc = wc.generate_from_frequencies(wc_untreated_weights)
    diff_untreated_wc.to_file(output_directory + '/wc_differential_frequency_weighting_predicted_untreated_patentClaims_'+str(version_string)+'.jpg')

    return

#============================================================
# Helper function word word cloud for LIME important word
#============================================================
def _wordcloud_top_label_df(top_label_df_grouped,
                            output_directory,
                            version_string):
    '''Wrapper for word cloud creation of LIME top weighted word for classification'''
    top_treated_words = top_label_df_grouped[top_label_df_grouped['mean'] > 0]. \
        sort_values(['count'], ascending=False).head(200)
    top_untreated_words = top_label_df_grouped[top_label_df_grouped['mean'] < 0]. \
        sort_values(['count'], ascending=False).head(200)

    #-----------------------------------------
    # get terms from LIME model and pair with frequency count
    wc_untreated_weights = {}
    for item in list(zip(top_untreated_words['word'], top_untreated_words['count'])):
        wc_untreated_weights[item[0]] = item[1]

    wc_treated_weights = {}
    for item in list(zip(top_treated_words['word'], top_treated_words['count'])):
        wc_treated_weights[item[0]] = item[1]

    #------------------------------------------

    wc = wordcloud.WordCloud(stopwords=wordcloud.STOPWORDS,
                                 background_color='white',
                                 max_font_size=40,
                                 color_func=lambda *args, **kwargs: "black",
                                 random_state=RANDOM_SEED)

    #-----------------------------------------
    # Create word cloud for both
    treated_wc = wc.generate_from_frequencies(wc_treated_weights)
    treated_wc.to_file(output_directory + '/wc_lime_wordCount_treated_patentClaims_'+str(version_string)+'.jpg')

    untreated_wc = wc.generate_from_frequencies(wc_untreated_weights)
    untreated_wc.to_file(output_directory + '/wc_lime_wordCount_untreated_patentClaims_'+str(version_string)+'.jpg')

    return

##############################################################
# Main Routine
##############################################################
def main_routine(input_version, output_version, cpc_nclasses):
    r'''wrapper for main routine, including the respective number of cpc classes corresponding to be classified
        INPUT: from Alice_NLP_classification_model_build:
            - TFIDF_SVC_Output: directory with main model for tfidf-SVM model and performance outputs
            - main_classes_Alice: pkl-file with list of uspc classes used for classification
        OUTPUT:
            - Alice_patent_classification: directory with various dataframes of classified patents
                                            Subdirectories for extracted and classified claims per year
                                            Wordcloud and LIME outputs for classified patents/applications
    r'''

    # Debugging elements
    # INPUT_VERSION='PatentsViewControls'+str(INPUT_VERSION_BUILD)
    # VERSION='PatentsViewControls'+str(VERSION_BUILD)
    # output_directory = r'Alice_patent_classification_' + str(VERSION)
    print('Start Main Routine for version: ' + str(output_version), flush=True)

    import time
    from datetime import timedelta
    start_time = time.time()
    #====================================
    # Define execution environment
    #====================================
    home_directory = os.getcwd() # Path where stored datasets should be located

    output_directory = r'Alice_patent_classification_v' + str(output_version)
    #====================================
    # Create Output Path if not already exist
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    #============================================
    #   Load Classification Model
    #from Alice_NLP_classification_model_build_v7 import custom_tokenizer, tokenizer, stop_words, Doc2VecTransformer
    # => Load also custom tokenizer from build class and Doc2VecTransformer

    text_poly2_svc = joblib.load('TFIDF_SVC_Output_'+str(input_version) + '//tfidf_svc_poly2_' + str(input_version) + '.joblib')
    #text_poly2_svc = joblib.load('tfidf_svc_poly2_' + str(INPUT_VERSION) + '.joblib')
    #nlp_model = joblib.load(r"C:\Users\domin\Desktop\tfidf_svc_linear_ApplicationControls7.2.joblib")


    #===============================================
    #   Collect searchable patents
    #===============================================
    print('\t Find patents that fit the desired classes', flush=True)

    #-------------------------------
    # uspc_current classifications
    #-------------------------------
    # Use current uspc classification to be more in aligne with cpc classification, AND
    # there seems to be an issue with classifications only reaching until 2013 assignments
    if ('uspc_current_PatentsView.tsv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        uspc_current = pd.read_csv('uspc_current_PatentsView.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from Patent View

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/uspc_current.tsv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break
        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'uspc_current_PatentsView.tsv'
        z.extract(z.infolist()[0])

        uspc_current = pd.read_csv(z.open(z.infolist()[0]), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #z = zipfile.ZipFile(BytesIO(r.content))
        #z.extractall()

        #uspc_current = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

    #---------------------------------
    # Load main uspc classes
    with open('main_classes_Alice_' + str(input_version) + '.pkl', 'rb') as fp:
         uspc_main_category = pickle.load(fp)

    print('\t USPC Main Classes for classification: ' + str(uspc_main_category), flush=True)

    #==============================================
    # Find patents to investigate in affected classes

    # => Note that the loaded categories are in int
    uspc_main_category_str = [str(c) for c in uspc_main_category]

    uspc_current['mainclass_id'] = uspc_current['mainclass_id'].astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    uspc_affected_patent = uspc_current[uspc_current.mainclass_id.isin(uspc_main_category_str)]
    #uspc_affected_patent = uspc_current[uspc_current.mainclass_id=='705']
    uspc_affected_patent = uspc_affected_patent[['patent_id', 'mainclass_id']].drop_duplicates()
    # Coerce to integer, since focusing on utility patents
    uspc_affected_patent['patent_id'] = pd.to_numeric(uspc_affected_patent.patent_id,
                                                      downcast='integer', errors='coerce')
    #uspc_current['patent_id'] = pd.to_numeric(uspc_current.patent_id, downcast='integer', errors='coerce')
    uspc_affected_patent_list = list(set(uspc_affected_patent.patent_id))
    #uspc_affected_patent_list = list(set(uspc_affected_patent.patent_id.astype(str).\
    #    apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))))
    print('\t Number of identified patents to be classified from USPC classes: '
          + str(len(uspc_affected_patent_list)), flush=True)

    # =============================================================================
    #  Direct claim classification
    # =============================================================================
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # !! Append here the application data which contain a lot of uspc classes

    print('\t Expand with patent ids from application data', flush=True)
    #----------------------------------
    # Application Data
    #----------------------------------
    if ('application_data_2020.csv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        application_data = pd.read_csv('application_data_2020.csv', low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from economic research dataset

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://bulkdata.uspto.gov/data/patent/pair/economics/2020/application_data.csv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'application_data_2020.csv'
        z.extract(z.infolist()[0])

        application_data = pd.read_csv(z.open(z.infolist()[0]), low_memory=False)

        #z = zipfile.ZipFile(BytesIO(r.content))
        #z.extractall()

        #application_data = pd.read_csv(z.open(z.infolist()[0].filename), low_memory=False)

    # Select the application with the fitting patent classes
    application_data['uspc_class'] = application_data['uspc_class'].astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    affected_applications = application_data[application_data.uspc_class.isin(uspc_main_category_str)]

    #pd.to_datetime(affected_applications.filing_date, errors='coerce').dt.year.value_counts()

    # Coerce to integer, since focusing on utility patents
    affected_applications['patent_id'] = pd.to_numeric(affected_applications.patent_number,
                                                       downcast='integer', errors='coerce')
    uspc_affected_application_publication_list = list(set(affected_applications.patent_id))
    # Expand patent list by patent ids from application data

    uspc_affected_patent_list.extend(uspc_affected_application_publication_list)

    print('\t Number of identified patents to be classified from USPC classes including application ids: '
          + str(len(uspc_affected_patent_list)), flush=True)


    # =============================================================================
    # Functional extraction of applications to be classified
    # =============================================================================

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

    #----------------------------------------
    #  USPC for Application data from Patent View
    #----------------------------------------
    if ('uspc_pregrant_publication.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Local
            uspc_app = pd.read_csv(PatentsView_directory + '/uspc_pregrant_publication.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from economic research dataset

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r'https://s3.amazonaws.com/data.patentsview.org/pregrant_publications/uspc.tsv.zip' , stream=True)
            if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'uspc_pregrant_publication.tsv'
        z.extract(z.infolist()[0])

        uspc_app = pd.read_csv(z.open(z.infolist()[0]), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        shutil.move('uspc_pregrant_publication.tsv', PatentsView_directory + '/uspc_pregrant_publication.tsv')


    #----------------------------------------
    #  CPC for Application data from Patent View
    #----------------------------------------
    # !!! cpc_current has three times as many observations than the cpc class
    # assigned at filing; this has to do with the classification being
    # version dependent for applications
    # !!! cpc classifications of applications only available after 2013!!!
    if ('cpc_current_pregrant_publication.tsv' in os.listdir(PatentsView_directory)):
            #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # Local
            cpc_app = pd.read_csv(PatentsView_directory + '/cpc_current_pregrant_publication.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from economic research dataset

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r'https://s3.amazonaws.com/data.patentsview.org/pregrant_publications/cpc_current.tsv.zip', stream=True)
            if (r.ok == True) & \
                   (len(r.content) == int(r.headers['Content-Length'])):
                   break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'cpc_current_pregrant_publication.tsv'
        z.extract(z.infolist()[0])

        cpc_app = pd.read_csv(z.open(z.infolist()[0]), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
        shutil.move('cpc_current_pregrant_publication.tsv', PatentsView_directory + '/cpc_current_pregrant_publication.tsv')

    # Focus on primary categories
    cpc_app = cpc_app[cpc_app.category=='inventional']

    # Focus on version '2013-01-01'
    cpc_app = cpc_app[cpc_app.version=='2013-01-01']

    #------------------------------------
    app_df = application.merge(
        uspc_app, on='document_number', how='left').merge(
            cpc_app, on='document_number', how='left')

    # Select the application with the fitting patent classes
    app_df['uspc_class'] = app_df['mainclass_id'].astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

    app_df_affected_uspc = app_df[app_df.uspc_class.isin(uspc_main_category_str)][
            ['app_id', 'uspc_class', 'document_number', 'filing_date_dt', 'filing_year']].drop_duplicates()


    #------------------------------------------
    # Treated applications according to USPC
    text_poly2_svc_PregrantApp_Claim_classification_uspc = pd.DataFrame()

    #-----------------------------------
    # Create sub-director for extracted texts to be classified
    suboutput_dir = output_directory+'//uspcAffectedApplication'
    if not os.path.exists(suboutput_dir):
        os.makedirs(suboutput_dir)


    #-------------------------------------------------------
    url_link_list = _url_claim_PatentView_PreGrant()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start classification application claims in affected uspc class, year: ' + str(year) + '\n')
        pool.apply_async(
                        application_claim_classification_PatentView,
                        args=(
                              yearly_link,
                              year,
                              app_df_affected_uspc,
                              text_poly2_svc,
                              suboutput_dir,
                              '_uspcAffectedApplication__v' + str(output_version)
                              )
                        )
    pool.close()
    pool.join()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Load from Target
    patent_classification_files = os.listdir(suboutput_dir)
    patent_classification_path = [suboutput_dir+'//'+f for f in patent_classification_files if \
                                  bool(re.search('.csv', f)) & bool(re.search('FullText', f)) & \
                                      bool(re.search('PregrantApp', f)) & \
                                      bool(re.search('_uspcAffectedApplication', f)) & bool(re.search(r'\d{4,4}', f))]

    for load_file in patent_classification_path:
        append_df = pd.read_csv(load_file, encoding='utf-8', low_memory=False)
        append_df['year'] = re.search(r'\d{4,4}', load_file).group(0)

        text_poly2_svc_PregrantApp_Claim_classification_uspc = pd.concat(
            [text_poly2_svc_PregrantApp_Claim_classification_uspc,
             append_df],
            axis=0)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save Fulltext output
    text_poly2_svc_PregrantApp_Claim_classification_uspc.to_csv(
        path_or_buf = output_directory +
        '/FullText_PregrantApp_claim_PatentView_Alice_predicted__uspcAffectedApplication__TFIDF_poly2__v' + str(output_version) + '.csv',
        index=False, encoding = 'utf-8')
    print('\t\t Total length of classified application data claims from Pregrant PatentsView - affected USPC based; TFIDF + SVC Poly 2: ' +
          str(len(text_poly2_svc_PregrantApp_Claim_classification_uspc)), flush=True)
    print('\t\t Unique classified application data from Pregrant PatentsView - affected USPC based; SVC Poly 2: ' +
          str(len(text_poly2_svc_PregrantApp_Claim_classification_uspc.app_id.unique())), flush=True)

    #------------------------------------------
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)


    # =============================================================================
    # CPC classification
    # =============================================================================
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #!!!! Most patents are now classified via CPC, as in Dugan (2018)
    # Translate affected patents into CPC classes
    # See: https://www.uspto.gov/patents-application-process/patent-search/classification-standards-and-development
    #-------------------------------
    # cpc classifications
    #-------------------------------
    if ('cpc_current_PatentsView.tsv' in os.listdir(home_directory)):
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Local
        cpc_current = pd.read_csv('cpc_current_PatentsView.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
    else:
        #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
        # Load application data from Patent View

        # Wrap around limited amount of retrys
        for request_attempt in range(5):
            r = requests.get(r"https://s3.amazonaws.com/data.patentsview.org/download/cpc_current.tsv.zip")
            if (r.ok == True) & \
               (len(r.content) == int(r.headers['Content-Length'])):
               break

        z = zipfile.ZipFile(BytesIO(r.content))
        z.infolist()[0].filename = 'cpc_current_PatentsView.tsv'
        z.extract(z.infolist()[0])

        cpc_current = pd.read_csv(z.open(z.infolist()[0]), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

        #z = zipfile.ZipFile(BytesIO(r.content))
        #z.extractall()

        #cpc_current = pd.read_csv(z.open(z.infolist()[0].filename), delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

    #-------------------------------------
    # Focus on primary categories
    cpc_current = cpc_current[cpc_current.category=='inventional']

    # Drop unneeded columns and make cpc groups unique
    cpc_current = cpc_current.drop(['uuid', 'section_id',
                                    'category', 'subgroup_id',
                                    'sequence'], axis=1).drop_duplicates()

    # Cast id to int
    cpc_current['patent_id'] = pd.to_numeric(cpc_current.patent_id,
                                             downcast='integer', errors='coerce')

    # Restrict to main class
    #cpc_current = cpc_current[cpc_current['sequence'] == 0]
    #-------------------------------------
    # Find patent_ids in the for the uspc classified
    cpc_uspc_patents = cpc_current[cpc_current.patent_id.isin([s for s in uspc_affected_patent_list if not(np.isnan(s))])]

    # select most common cpc classes
    main_cpc_classes = list(set(cpc_uspc_patents.group_id.value_counts(). \
                                nlargest(cpc_nclasses).reset_index()['index']))

    print('\t Most frequent CPC classes\n' + str(cpc_uspc_patents.group_id.value_counts(normalize=True).head(10).cumsum()), flush=True)
    # H04L    => TRANSMISSION OF DIGITAL INFORMATION, e.g. TELEGRAPHIC COMMUNICATION
    # G06Q    => DATA PROCESSING SYSTEMS OR METHODS, SPECIALLY ADAPTED FOR ADMINISTRATIVE, COMMERCIAL, FINANCIAL, MANAGERIAL, SUPERVISORY OR FORECASTING PURPOSES; SYSTEMS OR METHODS SPECIALLY ADAPTED FOR ADMINISTRATIVE, COMMERCIAL, FINANCIAL, MANAGERIAL, SUPERVISORY OR FORECASTING PURPOSES, NOT OTHERWISE PROVIDED FOR
    # G06F    => ELECTRIC DIGITAL DATA PROCESSING
    # A61P    => SPECIFIC THERAPEUTIC ACTIVITY OF CHEMICAL COMPOUNDS OR MEDICINAL PREPARATIONS
    # C12N    => MICROORGANISMS OR ENZYMES; COMPOSITIONS THEREOF; PROPAGATING, PRESERVING, OR MAINTAINING MICROORGANISMS; MUTATION OR GENETIC ENGINEERING; CULTURE MEDIA
    # C07K    => PEPTIDES
    # G01N    => INVESTIGATING OR ANALYSING MATERIALS BY DETERMINING THEIR CHEMICAL OR PHYSICAL PROPERTIES
    # H04N    => PICTORIAL COMMUNICATION, e.g. TELEVISION
    # A61K    => PREPARATIONS FOR MEDICAL, DENTAL, OR TOILET PURPOSES
    # C12Q    => MEASURING OR TESTING PROCESSES INVOLVING ENZYMES, NUCLEIC ACIDS OR MICROORGANISMS

    cpc_uspc_patents.group_id.value_counts(normalize=True).head(10).cumsum()
    #G06Q    0.406234 => DATA PROCESSING SYSTEMS OR METHODS, SPECIALLY ADAPTED FOR ADMINISTRATIVE, COMMERCIAL, FINANCIAL, MANAGERIAL, SUPERVISORY OR FORECASTING PURPOSES; SYSTEMS OR METHODS SPECIALLY ADAPTED FOR ADMINISTRATIVE, COMMERCIAL, FINANCIAL, MANAGERIAL, SUPERVISORY OR FORECASTING PURPOSES, NOT OTHERWISE PROVIDED FOR
    #G06F    0.480025 => ELECTRIC DIGITAL DATA PROCESSING
    #G07F    0.551197 => COIN-FREED OR LIKE APPARATUS
    #H04L    0.607321 => TRANSMISSION OF DIGITAL INFORMATION, e.g. TELEGRAPHIC COMMUNICATION
    #A63F    0.658519 => CARD, BOARD, OR ROULETTE GAMES; INDOOR GAMES USING SMALL MOVING PLAYING BODIES; VIDEO GAMES; GAMES NOT OTHERWISE PROVIDED FOR
    #H04N    0.698401 => PICTORIAL COMMUNICATION, e.g. TELEVISION
    #G09B    0.725411 => EDUCATIONAL OR DEMONSTRATION APPLIANCES; APPLIANCES FOR TEACHING, OR COMMUNICATING WITH, THE BLIND, DEAF OR MUTE; MODELS; PLANETARIA; GLOBES; MAPS; DIAGRAMS
    #G16H    0.742673 => HEALTHCARE INFORMATICS, i.e. INFORMATION AND COMMUNICATION TECHNOLOGY [ICT] SPECIALLY ADAPTED FOR THE HANDLING OR PROCESSING OF MEDICAL OR HEALTHCARE DATA
    #A61B    0.756516 => DIAGNOSIS; SURGERY; IDENTIFICATION
    #G01N    0.769756 => INVESTIGATING OR ANALYSING MATERIALS BY DETERMINING THEIR CHEMICAL OR PHYSICAL PROPERTIES

    # For 705 alone:
    #G06Q    0.514381
    #G06F    0.632402
    #H04L    0.702940

    cpc_uspc_patents.group_id.value_counts(normalize=True).head(10).cumsum()

    print('\t Selected main CPC classes\n' + str(main_cpc_classes), flush=True)
    # Define as patent ids those patents within the respective main CPC classes
    cpc_affected_patent_list = list(cpc_current[cpc_current.group_id.isin(main_cpc_classes)]['patent_id'])
    print('\t Number of affected cpc based patents: ' + str(len(cpc_affected_patent_list)), flush=True)

    del cpc_current, uspc_current

    #=========================================================================
    #   Prediction of Patent Classification from PatentView full text
    #=========================================================================
    print('\t Collect url to patent claim text', flush=True)
    url_link_list = _url_claim_PatentView(min_year=1980)

    #===============================================================
    # Parallel Execution of patent claim collection
    #===============================================================
    print('\t Classify patent claim text from URLs', flush=True)
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores), flush=True)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Define result storage df
    text_poly2_svc_PatentView_Claim_classification_uspc = pd.DataFrame()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    #-----------------------------------
    # Create sub-director for extracted texts to be classified
    suboutput_dir = output_directory+'//uspcAffected__TFIDF_poly2'
    if not os.path.exists(suboutput_dir):
        os.makedirs(suboutput_dir)
    #-----------------------------------

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        pool.apply_async(
                        patent_claim_classification_PatentView,
                        args=(
                              yearly_link,
                              year,
                              uspc_affected_patent_list,
                              text_poly2_svc,
                              suboutput_dir,
                              '_uspcAffected__TFIDF_poly2__v' + str(output_version)
                              )
                        )
    pool.close()
    pool.join()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Load from Target
    patent_classification_files = os.listdir(suboutput_dir)
    patent_classification_path = [suboutput_dir+'//'+f for f in patent_classification_files if \
                                  bool(re.search('.csv', f)) & bool(re.search('FullText', f)) & \
                                      bool(re.search('PatentView', f)) & \
                                      bool(re.search('_uspcAffected__TFIDF_poly2', f)) & bool(re.search(r'\d{4,4}', f))]

    for load_file in patent_classification_path:
        append_df = pd.read_csv(load_file, encoding='utf-8', low_memory=False)
        append_df['year'] = re.search(r'\d{4,4}', load_file).group(0)

        text_poly2_svc_PatentView_Claim_classification_uspc = pd.concat([text_poly2_svc_PatentView_Claim_classification_uspc,
                                                                         append_df],
                                                                        axis=0)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save Fulltext output
    text_poly2_svc_PatentView_Claim_classification_uspc.to_csv(path_or_buf = output_directory +
                                                               '/FullText_Patent_claim_PatentView_uspcAffected__Alice_predicted_TFIDF_poly2__v' + str(output_version) + '.csv',
                                                               index=False, encoding = 'utf-8')
    print('\t\t Total length of classified patent claims - affected USPC based; TFIDF + SVC Poly 2: ' +
          str(len(text_poly2_svc_PatentView_Claim_classification_uspc)), flush=True)
    print('\t\t Unique classified patents - affeced USPC based; SVC Poly 2: ' +
          str(len(text_poly2_svc_PatentView_Claim_classification_uspc.patent_id.unique())), flush=True)

    #--------------------------------------
    #--------------------------------------

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Define result storage df
    text_poly2_svc_PatentView_Claim_classification_cpc = pd.DataFrame()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    #-----------------------------------
    # Create sub-director for extracted texts to be classified
    suboutput_dir = output_directory+'//cpcAffected__TFIDF_poly2'
    if not os.path.exists(suboutput_dir):
        os.makedirs(suboutput_dir)
    #-----------------------------------

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        pool.apply_async(
                        patent_claim_classification_PatentView,
                        args=(
                              yearly_link,
                              year,
                              cpc_affected_patent_list,
                              text_poly2_svc,
                              suboutput_dir,
                              '_cpcAffected__TFIDF_poly2__v' + str(output_version)
                              )
                        )
    pool.close()
    pool.join()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Load from Target
    patent_classification_files = os.listdir(suboutput_dir)
    patent_classification_path = [suboutput_dir+'//'+f for f in patent_classification_files if \
                                  bool(re.search('.csv', f)) & bool(re.search('FullText', f)) & \
                                    bool(re.search('PatentView', f)) & \
                                      bool(re.search('_cpcAffected__TFIDF_poly2', f)) & bool(re.search(r'\d{4,4}', f))]

    for load_file in patent_classification_path:
        append_df = pd.read_csv(load_file, encoding='utf-8', low_memory=False)
        append_df['year'] = re.search(r'\d{4,4}', load_file).group(0)

        text_poly2_svc_PatentView_Claim_classification_cpc = pd.concat([text_poly2_svc_PatentView_Claim_classification_cpc,
                                                                         append_df],
                                                                        axis=0)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save Fulltext output
    text_poly2_svc_PatentView_Claim_classification_cpc.to_csv(path_or_buf = output_directory +
                                                               '/FullText_Patent_claim_PatentView_cpcAffected__Alice_predicted_TFIDF_poly2__v' + str(output_version) + '.csv',
                                                               index=False, encoding = 'utf-8')
    print('\t\t Total length of classified patent claims - affected CPC based; TFIDF + SVC Poly 2: ' +
          str(len(text_poly2_svc_PatentView_Claim_classification_cpc)), flush=True)
    print('\t\t Unique classified patents - affected CPC based; SVC Poly 2: ' +
          str(len(text_poly2_svc_PatentView_Claim_classification_cpc.patent_id.unique())), flush=True)


    #------------------------------------------
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)

    #===============================================
    #  Application text classification
    #===============================================
    print('\t Iterate through application text publications and classify if are in main cpc classes', flush=True)
    #!!! Since 2013 the USPTO switched to CPC classificaiton, so this is the only approach applied

    app_df_affected_cpc = app_df[app_df.group_id.isin(main_cpc_classes)][
            ['app_id', 'group_id', 'document_number', 'filing_date_dt', 'filing_year']].drop_duplicates()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Define result storage df
    text_poly2_svc_PregrantApp_Claim_classification_cpc = pd.DataFrame()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

    #-----------------------------------
    # Create sub-director for extracted texts to be classified
    suboutput_dir = output_directory+'//cpcAffectedApplication__TFIDF_poly2'
    if not os.path.exists(suboutput_dir):
        os.makedirs(suboutput_dir)

    #-------------------------------------------------------
    url_link_list = _url_claim_PatentView_PreGrant()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Parallel Execution
    cores = mp.cpu_count()
    print('\t\t Number of Cores: ' + str(cores))

    pool = mp.Pool(cores)
    # Run the scraping method for the contents required
    for yearly_link, year in url_link_list:
        print('\t Start classification for application in affected cpc group, year: ' + str(year) + '\n')
        pool.apply_async(
                        application_claim_classification_PatentView,
                        args=(
                              yearly_link,
                              year,
                              app_df_affected_cpc,
                              text_poly2_svc,
                              suboutput_dir,
                              '_cpcAffectedApplication__v' + str(output_version)
                              )
                        )
    pool.close()
    pool.join()

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Load from Target
    patent_classification_files = os.listdir(suboutput_dir)
    patent_classification_path = [suboutput_dir+'//'+f for f in patent_classification_files if \
                                  bool(re.search('.csv', f)) & bool(re.search('FullText', f)) & \
                                      bool(re.search('PregrantApp', f)) & \
                                      bool(re.search('_cpcAffectedApplication', f)) & bool(re.search(r'\d{4,4}', f))]

    for load_file in patent_classification_path:
        append_df = pd.read_csv(load_file, encoding='utf-8', low_memory=False)
        append_df['year'] = re.search(r'\d{4,4}', load_file).group(0)

        text_poly2_svc_PregrantApp_Claim_classification_cpc = pd.concat(
            [text_poly2_svc_PregrantApp_Claim_classification_cpc,
             append_df],
            axis=0)

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Save Fulltext output
    text_poly2_svc_PregrantApp_Claim_classification_cpc.to_csv(
        path_or_buf = output_directory +
        '/FullText_PregrantApp_claim_PatentView_Alice_predicted__cpcAffectedApplication__TFIDF_poly2__v' + str(output_version) + '.csv',
        index=False, encoding = 'utf-8')

    print('\t\t Total length of classified application claims from Pregrant PatentsView - affected CPC based; TFIDF + SVC Poly 2: ' +
          str(len(text_poly2_svc_PregrantApp_Claim_classification_cpc)), flush=True)
    print('\t\t Unique classified applications from Pregrant PatentsView - affected CPC based; SVC Poly 2: ' +
          str(len(text_poly2_svc_PregrantApp_Claim_classification_cpc.app_id.unique())), flush=True)

    #------------------------------------------
    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)


    #=================================================
    # WordCloud Generation
    #=================================================
    print('\t Create Word Clouds for predicted patent classes', flush=True)

    model_data_text_poly2_svc_uspc = text_poly2_svc_PatentView_Claim_classification_uspc[
        ['text', '1', 'predicted_label']
        ].drop_duplicates()

    # Create model text for word cloud and predict classification
    model_data_text_poly2_svc_uspc = model_data_text_poly2_svc_uspc.rename(columns={'text':'claim_text',
                                                                                    '1':'pred_treated'})
    #model_data_text_poly2_svc['treated'] = (model_data_text_poly2_svc.pred_treated > 0.5).astype(int)
    model_data_text_poly2_svc_uspc['treated'] = (model_data_text_poly2_svc_uspc.predicted_label == 1).astype(int)

    _wordcloud_creation(model_data=model_data_text_poly2_svc_uspc,
                        output_directory=output_directory,
                        version_string='PatentView_uspcAffected__Poly2_SVC__v' + str(output_version))

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    model_data_text_poly2_svc_cpc = text_poly2_svc_PatentView_Claim_classification_cpc[
        ['text', '1', 'predicted_label']
        ].drop_duplicates()

    # Create model text for word cloud and predict classification
    model_data_text_poly2_svc_cpc = model_data_text_poly2_svc_cpc.rename(columns={'text':'claim_text',
                                                                                    '1':'pred_treated'})
    #model_data_text_poly2_svc['treated'] = (model_data_text_poly2_svc.pred_treated > 0.5).astype(int)
    model_data_text_poly2_svc_cpc['treated'] = (model_data_text_poly2_svc_cpc.predicted_label == 1).astype(int)

    # !!! There are vastly more cpc classifications than uspc classification => randomly draw! if size over 1M
    if len(model_data_text_poly2_svc_cpc) > 1000000:
        model_data_text_poly2_svc_cpc = model_data_text_poly2_svc_cpc.sample(
            n=1000000,
            random_state = RANDOM_SEED,
            replace=False
            )

    _wordcloud_creation(model_data=model_data_text_poly2_svc_cpc,
                        output_directory=output_directory,
                        version_string='PatentView_cpcAffected__Poly2_SVC__v' + str(output_version))


    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    model_data_text_poly2_svc_appl = text_poly2_svc_PregrantApp_Claim_classification_cpc[
        ['text', '1', 'predicted_label']
        ].drop_duplicates()

    # Create model text for word cloud and predict classification
    model_data_text_poly2_svc_appl = model_data_text_poly2_svc_appl.rename(columns={'text':'claim_text',
                                                                                    '1':'pred_treated'})
    #model_data_text_poly2_svc['treated'] = (model_data_text_poly2_svc.pred_treated > 0.5).astype(int)
    model_data_text_poly2_svc_appl['treated'] = (model_data_text_poly2_svc_appl.predicted_label == 1).astype(int)

    # !!! There are vastly more cpc classifications than uspc classification => randomly draw! if size over 1M
    if len(model_data_text_poly2_svc_appl) > 1000000:
        model_data_text_poly2_svc_appl = model_data_text_poly2_svc_appl.sample(
            n=1000000,
            random_state = RANDOM_SEED,
            replace=False
            )

    _wordcloud_creation(model_data=model_data_text_poly2_svc_appl,
                        output_directory=output_directory,
                        version_string='PregrantApp_PatentsView_cpcAffected__Poly2_SVC__v' + str(output_version))


    #===============================================================
    # Patent Claim Classification Example
    #===============================================================
    print('\t Lime classification sample analysis', flush=True)

    _, top_label_df_grouped_poly2_svc_uspc =  lime_text_explainer(
        patent_classification=text_poly2_svc_PatentView_Claim_classification_uspc[
            ['text', '1', 'predicted_label']
            ].drop_duplicates(),
        model=text_poly2_svc,
        version_string='Poly2_SVC_uspc_v' + str(output_version),
        output_path=output_directory,
        size=1000)

    _wordcloud_top_label_df(top_label_df_grouped=top_label_df_grouped_poly2_svc_uspc,
                            output_directory=output_directory,
                            version_string='PatentView_uspcAffected__Poly2_SVC__v' + str(output_version))

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    _, top_label_df_grouped_poly2_svc_cpc =  lime_text_explainer(
        patent_classification=text_poly2_svc_PatentView_Claim_classification_cpc[
            ['text', '1', 'predicted_label']
            ].drop_duplicates(),
        model=text_poly2_svc,
        version_string='Poly2_SVC_cpc_v' + str(output_version),
        output_path=output_directory,
        size=1000)

    _wordcloud_top_label_df(top_label_df_grouped=top_label_df_grouped_poly2_svc_cpc,
                            output_directory=output_directory,
                            version_string='PatentView_cpcAffected__Poly2_SVC__v' + str(output_version))

    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    _, top_label_df_grouped_poly2_svc_appl =  lime_text_explainer(
        text_poly2_svc_PregrantApp_Claim_classification_cpc[
            ['text', '1', 'predicted_label']
            ].drop_duplicates(),
        model=text_poly2_svc,
        version_string='Poly2_SVC_application_v' + str(output_version),
        output_path=output_directory,
        size=1000)

    _wordcloud_top_label_df(top_label_df_grouped=top_label_df_grouped_poly2_svc_appl,
                            output_directory=output_directory,
                            version_string='PregrantApp_PatentsView_cpcAffected__Poly2_SVC__v' + str(output_version))


    print("\t\tElapsed Execution time: " + str(timedelta(seconds=(time.time() - start_time))), flush=True)


    print('End Main Routine for version: ' + str(output_version), flush=True)

#==========================================
# Main execution
if __name__ == '__main__':
    #!!! Note, PatentsViewControls version using patent claims for controls always use non-resampling in the training
    #   set construction, while ApplicationControls version always use resampling (smaller number of eligible controls)
    main_routine(
        input_version='PatentsViewControls_v'+str(INPUT_VERSION_BUILD),
        output_version='PatentsViewControls_v'+str(VERSION_BUILD),
        cpc_nclasses=CPC_NCLASSES)
    main_routine(
        input_version='ApplicationControls_v'+str(INPUT_VERSION_BUILD),
        output_version='ApplicationControls_v'+str(VERSION_BUILD),
        cpc_nclasses=CPC_NCLASSES)
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Automatically only load 705 uspc class as mainclass; only one saved in NLP classification routine
    main_routine(
        input_version='PatentsViewControls_only705_v'+str(INPUT_VERSION_BUILD),
        output_version='PatentsViewControls_only705_v'+str(VERSION_BUILD),
        cpc_nclasses=CPC_NCLASSES_705)
    main_routine(
        input_version='ApplicationControls_only705_v'+str(INPUT_VERSION_BUILD),
        output_version='ApplicationControls_only705_v'+str(VERSION_BUILD),
        cpc_nclasses=CPC_NCLASSES_705)

r'''
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Local Execution

# Test of cpc_current for applications going back further than 2013
cpc_current = pd.read_csv(
    r"C:\Users\domin\Downloads\cpc_current.tsv\cpc_current.tsv",
    delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)
application = pd.read_csv(
    r"G:\My Drive\Preliminary Research\Alice and Innovation Project\Census Data Application\Data Upload Kiteworks\Upload 3_10_2022\Packages_PatentsView_data\application_pregrant.tsv",
    delimiter="\t", quoting=csv.QUOTE_NONNUMERIC, low_memory=False)

merged_cpc_current_application = cpc_current[
    ['document_number', 'version', 'group_id', 'value', 'symbol_position']].merge(
    application[['document_number', 'application_number', 'date']],
    on='document_number', how='inner')

merged_cpc_current_application['date_dt'] = pd.to_datetime(
    merged_cpc_current_application.date, errors='coerce')

merged_cpc_current_application['date_dt'].dt.year.value_counts()
# =============================================================================
# 2017.0    4037735
# 2018.0    4004459
# 2016.0    3834022
# 2019.0    3721052
# 2015.0    3578608
# 2014.0    3346940
# 2013.0    3068235
# 2012.0    2694873
# 2020.0    2600477
# 2011.0    2439010
# 2007.0    2183036
# 2010.0    2178099
# 2006.0    2115459
# 2008.0    2065814
# 2009.0    2001794
# 2005.0    1949736
# 2004.0    1426540
# 2021.0     703687
# 2003.0     545946
# 2002.0     103046
# 2001.0      18299
# 2000.0        895
# 1999.0        149
# =============================================================================

merged_cpc_current_application.version.value_counts(normalize=True).head()
#2013-01-01    0.866718
#2018-01-01    0.037045
#2015-01-15    0.012909
#2019-01-01    0.009570
#2020-01-01    0.008434
#Name: version, dtype: float64

merged_cpc_current_application[
    #(merged_cpc_current_application.version==merged_cpc_current_application.version.max())
    (merged_cpc_current_application.version=='2013-01-01')
    ]['date_dt'].dt.year.value_counts()

# =============================================================================
# 2017.0    3552995
# 2018.0    3522462
# 2016.0    3373523
# 2019.0    3257719
# 2015.0    3141174
# 2014.0    2913981
# 2013.0    2652147
# 2012.0    2308346
# 2020.0    2257095
# 2011.0    2072247
# 2007.0    1866879
# 2010.0    1840517
# 2006.0    1826922
# 2008.0    1760635
# 2009.0    1696653
# 2005.0    1689837
# 2004.0    1230966
# 2021.0     609392
# 2003.0     463394
# 2002.0      85090
# 2001.0      15136
# 2000.0        760
# 1999.0        146
# 1918.0         46
# 1998.0         38
# 1995.0         33
# 1994.0         18
# 1911.0         18
# 1919.0         17
# 1996.0         16
# 1997.0         10
# 1913.0          6
# 1991.0          2
# 1909.0          1
# Name: date_dt, dtype: int64
# =============================================================================

###################################################
#   Group size test of treated cpc and uspc classes
###################################################

uspc = pd.read_csv('uspc.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC)
cpc_current = pd.read_csv('cpc_current.tsv', delimiter="\t", quoting=csv.QUOTE_NONNUMERIC)
cpc_current = cpc_current.drop(['uuid', 'section_id',
                                'category', 'subgroup_id',
                                'sequence'], axis=1).drop_duplicates()
uspc = uspc.drop(['uuid', 'subclass_id', 'sequence'], axis=1).drop_duplicates()

uspc_main_classes = ['705', '434', '702', '463']
uspc['mainclass_id'] = uspc['mainclass_id'].astype(str).\
        apply(lambda s: re.sub(r'^0*', '', str(s).split('.')[0]))

(uspc.mainclass_id.isin(uspc_main_classes)).value_counts(normalize=True)
# False    0.989084
# True     0.010916
cpc_main_classes = ['G06F', 'G06Q', 'G07F', 'A63F', 'H04L']
cpc_current.group_id.isin(cpc_main_classes).value_counts(normalize=True)
# False    0.908123
# True     0.091877

###################################################
#   Wording Testing
###################################################
FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7 = pd.read_csv(r"C:\Users\domin\Desktop\FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7.csv")
said_cond = (FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7.text.apply(lambda x: bool(re.search('said', str(x))))) & (FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7.predicted_label==1)
text_samples = FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7[said_cond]['text']
for t in text_samples.sample(20): print(t + '\n')
second_cond = FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7.text.apply(lambda x: bool(re.search('second', str(x)))) & (FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7.predicted_label==0)
text_samples = FullText_Patent_claim_PatentView_Alice_predicted_TFIDF_poly2_uspc_vApplicationControls7[second_cond]['text']
for t in text_samples.sample(20): print(t + '\n')
r'''
