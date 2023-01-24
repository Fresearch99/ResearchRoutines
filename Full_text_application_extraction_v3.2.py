# -*- coding: utf-8 -*-
"""
Author: Dominik Jurek

DATE: 2/5/2021
METHOD: Use the application assignment data from DB_patent_applications_structurng_for_analysis_2
        and an adapted version of the Alice_Training_Claim_Text_Extraction_v7
        text extraction from the xml files to search for the full text of the
        application assignment for which I can find firm assignees (in this case, in DMI data)
    VERSION 2: Extraction of all application from PAIR, and saving of extracts in .json format
    VERSION 3: Implement more verbous error messages and load from already saved .json files
        Subversion 3.1: Exclude the writing into file and just scrape the .json files to reduce error likelihood
        Subversion 3.2: Correct for NoneType errors in text cleaning by checking in text normalization function
                        AND modify to collect only first, independent claim
                        AND more exception handling around requests
"""

# bsub -q 8C-128G -e Full_text_application_extraction_v3_2.%J.err -o Full_text_application_extraction_v3_2.%J.out < ./Full_text_application_extraction_v3_2.sh


r'''
.sh helper file:
#-----------------------
#!/bin/bash
~/.conda/envs/py37/bin/python3 Full_text_application_extraction_v3_2.py

r'''


# %%
#################################################################
# Load Packages
#################################################################

import pandas as pd
import numpy as np
import re
import os

import requests
from io import BytesIO
from lxml import html

import zipfile
import csv

import json

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
VERSION = 3.2


# home directory
home_directory = os.getcwd()

output_directory = r'Application_fulltext_extraction_' + str(VERSION)
# Create Output Path if not already exist
if not os.path.exists(output_directory):
    os.makedirs(output_directory)

# Create also output path for json files
output_json_directory = r'Application_fulltext_extraction_' + str(VERSION) + '/app_json_files'
# Create Output Path if not already exist
if not os.path.exists(output_json_directory):
    os.makedirs(output_json_directory)


r'''
pd.set_option('display.max_rows', 400)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 100)
r'''



# %%
#################################################################
# Direct Extraction of Application Full Text
#################################################################
# Since the available data with Claim Fulltext are limited to publications before
# 2014, I will just extract the text directly from the xml publications
# Source: https://bulkdata.uspto.gov/

def application_fulltext_extraction(search_ids, output_path, output_json_directory,
                                    year = 2006, output_name = 'v6'):
    '''
    METHOD: Extracts from USPTO bulk website full text application
            for given list of application ids from xml publications
    INPUT:  search_ids: List of int application number ids to be searched after
            output_path: Path to output directory
            output_json_directory: Path to store application text extraction in .json format
            year: publication year of application to be extracted
            output_name: string of added to the end of the outpuf file name
    OUTPUT: output_json_directory: Filled with .json files for individual app text extractions
    RETURN: NONE
    '''
    #==========================================
    # Convert search id's to int
    search_ids = [int(s) for s in search_ids if not(np.isnan(s))]

    # Look for integers of the extracted .json files already
    app_json_already_existing = [int(j.replace('.json','')) for j in os.listdir(output_json_directory)]

    ##########################################
    # Text Normalization Routine             #
    ##########################################
    #import unicodedata
    def _text_nomralization(text):
        # Check if the text is empty or not, if so, return empty string
        if not(text is None):
            #text = unicodedata.normalize('NFC', text)
            # remove residual html tags
            text = re.sub(re.compile('<.*?>'), ' ', text)

            text = re.sub(r'\n|\r|\t', ' ', text)
            # Remove double spacing and backslashes
            text = re.sub(r'\s+', ' ', text)
            # Remove leading space
            text = text.strip()

            return text
        else:
            return ''

    ######################################################

    print('Start of Extraction Routine for year: ' + str(year), flush=True)

    bulk_data_url = r'https://bulkdata.uspto.gov/'

    for request_attempt in range(7):
        try:
            request = requests.get(bulk_data_url)
            if (request.ok == True):
                break
        except Exception:
            print('Error in bulk data main page connection atempt: ' + str(request_attempt), flush=True)
            continue

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
        for attempts_for_sublisting in range(7):

            # Wrapper for recall of request method if not fully fetched
            request_yearly_bool=False
            for request_attempt in range(7):
                try:
                    request_yearly = requests.get(yearly_url)
                    print('\t\t Year ' + str(year) + ', status code in attempt: '  +
                              str(attempts_for_sublisting + 1) +
                              ': ' + str(request_yearly.status_code) +
                              ' request attempt: ' + str(request_attempt), flush=True)
                    if (request_yearly.ok == True):
                        request_yearly_bool=True
                        break
                except Exception:
                    print('\t\t Error in request for yearly urls for year' + str(year)
                          + ', atempt: ' + str(request_attempt), flush=True)
                    continue

            #---------------------------------
            # Check integrity
            if request_yearly_bool==False:
                print('\t\t Year ' + str(year) + ', failed request for yearly url: '  +
                      str(attempts_for_sublisting + 1), flush=True)
                continue
            #---------------------------------

            yearly_tree = html.fromstring(request_yearly.content)

            target_columns = ['app_id',
                                  'pgpub_number',
                                  'publication_identifiers',
                                  'pgpub_country',
                                  'pgpub_kind',
                                  'pgpub_date',
                                  'application_identifiers',
                                  'app_country',
                                  'app_date',
                                  'invention_title',
                                  'abstract',
                                  'description',
                                  'first_claim',
                                  'us_related_documents',
                                  'parties',
                                  'assignee',
                                  'priority_claims',
                                  'parent_doc',
                                  'child_doc',
                                  'xml_raw_text',
                                  'full_text']

            r'''
            #------------------------------------------
            # Create yearly output df, if not already exists

            if ('Application_publication_extraction_' + str(year) + '_' + output_name + '.csv' in os.listdir(output_path)):
                print('\t\t Output table for year ' + str(year) + 'found in directory, load.', flush=True)
                full_text_df = pd.read_csv(
                    output_path + '/Application_publication_extraction_' + str(year) + \
                    '_' + output_name + '.csv', index = False, encoding = 'utf-8')

            else:
                print('\t\t Create output table for year ' + str(year), flush=True)


                full_text_df = pd.DataFrame(columns = target_columns)
                r'''
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
                attempts_for_content_table_bool=False
                for attempts_for_content_table in range(7):
                    try:
                        table = yearly_tree.xpath("//table")[1]
                        data = [[str(td.text_content()) for td in tr.xpath('td')] for tr in table.xpath('//tr')]

                        content_table = pd.DataFrame(data, columns=data[0])
                        print('\t\t\t\t Content table for ' + str(output_name) +
                              ' year ' + str(year) + ' attempt: ' + str(attempts_for_content_table) +
                              ': \n' + str(content_table), flush=True)
                        attempts_for_content_table_bool=True
                        break

                    except Exception:
                        print('\t\t\t\t Content table not created for ' + str(output_name) +
                              ' year ' + str(year) + ' attempt: ' + str(attempts_for_content_table), flush=True)
                        #retry
                #---------------------------------
                # Check integrity
                if attempts_for_content_table_bool==False:
                    print('\t\t\t\t Content table for ' + str(output_name) +
                          ' year ' + str(year) + ' failed.', flush=True)
                    continue
                else:
                    # Ultimately, break out of main loop for attempts_for_sublisting
                    break

        #================================================
        for zip_url_link_publication in zip_url_link_list:
            print('\t\t Sublist: ' + str(zip_url_link_publication), flush=True)
            try:
                # Read zip file via IO stream

                # Wrap around limited amount of retrys
                request_attempt_bool=False
                for request_attempt in range(7):
                    try:
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
                            request_attempt_bool=True
                            break
                    except Exception:
                        print('\t\t\t Error in request for sublist:' + str(zip_url_link_publication) +
                              ' attempt: ' + str(request_attempt), flush=True)
                        continue

                #---------------------------------
                # Check integrity
                if request_attempt_bool==False:
                    print('\t\t Sublist: ' + str(zip_url_link_publication) + ', loading failed.', flush=True)
                    continue
                #---------------------------------

                z = zipfile.ZipFile(BytesIO(r.content))

                # z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa100107.zip")
                # z = zipfile.ZipFile(r"C:\Users\domin\Downloads\ipa161117.zip")

                # Decode bytes object into string by following encoding of xml files
                document_string = z.open(z.infolist()[0].filename).read().decode('utf-8')

                # For debugging, search for app_id:14027103, earliest pub: US20140276241A1

                # Iterate through the string and search for document id's that fit those from
                # the required field

                #-----------------------------------------
                # Search for id that are in the extracted xml string and in the looked for search id set
                # 1. Extract all doc-number that can be found:
                # See: https://www.uspto.gov/patents-application-process/checking-application-status/search-application

                doc_number = [int(n) for n in re.findall(r'<doc-number>(\d*)</doc-number>', document_string)]
                # doc_number = [str(n).strip() for n in re.findall(r'<doc-number>(.*)</doc-number>', document_string)]

                #doc_number_int = [int(n) for n in re.findall(r'<doc-number>(\d*)</doc-number>', document_string)]
                #doc_number_str = [str(n) for n in re.findall(r'<doc-number>(.*)</doc-number>', document_string)]
                #doc_number_int_str = [str(i) for i in doc_number_int]
                #np.setdiff1d(doc_number_int_str, doc_number_str)
                #[len(s) for s in np.setdiff1d(doc_number_int_str, doc_number_str)]
                #np.setdiff1d(doc_number_str, doc_number_int_str)
                # [k for k in doc_number_str if '9449780' in k]
                # ['09449780']
                # => leading zeros are dropped
                # [k for k in doc_number_str if '201520323313.0' in k]
                # => float with decimals most likely refering to priority claims

                # for test purpose: app_id_search = '12128098'
                # app_id_search  = '20140276241'

                # 2. Find set intersect between searched and contained id's
                found_ids_in_zip = list(set.intersection(set(search_ids), set(doc_number)))
                # => It's not 100% safe to look for the application id, since it could be the case
                # that other applications reference to the application before it being published.
                # In this itteration, I also control for the multiple appearance of the same
                # application ID in the same publication xml files

                # For testing:
                # app_id_search = doc_number[1220]
                # app_id_search = 15112465
                # app_id_search = 15111543

                # 3. Check also for all the application ID values that were already extracted
                found_ids = list(set.difference(set(found_ids_in_zip), set(app_json_already_existing)))

                #alread_searched_ids = list(set.intersection(set(found_ids_in_zip), set(app_json_already_existing)))
                #============================================================
                # Extract surrounding xml tree for each id:
                # 1) search those ids that are not already in as json available
                for app_id_search  in found_ids:
                    try:
                        # => too much printing
                        #print('\t\t\t ID extraction for application number: ' + str(app_id_search) + \
                        #      ' in file ' + str(zip_url_link_publication), flush=True)

                        # Identify location of searched id in concatenated xml string
                        # NOTE: integer conversion causes leading zeros to be dropped
                        #id_positions = re.search('<doc-number>0*' + str(app_id_search) + '</doc-number>', document_string).span()
                        id_positions = [m.start() for m in re.finditer('<doc-number>0*' + str(app_id_search) + '</doc-number>', document_string)]

                        #print('\t\t\t\t Occurances found for ' + str(app_id_search) + \
                        #      ' in file ' + str(zip_url_link_publication) + ' : ' + str(len(id_positions)), flush=True)

                        # For testing
                        #id_pos = id_positions[0]

                        for id_pos in id_positions:
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

                            #----------------------------------------
                            # Raw xml text
                            xml_raw_text = subtree_string

                            # Cleaned full text:
                            full_text = _text_nomralization(document_tree.text_content())
                            #----------------------------------------


                            # publication reference:
                            publication_identifiers_dict = {}
                            if len(document_tree.xpath("//publication-reference")) != 0:
                                for item in document_tree.xpath("//publication-reference")[0].iterdescendants():
                                    publication_identifiers_dict['pgpub_'+item.tag] = _text_nomralization(item.text)

                            #======================================
                            # Detail data from publication information

                            #--------------------------------------
                            # Get pgpub county
                            if len(document_tree.xpath("//publication-reference/document-id/country")) != 0:
                                pgpub_country = _text_nomralization(document_tree.xpath("//publication-reference/document-id/country")[0].text)
                            else:
                                pgpub_country = ''
                            #--------------------------------------

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
                            # Get app country
                            if len(document_tree.xpath("//application-reference/document-id/country")) != 0:
                                app_country = _text_nomralization(document_tree.xpath("//application-reference/document-id/country")[0].text)
                            else:
                                app_country = ''
                            #--------------------------------------

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
                            #!!!!!!!!!!!!! Continue only if seached app_id equals found app_id
                            if app_id != app_id_search:
                                #print('\t\t\t\t Appl ID mismatch: ' + str(app_id_search ) + \
                                #      ' in file ' + str(zip_url_link_publication) + \
                                #      ' => Jump to next match or app_id', flush=True)
                                continue
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

                            #--------------------------------------
                            # Abstract
                            if len(document_tree.xpath("//abstract")) != 0:
                                abstract = _text_nomralization(document_tree.xpath("//abstract")[0].text_content())
                            else:
                                abstract = ''
                            #--------------------------------------

                            #--------------------------------------
                            # Description
                            if len(document_tree.xpath("//description")) != 0:
                                description = _text_nomralization(document_tree.xpath("//description")[0].text_content())
                            else:
                                description = ''
                            #--------------------------------------

                            #--------------------------------------
                            # First (uncancelled, independent) claim
                            claims = document_tree.xpath("//claims/claim")
                            if len(claims) != 0:
                                for i in range(len(claims)):
                                    first_claim = _text_nomralization(claims[i].text_content())
                                    if not(bool(re.search(r'canceled', re.sub('[^A-Za-z]','', first_claim))) & bool(len(re.sub('[^A-Za-z]','', first_claim)) < 20)):
                                        # Iterate through the children of the claim-text (which is by itself the first child of the
                                        # the claim element) and see if any of them is tagged as a claim-ref, meaning it is
                                        # a dependent claims
                                        child_tags = [child.tag for child in claims[i].getchildren()[0].getchildren()]
                                        if not('claim-ref' in child_tags):
                                            break   # => jump out of iteration through claims only if don't have cancelled string
                                                    # AND if doesn't contain references, i.e. is independent
                                    first_claim = ''
                            else:
                                first_claim = ''
                            #--------------------------------------

                            #=========================================
                            #---------------------------------
                            # Parties and assigness
                            parties_dict = {}
                            parties_n = 1
                            if len(document_tree.xpath("//parties")) != 0:
                                for item in document_tree.xpath("//parties")[0].iterchildren():
                                    for item_item in item.iterchildren():
                                        parties_dict['parties_'+item_item.tag+'_'+str(parties_n)] = _text_nomralization(item_item.text)
                                    parties_n += 1

                            #----------------------------------------
                            assignee_dict = {}
                            assignee_n = 1
                            if len(document_tree.xpath("//assignee")) != 0:
                                for item in document_tree.xpath("//assignee")[0].iterchildren():
                                    for item_item in item.iterchildren():
                                        assignee_dict['assignee_'+item_item.tag+'_'+str(assignee_n)] = _text_nomralization(item_item.text)
                                    assignee_n += 1


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


                            #===================================================
                            # Append and output
                            # => only those elements that were not already saved as .json will be appended
                            append_list = [app_id, pgpub_id,
                                           publication_identifiers_dict.__str__(),
                                           pgpub_country,
                                           pgpub_kind,
                                           pgpub_date,
                                           application_identifiers_dict.__str__(),
                                           app_country,
                                           app_date,
                                           invention_title,
                                           abstract,
                                           description,
                                           first_claim,
                                           us_related_documents_dict.__str__(),
                                           parties_dict.__str__(),
                                           assignee_dict.__str__(),
                                           priority_claims_dict.__str__(),
                                           parent_doc_dict.__str__(),
                                           child_doc_dict.__str__(),
                                           xml_raw_text,
                                           full_text]

                            #-----------------------------------------
                            # Save as .json to file
                            #-----------------------------------------
                            output_dict = dict(zip(target_columns, append_list))
                            with open(output_json_directory + '/' + str(app_id) + '.json', 'w') as fp:
                                json.dump(output_dict, fp)

                            r'''
                            #-----------------------------------------
                            full_text_df.loc[len(full_text_df)] = append_list
                            # Save output after number of itterations
                            if len(full_text_df) % 50 == 0:
                                full_text_df.to_csv(
                                    path_or_buf = output_path + '/Application_publication_extraction_'
                                    + str(year) + '_' + output_name + '.csv', index = False, encoding = 'utf-8')

                    r'''
                    except Exception as exc:
                        print('\t\t\tError in newly scraped application id ' + str(app_id_search)
                              + ' itteration through xml file ' + str(zip_url_link_publication)
                              + ' for output ' + str(output_name) + ' year '
                              + str(year) + ' :' + str(exc), flush=True)

                r'''
                #---------------------------------------------------------------------
                # 2) Extract and add the already scraped application data from .json files
                for app_id_search  in alread_searched_ids:
                    try:
                        with open(output_json_directory + '/' + str(app_id) + '.json', 'r') as fp:
                            load_dict = json.load(fp)

                        append_list = list(load_dict.values())

                        #-----------------------------------------
                        full_text_df.loc[len(full_text_df)] = append_list
                        # Save output after number of itterations
                        if len(full_text_df) % 50 == 0:
                            full_text_df.to_csv(
                                path_or_buf = output_path + '/Application_publication_extraction_'
                                + str(year) + '_' + output_name + '.csv', index = False, encoding = 'utf-8')

                    except Exception as exc:
                        print('\t\t\tError in loading existing scraped application id ' + str(app_id_search)
                              + ' itteration through xml file ' + str(zip_url_link_publication)
                              + ' for output ' + str(output_name) + ' year '
                              + str(year) + ' :' + str(exc), flush=True)
            r'''
            #------------------------------------------------------
            except Exception as exc:
                print('\t\tError in file itteration ' + str(zip_url_link_publication)
                      + ' for output ' + str(output_name)
                      + ' year ' + str(year) + ' :' + str(exc), flush=True)
        r'''
        full_text_df.to_csv(
            path_or_buf = output_path + '/Application_publication_extraction_'
            + str(year) + '_' + output_name + '.csv', index = False, encoding = 'utf-8')
    r'''
    print('End of Extraction Routine for output ' + str(output_name) +
          ' year: ' + str(year), flush=True)
    return


# %%
#################################################################
# Load target application ids and execution
#################################################################
print('Load application data', flush=True)
#----------------------------------
# Application Data
#----------------------------------
if ('application_data.csv' in os.listdir(home_directory)):
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Local
    application_data = pd.read_csv('application_data.csv')
else:
    #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    # Load application data from economic research dataset

    # Wrap around limited amount of retrys
    for request_attempt in range(5):
        r = requests.get(r"https://bulkdata.uspto.gov/data/patent/pair/economics/2019/application_data.csv.zip")
        if (r.ok == True) & \
           (len(r.content) == int(r.headers['Content-Length'])):
           break

    z = zipfile.ZipFile(BytesIO(r.content))
    z.extractall()

    application_data = pd.read_csv(z.open(z.infolist()[0].filename))

#-------------------------------------------
# find unique IDs to be searched for
application_data['app_id'] = pd.to_numeric(application_data.application_number,
                                           downcast = 'integer', errors = 'coerce')

search_list_applications = list(set([i for i in application_data['app_id'] if not(np.isnan(i))]))

del application_data
#^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# Parallel Execution
cores = mp.cpu_count()
print('\t\t Number of Cores: ' + str(cores), flush=True)

#pool = mp.Pool(cores)
pool = mp.Pool(4)
# Run the scraping method for the contents required
# !!! Before 2005, the tags for the xml files are not 'us-patent-application', so no files are extracted until 2005!!!
for year_itter in range(2001, 2021):
    print('\t Start extraction of full text for applications for year ' + str(year_itter) + '\n', flush=True)
    pool.apply_async(
                    application_fulltext_extraction,
                    args=(
                          search_list_applications,
                          output_directory,
                          output_json_directory,
                          year_itter,
                          'app_extraction_v' + str(VERSION)
                          )
                    )
pool.close()
pool.join()


r'''
# %%
#############################################
# Local; testing readability measure using Kong et al, 2020, measure
#############################################
import subprocess


p = subprocess.Popen("java -cp lib/*: /text_readability_code/readinglevel/wrappers.ExtractFeaturesForGivenText, stdin = subprocess.PIPE, stdout = subprocess.PIPE")


with open("matched_name_assignee" + str(VERSION) + ".txt","w") as f:
p = subprocess.Popen(["java -cp lib/* ", "wrappers.ExtractFeaturesForGivenText",], stdout=subprocess.PIPE)

r'''
